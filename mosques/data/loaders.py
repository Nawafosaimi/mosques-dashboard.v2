from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import hashlib

import geopandas as gpd
import openpyxl
import pandas as pd
import streamlit as st
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon  # type: ignore

from config import (
    CACHE_DIR,
    INDUSTRY_META_FILE,
    QUARTER_FILES,
    REGIONS_FILE,
    REGION_SIMPLIFY_TOLERANCE,
    REGION_NAME_MAP,
    SIMPLIFIED_REGIONS_FILE,
    TIMESERIES_FILE,
)


class DataFileError(FileNotFoundError):
    """Raised when a required data file is missing."""


def _ensure_file(path: Path, description: str) -> Path:
    if not path.exists():
        raise DataFileError(f"{description} was not found at {path}.")
    return path


@st.cache_data
def load_regions(path: Path | str = REGIONS_FILE):
    source_path = _ensure_file(Path(path), "Regions GeoJSON")
    gdf = _load_or_build_simplified_regions(source_path)
    gdf["province_en"] = gdf["name_ar"].map(REGION_NAME_MAP)
    return gdf.dropna(subset=["province_en", "geometry"])


def _load_or_build_simplified_regions(source_path: Path):
    target_path = SIMPLIFIED_REGIONS_FILE
    if (
        target_path.exists()
        and target_path.stat().st_mtime >= source_path.stat().st_mtime
        and REGION_SIMPLIFY_TOLERANCE >= 0
    ):
        cached = gpd.read_file(target_path)
        if cached["geometry"].isnull().any() or (cached.geom_type == "GeometryCollection").any():
            target_path.unlink(missing_ok=True)
        else:
            return cached

    gdf = gpd.read_file(source_path)
    gdf["geometry"] = gdf["geometry"].apply(_normalize_geometry)
    gdf = gdf.dropna(subset=["geometry"])

    if REGION_SIMPLIFY_TOLERANCE > 0:
        gdf["geometry"] = gdf["geometry"].apply(
            lambda geom: geom.simplify(
                REGION_SIMPLIFY_TOLERANCE,
                preserve_topology=True,
            )
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(target_path, driver="GeoJSON")
    return gdf


def _normalize_geometry(geom):
    if geom is None:
        return None

    if isinstance(geom, GeometryCollection):
        polygons = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not polygons:
            return None
        geom = (
            polygons[0]
            if len(polygons) == 1
            else MultiPolygon(
                [
                    poly
                    if isinstance(poly, Polygon)
                    else Polygon(poly.exterior.coords)
                    for poly in polygons
                ]
            )
        )

    return geom


@st.cache_data
def load_timeseries(path: Path | str = TIMESERIES_FILE):
    file_path = _ensure_file(Path(path), "Mosque violations timeseries parquet")
    df = pd.read_parquet(file_path)
    df["date"] = pd.to_datetime(df["date"])
    df["METER_ID_STR"] = df["METER_ID"].astype(str)
    return df


@st.cache_data
def load_industry_meta(path: Path | str = INDUSTRY_META_FILE):
    file_path = _ensure_file(Path(path), "Industry metadata parquet")
    meta = pd.read_parquet(file_path).rename(columns={"Meter Number": "METER_ID"})
    meta["METER_ID_STR"] = meta["METER_ID"].astype(str)
    lon_col, lat_col = find_coord_cols(meta)
    if lon_col and lat_col:
        meta[lon_col] = pd.to_numeric(meta[lon_col], errors="coerce")
        meta[lat_col] = pd.to_numeric(meta[lat_col], errors="coerce")
    return meta


def find_coord_cols(meta_df: pd.DataFrame) -> Tuple[str | None, str | None]:
    cols = list(meta_df.columns)
    lon = next(
        (c for c in cols if isinstance(c, str) and "x" in c.lower() and "coord" in c.lower()),
        None,
    )
    lat = next(
        (c for c in cols if isinstance(c, str) and "y" in c.lower() and "coord" in c.lower()),
        None,
    )
    return lon, lat


@st.cache_data
def load_all_violator_data(quarter_files: Dict[str, Path] = QUARTER_FILES):
    all_data: Dict[str, pd.DataFrame] = {}
    missing_sources: Dict[str, Path] = {}

    for quarter, file_path in quarter_files.items():
        path = Path(file_path)
        cache_path = _quarter_cache_path(quarter, path)

        if path.exists():
            df = _load_quarter_excel(path, quarter)
        elif cache_path.exists():
            df = pd.read_parquet(cache_path)
        else:
            missing_sources[quarter] = path
            continue

        if df is not None and not df.empty:
            all_data[quarter] = df

    if missing_sources:
        missing_list = "\n".join(f"- {q}: {p}" for q, p in missing_sources.items())
        st.warning(
            "لم يتم العثور على بعض ملفات المخالفات أو ملفات الكاش الخاصة بها. "
            "سيتم عرض ما توفر من البيانات:\n"
            f"{missing_list}"
        )

    if not all_data:
        raise DataFileError(
            "لم يتم العثور على أي ملف بيانات للمخالفات. تحقق من المسارات في config.py."
        )

    all_cols = set().union(*(df.columns for df in all_data.values()))
    for quarter in all_data:
        for col in all_cols:
            if col not in all_data[quarter].columns:
                all_data[quarter][col] = pd.NA
        all_data[quarter] = all_data[quarter][list(all_cols)]
    return all_data


def _quarter_cache_path(quarter: str, source_path: Path) -> Path:
    slug = hashlib.md5(f"{quarter}|{source_path}".encode("utf-8")).hexdigest()
    filename = f"violators_{slug}.parquet"
    return CACHE_DIR / filename


def _load_quarter_excel(path: Path, quarter: str):
    cache_path = _quarter_cache_path(quarter, path)
    if cache_path.exists() and cache_path.stat().st_mtime >= path.stat().st_mtime:
        return pd.read_parquet(cache_path)

    wb = openpyxl.load_workbook(path, data_only=False)
    dfs = []
    for sheet_name in wb.sheetnames:
        if quarter == "الربع الرابع 2024" and sheet_name == "مدينة الرياض2":
            continue
        sheet = wb[sheet_name]
        header = [
            cell.value.strip() if isinstance(cell.value, str) else cell.value
            for cell in sheet[1]
        ]
        loc_idx = header.index("الموقع") if "الموقع" in header else -1
        rows = []
        for ridx, row in enumerate(sheet.iter_rows()):
            if ridx == 0:
                continue
            values = []
            for cidx, cell in enumerate(row):
                value = cell.value
                if cidx == loc_idx and isinstance(value, str) and value.startswith("=HYPERLINK"):
                    try:
                        values.append(value.split('"')[1])
                    except Exception:
                        values.append(None)
                elif cidx == loc_idx and cell.hyperlink:
                    values.append(cell.hyperlink.target)
                else:
                    values.append(value)
            rows.append(values)
        if rows:
            sheet_df = pd.DataFrame(rows, columns=header)
            # Track which sheet this data came from using المحافظة
            sheet_df["المحافظة_الورقة"] = sheet_name
            dfs.append(sheet_df)

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        df.to_parquet(cache_path, index=False)
        return df
    return pd.DataFrame()


@st.cache_data
def precompute_helpers(all_violator_data: Dict[str, pd.DataFrame], metadata: pd.DataFrame):
    violator_sets = {
        quarter: set(df["رقم العداد"].astype(str))
        for quarter, df in all_violator_data.items()
        if "رقم العداد" in df.columns
    }
    meter_to_province = (
        metadata.set_index("METER_ID_STR")["Province"]
        if "Province" in metadata.columns
        else pd.Series(dtype="object")
    )
    return violator_sets, meter_to_province


def process_uploaded_quarter(uploaded_file, quarter_name: str) -> Tuple[bool, str]:
    """Process an uploaded quarter file and save it to quarters_config.json."""
    import json
    from io import BytesIO

    try:
        # Validate Excel structure
        excel_file = BytesIO(uploaded_file.getbuffer())
        is_valid, validation_msg = _validate_excel_structure(excel_file, quarter_name)
        if not is_valid:
            return False, validation_msg

        # Create uploaded_quarters directory if it doesn't exist
        uploaded_quarters_dir = Path(__file__).parent.parent / "uploaded_quarters"
        uploaded_quarters_dir.mkdir(parents=True, exist_ok=True)

        # Save the file
        filename = f"{quarter_name}.xlsx"
        file_path = uploaded_quarters_dir / filename

        # Write the uploaded file to disk
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Extract date range from quarter name
        start_date, end_date = _extract_date_range_from_quarter_name(quarter_name)

        # Update quarters_config.json (save in DATA_DIR, same location as quarter Excel files)
        from config import DATA_DIR
        config_file = DATA_DIR / "quarters_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
        else:
            config = {"quarters": {}}

        # Add or update the quarter
        config["quarters"][quarter_name] = {
            "file_path": f"uploaded_quarters/{filename}",
            "start_date": start_date,
            "end_date": end_date,
        }

        # Save updated config with explicit flush to ensure file is written
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            f.flush()  # Ensure file is written to disk
            import os
            os.fsync(f.fileno())  # Force OS to sync the file to disk

        # Clear cache to force reload
        st.cache_data.clear()

        return True, f"تم تحميل الربع '{quarter_name}' بنجاح!"
    except Exception as e:
        return False, f"خطأ أثناء معالجة الملف: {str(e)}"


def _validate_excel_structure(excel_file, quarter_name: str) -> Tuple[bool, str]:
    """Validate that the Excel file has the required structure."""
    try:
        wb = openpyxl.load_workbook(excel_file, data_only=False)

        # Check if file has sheets
        if not wb.sheetnames:
            return False, "الملف لا يحتوي على أي ورقات (sheets)"

        # Check required columns in first sheet
        sheet = wb[wb.sheetnames[0]]
        if not sheet:
            return False, "الملف لا يحتوي على أي بيانات"

        header = [
            cell.value.strip() if isinstance(cell.value, str) else cell.value
            for cell in sheet[1]
        ]

        # Required columns
        required_cols = {"رقم العداد", "اسم المسجد", "المحافظة"}
        missing_cols = required_cols - set(header)

        if missing_cols:
            return False, f"الملف لا يحتوي على الأعمدة المطلوبة: {', '.join(missing_cols)}"

        return True, "الملف صحيح"
    except Exception as e:
        return False, f"خطأ في التحقق من الملف: {str(e)}"


def _extract_date_range_from_quarter_name(quarter_name: str) -> Tuple[str, str]:
    """Extract date range from quarter name based on Arabic text."""
    quarter_name_lower = quarter_name.lower()
    year_str = None

    # Try to extract year
    for word in quarter_name.split():
        if word.isdigit() and len(word) == 4:
            year_str = word
            break

    if not year_str:
        year_str = str(datetime.now().year)

    year = int(year_str)

    # Determine quarter number from Arabic text
    quarter_num = 1
    if "ثاني" in quarter_name_lower or "الثاني" in quarter_name_lower:
        quarter_num = 2
    elif "ثالث" in quarter_name_lower or "الثالث" in quarter_name_lower:
        quarter_num = 3
    elif "رابع" in quarter_name_lower or "الرابع" in quarter_name_lower:
        quarter_num = 4

    # Map quarter number to date range
    quarter_dates = {
        1: ("01-01", "03-31"),
        2: ("04-01", "06-30"),
        3: ("07-01", "09-30"),
        4: ("10-01", "12-31"),
    }

    start_month_day, end_month_day = quarter_dates.get(quarter_num, ("01-01", "03-31"))
    start_date = f"{year}-{start_month_day}"
    end_date = f"{year}-{end_month_day}"

    return start_date, end_date


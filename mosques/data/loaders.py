from __future__ import annotations

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


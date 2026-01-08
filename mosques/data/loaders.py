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
from shapely.ops import orient, unary_union
from shapely.validation import make_valid

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


def normalize_id(val) -> str:
    """Robustly normalize Meter IDs to strings, stripping .0 and whitespace."""
    if val is None or pd.isna(val):
        return ""
    # Convert to string and strip whitespace
    s = str(val).strip()
    # Remove trailing .0 which often happens when Excel reads IDs as floats
    if s.endswith(".0"):
        s = s[:-2]
    return s


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
        # Re-normalize after simplification in case it created GeometryCollections
        gdf["geometry"] = gdf["geometry"].apply(_normalize_geometry)
        gdf = gdf.dropna(subset=["geometry"])

    target_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(target_path, driver="GeoJSON")
    return gdf


def _normalize_geometry(geom):
    if geom is None:
        return None

    # Helper to extract polygons recursively
    def _extract_polys(g):
        polys = []
        if isinstance(g, Polygon):
            polys.append(g)
        elif isinstance(g, MultiPolygon):
            polys.extend(g.geoms)
        elif isinstance(g, GeometryCollection):
            for sub_g in g.geoms:
                polys.extend(_extract_polys(sub_g))
        return polys

    all_polys = _extract_polys(geom)
    
    if not all_polys:
        return None
        
    if len(all_polys) == 1:
        final_geom = all_polys[0]
    else:
        final_geom = MultiPolygon(all_polys)
        
    # Fix invalid geometries
    # Check for negative area (wrong winding) and manually reverse if needed
    if final_geom.area < 0:
        if isinstance(final_geom, Polygon):
            final_geom = Polygon(final_geom.exterior.coords[::-1], final_geom.interiors)
        elif isinstance(final_geom, MultiPolygon):
            new_polys = []
            for p in final_geom.geoms:
                new_polys.append(Polygon(p.exterior.coords[::-1], p.interiors))
            final_geom = MultiPolygon(new_polys)

    if not final_geom.is_valid:
        try:
            final_geom = make_valid(final_geom)
            if isinstance(final_geom, GeometryCollection):
                 final_geom = _normalize_geometry(final_geom)
        except Exception:
            try:
                final_geom = unary_union(final_geom)
            except Exception:
                final_geom = final_geom.buffer(0)
        
    return final_geom


@st.cache_data
def load_timeseries(path: Path | str = TIMESERIES_FILE):
    file_path = _ensure_file(Path(path), "Mosque violations timeseries parquet")
    df = pd.read_parquet(file_path)
    df["date"] = pd.to_datetime(df["date"])
    df["METER_ID_STR"] = df["METER_ID"].astype(str)
    return df


@st.cache_data(ttl=3600)  # Cache for 1 hour to prevent re-validation on idle reconnect
def load_industry_meta(path: Path | str = INDUSTRY_META_FILE, meter_id: str | None = None):
    file_path = _ensure_file(Path(path), "Industry metadata parquet")
    
    meta = None
    if meter_id:
        try:
            # Try to filter at the Parquet level
            # The column in the file is "Meter Number" before renaming
            try:
                m_int = int(meter_id)
                # Check for both string and int representations
                filters = [("Meter Number", "in", [meter_id, m_int])]
            except ValueError:
                filters = [("Meter Number", "==", meter_id)]
            
            meta = pd.read_parquet(file_path, filters=filters)
        except Exception:
            # Fallback if filtering fails (e.g. column not found or other error)
            meta = None

    if meta is None:
        meta = pd.read_parquet(file_path)
        # If we fell back to full load but had a meter_id, filter in memory
        if meter_id and "Meter Number" in meta.columns:
             # We convert to string for comparison to be safe
             meta = meta[meta["Meter Number"].astype(str) == str(meter_id)]

    meta = meta.rename(columns={"Meter Number": "METER_ID"})
    # Normalize and clean columns before use and caching
    meta["METER_ID_STR"] = meta["METER_ID"].apply(normalize_id)
    if "Province" in meta.columns:
        meta["Province"] = meta["Province"].astype(str).str.strip()
    
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
def load_single_quarter_data(quarter: str, quarter_files: Dict[str, Path] = QUARTER_FILES) -> pd.DataFrame:
    """Load data for a single quarter. Useful for lazy loading specific quarters."""
    if quarter not in quarter_files:
        raise DataFileError(f"Quarter '{quarter}' not found in configuration.")
    
    file_path = quarter_files[quarter]
    path = Path(file_path)
    cache_path = _quarter_cache_path(quarter, path)

    if path.exists():
        df = _load_quarter_excel(path, quarter)
    elif cache_path.exists():
        df = pd.read_parquet(cache_path)
    else:
        raise DataFileError(f"Data file for quarter '{quarter}' not found at {path}")

    if df is None or df.empty:
        return pd.DataFrame()
    
    return df


@st.cache_data(ttl=3600)  # Cache for 1 hour to prevent re-validation on idle reconnect
def load_all_violator_data(quarter_files: Dict[str, Path] = QUARTER_FILES, specific_quarters: list[str] | None = None, meter_id: str | None = None):
    """Load violator data for all quarters or specific quarters only.
    
    Args:
        quarter_files: Dictionary mapping quarter names to file paths
        specific_quarters: Optional list of quarter names to load. If None, loads all quarters.
        meter_id: Optional meter ID to filter by. If provided, optimizes loading by filtering at source (Parquet).
    """
    all_data: Dict[str, pd.DataFrame] = {}
    missing_sources: Dict[str, Path] = {}

    # Filter to specific quarters if requested
    quarters_to_load = specific_quarters if specific_quarters else list(quarter_files.keys())

    for quarter in quarters_to_load:
        if quarter not in quarter_files:
            continue
            
        file_path = quarter_files[quarter]
        path = Path(file_path)
        cache_path = _quarter_cache_path(quarter, path)

        if path.exists():
            # If source exists, check cache validity
            if cache_path.exists() and cache_path.stat().st_mtime >= path.stat().st_mtime:
                # Cache is valid, use it
                if meter_id:
                    # Optimize: Use pushdown predicate to only load rows for this meter
                    # We try both string and int versions of the ID to be safe
                    try:
                        meter_val_int = int(meter_id)
                        filters = [("رقم العداد", "in", [meter_id, meter_val_int])]
                    except ValueError:
                        filters = [("رقم العداد", "==", meter_id)]
                    
                    try:
                        df = pd.read_parquet(cache_path, filters=filters)
                    except Exception:
                        # Fallback if filtering fails (e.g. column missing in parquet schema)
                        df = pd.read_parquet(cache_path)
                        if "رقم العداد" in df.columns:
                            df = df[df["رقم العداد"].astype(str) == str(meter_id)]
                else:
                    df = pd.read_parquet(cache_path)
            else:
                # Cache invalid or missing, load from Excel (slow)
                df = _load_quarter_excel(path, quarter)
                # Filter in memory after loading full file (so cache is saved correctly in _load_quarter_excel)
                if meter_id and df is not None and not df.empty and "رقم العداد" in df.columns:
                    df = df[df["رقم العداد"].astype(str) == str(meter_id)]
        elif cache_path.exists():
            # Only cache exists (source missing)
            if meter_id:
                try:
                    meter_val_int = int(meter_id)
                    filters = [("رقم العداد", "in", [meter_id, meter_val_int])]
                except ValueError:
                    filters = [("رقم العداد", "==", meter_id)]
                
                try:
                    df = pd.read_parquet(cache_path, filters=filters)
                except Exception:
                    df = pd.read_parquet(cache_path)
                    if "رقم العداد" in df.columns:
                        df = df[df["رقم العداد"].astype(str) == str(meter_id)]
            else:
                df = pd.read_parquet(cache_path)
        else:
            missing_sources[quarter] = path
            continue

        if df is not None and not df.empty:
            all_data[quarter] = df

    if missing_sources and not specific_quarters:
        # Only show warning if we're loading all quarters (not specific ones)
        missing_list = "\n".join(f"- {q}: {p}" for q, p in missing_sources.items())
        st.warning(
            "لم يتم العثور على بعض ملفات المخالفات أو ملفات الكاش الخاصة بها. "
            "سيتم عرض ما توفر من البيانات:\n"
            f"{missing_list}"
        )

    if not all_data and not missing_sources:
         # If we have no data but also no missing sources (e.g. empty folder?), just return empty
         pass
    elif not all_data and missing_sources:
        # If everything is missing
        raise DataFileError(
            "لم يتم العثور على أي ملف بيانات للمخالفات. تحقق من المسارات في config.py."
        )

    # Ensure columns consistency (only if we have data)
    if all_data:
        # First, standardize column names across all quarters
        for quarter in all_data:
            # Standardize the period column name (some quarters have extra "ا")
            if "الفترة صباحا/مساءا" in all_data[quarter].columns:
                all_data[quarter] = all_data[quarter].rename(columns={
                    "الفترة صباحا/مساءا": "الفترة صباحا/مساء"
                })
        
        # Now collect all unique columns (after standardization)
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
    
    # Check if this is Quarter 3 with special structure (morning/evening sheets)
    is_quarter_3_structure = (
        "الفترة الصباحية" in wb.sheetnames and 
        "الفترة المسائية" in wb.sheetnames
    )
    
    if is_quarter_3_structure:
        # Handle Quarter 3 special structure
        df = _load_quarter_3_special(wb, quarter, cache_path)
        return df
    
    # Standard loading for other quarters
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
            # Pre-clean critical columns
            if "رقم العداد" in sheet_df.columns:
                sheet_df["رقم العداد"] = sheet_df["رقم العداد"].apply(normalize_id)
            if "المحافظة" in sheet_df.columns:
                sheet_df["المحافظة"] = sheet_df["المحافظة"].astype(str).str.strip()
            dfs.append(sheet_df)

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        # If there's no المحافظة column but we have المحافظة_الورقة, use it as المحافظة
        if "المحافظة" not in df.columns and "المحافظة_الورقة" in df.columns:
            df["المحافظة"] = df["المحافظة_الورقة"]
        df.to_parquet(cache_path, index=False)
        return df
    return pd.DataFrame()


def _load_quarter_3_special(wb, quarter: str, cache_path: Path):
    """Load Quarter 3 data with special morning/evening sheet structure."""
    
    # Load morning period sheet
    morning_sheet = wb["الفترة الصباحية"]
    morning_df = _load_sheet_data(morning_sheet, "الفترة الصباحية")
    if "رقم العداد" in morning_df.columns:
        morning_df["رقم العداد"] = morning_df["رقم العداد"].apply(normalize_id)
    morning_df["الفترة صباحا/مساء"] = "صباحا"
    # Add evening violation column with NA for morning-only mosques
    morning_df["نسبة التجاوز في الفترة المسائية"] = pd.NA
    
    # Load evening period sheet
    evening_sheet = wb["الفترة المسائية"]
    evening_df = _load_sheet_data(evening_sheet, "الفترة المسائية")
    if "رقم العداد" in evening_df.columns:
        evening_df["رقم العداد"] = evening_df["رقم العداد"].apply(normalize_id)
    evening_df["الفترة صباحا/مساء"] = "مساء"
    # Add morning violation column with NA for evening-only mosques
    evening_df["نسبة التجاوز في الفترة الصباحية"] = pd.NA
    
    # Combine both periods
    combined_df = pd.concat([morning_df, evening_df], ignore_index=True)
    
    # Deduplicate mosques that appear in both periods
    if "رقم العداد" in combined_df.columns:
        # Find mosques that appear in both periods by checking which meters appear exactly twice
        meter_period_groups = combined_df.groupby("رقم العداد")["الفترة صباحا/مساء"].apply(list)
        
        # Mosques in both periods will have ['صباحا', 'مساء'] or ['مساء', 'صباحا']
        both_period_meters = []
        for meter_id, periods in meter_period_groups.items():
            if len(periods) == 2 and set(periods) == {'صباحا', 'مساء'}:
                both_period_meters.append(meter_id)
        
        both_period_meters = set(both_period_meters)
        
        # For mosques in both periods: merge the two rows into one with both violation percentages
        # For mosques in single period: keep as is
        if both_period_meters:
            # Separate mosques that appear in both periods
            is_both_period = combined_df["رقم العداد"].isin(both_period_meters)
            both_period_df = combined_df[is_both_period].copy()
            single_period_df = combined_df[~is_both_period].copy()
            
            # For mosques in both periods, merge the rows
            # Group by meter ID and combine the violation percentages
            merged_rows = []
            for meter_id in both_period_meters:
                meter_rows = both_period_df[both_period_df["رقم العداد"] == meter_id]
                
                # Start with the first row as base
                merged_row = meter_rows.iloc[0].copy()
                merged_row["الفترة صباحا/مساء"] = "كلا الفترتين"
                
                # Fill in the violation percentages from both rows
                for _, row in meter_rows.iterrows():
                    if row["الفترة صباحا/مساء"] == "صباحا":
                        merged_row["نسبة التجاوز في الفترة الصباحية"] = row["نسبة التجاوز في الفترة الصباحية"]
                    elif row["الفترة صباحا/مساء"] == "مساء":
                        merged_row["نسبة التجاوز في الفترة المسائية"] = row["نسبة التجاوز في الفترة المسائية"]
                
                merged_rows.append(merged_row)
            
            # Create DataFrame from merged rows
            if merged_rows:
                merged_df = pd.DataFrame(merged_rows)
                combined_df = pd.concat([single_period_df, merged_df], ignore_index=True)
            else:
                combined_df = single_period_df
    
    # Clean up المحافظة column - remove parenthetical suffixes like "(مقر الامارة)"
    if "المحافظة" in combined_df.columns:
        combined_df["المحافظة"] = combined_df["المحافظة"].apply(
            lambda x: x.split("(")[0].strip() if isinstance(x, str) and "(" in x else x
        )
    
    # Add "مخالف سابقا" column by checking Quarter 2
    combined_df = _add_previous_violator_column(combined_df, quarter)
    
    # Save to cache
    combined_df.to_parquet(cache_path, index=False)
    return combined_df


def _load_sheet_data(sheet, sheet_name: str) -> pd.DataFrame:
    """Load data from a single Excel sheet."""
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
        sheet_df["المحافظة_الورقة"] = sheet_name
        return sheet_df
    return pd.DataFrame()


def _add_previous_violator_column(df: pd.DataFrame, current_quarter: str) -> pd.DataFrame:
    """Add 'مخالف سابقا' column by checking if mosque was in Quarter 2."""
    
    # Only check for Quarter 3 (الربع الثالث 2025)
    if "الربع الثالث" not in current_quarter or "رقم العداد" not in df.columns:
        return df
    
    try:
        # Load Quarter 2 data to check for previous violators
        from config import QUARTER_FILES
        quarter_2_name = "الربع الثاني 2025"
        
        if quarter_2_name in QUARTER_FILES:
            quarter_2_path = Path(QUARTER_FILES[quarter_2_name])
            quarter_2_cache = _quarter_cache_path(quarter_2_name, quarter_2_path)
            
            # Try to load Quarter 2 data
            q2_df = None
            if quarter_2_path.exists():
                # Load from source if available
                q2_wb = openpyxl.load_workbook(quarter_2_path, data_only=False)
                q2_dfs = []
                for sheet_name in q2_wb.sheetnames:
                    if quarter_2_name == "الربع الرابع 2024" and sheet_name == "مدينة الرياض2":
                        continue
                    sheet = q2_wb[sheet_name]
                    header = [
                        cell.value.strip() if isinstance(cell.value, str) else cell.value
                        for cell in sheet[1]
                    ]
                    if "رقم العداد" not in header:
                        continue
                    
                    meter_idx = header.index("رقم العداد")
                    meters = [row[meter_idx].value for row in sheet.iter_rows(min_row=2)]
                    q2_dfs.extend([str(m) for m in meters if m is not None])
                
                if q2_dfs:
                    q2_meters = set(q2_dfs)
                else:
                    q2_meters = set()
            elif quarter_2_cache.exists():
                # Load from cache if source not available
                q2_df = pd.read_parquet(quarter_2_cache)
                q2_meters = set(q2_df["رقم العداد"].astype(str).unique()) if "رقم العداد" in q2_df.columns else set()
            else:
                q2_meters = set()
            
            # Add the column based on whether meter was in Quarter 2
            if q2_meters:
                df["مخالف سابقا"] = df["رقم العداد"].astype(str).apply(
                    lambda x: "نعم" if x in q2_meters else "لا"
                )
            else:
                # If Quarter 2 data not available, mark as unknown
                df["مخالف سابقا"] = pd.NA
        else:
            df["مخالف سابقا"] = pd.NA
            
    except Exception as e:
        # If any error occurs, add column with NA values
        import sys
        print(f"Warning: Could not check Quarter 2 for previous violators: {e}", file=sys.stderr)
        df["مخالف سابقا"] = pd.NA
    
    return df



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


from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import streamlit as st # Added for caching

from dotenv import load_dotenv

load_dotenv()

# ===== Mapbox Configuration =====

MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "")
MAPBOX_STYLE = "mapbox://styles/mapbox/light-v11"  # or streets-v11, outdoors-v11

# ===== Paths =====

BASE_DIR = Path(__file__).resolve().parent


def _resolve_data_dir() -> Path:
    """Return the data directory, validating any override from the environment."""
    override = os.environ.get("MOSQUES_DATA_DIR")
    if override:
        candidate = Path(override).expanduser()
        if not candidate.exists():
            raise FileNotFoundError(
                f"MOSQUES_DATA_DIR points to '{candidate}', but that path does not exist."
            )
        return candidate
    return BASE_DIR


DATA_DIR = _resolve_data_dir()


def _resolve_cache_dir(default_base: Path) -> Path:
    override = os.environ.get("MOSQUES_CACHE_DIR")
    if override:
        candidate = Path(override).expanduser()
    else:
        candidate = default_base / "cache"
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


CACHE_DIR = _resolve_cache_dir(DATA_DIR)


def _get_float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default

REGIONS_FILE = DATA_DIR / "regions.geojson"
SIMPLIFIED_REGIONS_FILE = Path(
    os.environ.get("MOSQUES_REGIONS_CACHE_FILE", CACHE_DIR / "regions_simplified.geojson")
)
REGION_SIMPLIFY_TOLERANCE = _get_float_env("REGIONS_SIMPLIFY_TOLERANCE", 0.005)

TIMESERIES_FILE = DATA_DIR / "mosque_violations_by_day.parquet"
INDUSTRY_META_FILE = DATA_DIR / "Industry Code with Population 1.parquet"

QUARTER_FILES_STATIC: Dict[str, Path] = {
    "الربع الرابع 2024": DATA_DIR
    / "المساجد المتجاوزة في الربع الرابع لعام 2024- موزعة حسب الجهات.xlsx",
    "الربع الأول 2025": DATA_DIR
    / "المساجد المتجاوزة في الربع الأول لعام 2025- موزعة حسب الجهات.xlsx",
    "الربع الثاني 2025": DATA_DIR
    / "المساجد المتجاوزة في الربع الثاني لعام 2025- موزعة حسب الجهات.xlsx",
}

QUARTER_DATES_STATIC: Dict[str, Tuple[datetime, datetime]] = {
    "الربع الرابع 2024": (datetime(2024, 10, 1), datetime(2024, 12, 31)),
    "الربع الأول 2025": (datetime(2025, 1, 1), datetime(2025, 3, 31)),
    "الربع الثاني 2025": (datetime(2025, 4, 1), datetime(2025, 6, 30)),
}


def _load_dynamic_quarters() -> Tuple[Dict[str, Path], Dict[str, Tuple[datetime, datetime]], list]:
    """Load quarters from both static config and uploaded quarters_config.json."""
    import json

    # Start with static quarters
    quarter_files = QUARTER_FILES_STATIC.copy()
    quarter_dates = QUARTER_DATES_STATIC.copy()

    # Load uploaded quarters from quarters_config.json
    config_file = DATA_DIR / "quarters_config.json"
    if config_file.exists():
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            for quarter_name, quarter_info in config.get("quarters", {}).items():
                file_path = quarter_info.get("file_path", "")
                # Convert relative path to absolute path
                if file_path:
                    abs_path = DATA_DIR / file_path
                    quarter_files[quarter_name] = abs_path

                # Parse dates
                start_date_str = quarter_info.get("start_date", "")
                end_date_str = quarter_info.get("end_date", "")
                if start_date_str and end_date_str:
                    try:
                        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                        quarter_dates[quarter_name] = (start_date, end_date)
                    except ValueError:
                        pass
        except Exception as e:
            import sys
            print(f"ERROR loading quarters_config.json: {e}", file=sys.stderr)

    # Build quarters list
    quarters = list(quarter_files.keys())

    return quarter_files, quarter_dates, quarters


# ===== Time ranges =====

@st.cache_data
def get_quarters() -> Tuple[Dict[str, Path], Dict[str, Tuple[datetime, datetime]], list]:
    """Get current quarters (static + dynamic).

    This function should be called during app execution to ensure
    dynamically loaded quarters (from uploads) are always fresh.

    IMPORTANT: This must be called on every app run to pick up newly uploaded quarters.
    """
    return _load_dynamic_quarters()


# Default values (will be overridden in app.py on each run)
QUARTER_FILES, QUARTER_DATES, QUARTERS = _load_dynamic_quarters()

# ===== Lookups =====

REGION_NAME_MAP = {
    "منطقة الرياض": "RIYADH PROVINCE",
    "منطقة مكة المكرمة": "MAKKAH PROVINCE",
    "منطقة المدينة المنورة": "MADINAH PROVINCE",
    "منطقة القصيم": "AL-QASIM PROVINCE",
    "المنطقة الشرقية": "EASTERN PROVINCE",
    "منطقة عسير": "ASEER PROVINCE",
    "منطقة تبوك": "TABOUK PROVINCE",
    "منطقة حائل": "HAIL PROVINCE",
    "منطقة الحدود الشمالية": "NORTHERN BORDERS PROVINCE",
    "منطقة جازان": "JAZAN PROVINCE",
    "منطقة نجران": "NAJRAN PROVINCE",
    "منطقة الباحة": "AL-BAAHA PROVINCE",
    "منطقة الجوف": "AL-JOWF PROVINCE",
}

CRITICAL_FILES = {
    "regions_geojson": REGIONS_FILE,
    "timeseries_parquet": TIMESERIES_FILE,
    "industry_meta_parquet": INDUSTRY_META_FILE,
}


def validate_data_configuration(require_all_quarter_files: bool = False, quarter_files: Dict[str, Path] | None = None):
    """Return dictionaries of missing critical or optional files."""
    if quarter_files is None:
        quarter_files = QUARTER_FILES

    missing_critical = {
        label: path
        for label, path in CRITICAL_FILES.items()
        if not path.exists()
    }
    missing_optional = {
        quarter: path
        for quarter, path in quarter_files.items()
        if not path.exists()
    }

    if require_all_quarter_files:
        missing_critical.update(missing_optional)
        missing_optional = {}

    return missing_critical, missing_optional


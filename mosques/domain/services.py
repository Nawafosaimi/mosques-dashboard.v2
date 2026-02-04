from __future__ import annotations

from typing import Dict, Iterable, Tuple

import pandas as pd
import streamlit as st


def safe_str(value) -> str:
    try:
        return str(value).strip()
    except Exception:
        return ""


def localize_booleans(df: pd.DataFrame) -> pd.DataFrame:
    for column in df.columns:
        if df[column].dtype == bool:
            df[column] = df[column].map({True: "نعم", False: "لا"})
        else:
            df[column] = df[column].astype(str).replace({"True": "نعم", "False": "لا"})
    return df


@st.cache_data
def simplify_geom(geom, tolerance: float = 0.01):
    """Simplify polygons to make rendering faster."""
    try:
        return geom.simplify(tolerance, preserve_topology=True)
    except Exception:
        return geom


@st.cache_data
def build_marker_payload(
    metadata: pd.DataFrame,
    meters: Iterable[str],
    lat_col: str,
    lon_col: str,
) -> Tuple[list, Dict[Tuple[float, float], str]]:
    """Return marker points + lookup table for fast clicks."""
    df = metadata[metadata["METER_ID_STR"].isin(meters)].dropna(subset=[lat_col, lon_col]).copy()
    if df.empty:
        return [], {}

    df[lat_col] = df[lat_col].astype(float)
    df[lon_col] = df[lon_col].astype(float)

    marker_lookup = {
        (round(row[lat_col], 6), round(row[lon_col], 6)): str(row["METER_ID_STR"])
        for _, row in df.iterrows()
    }

    def minimal_popup(mid, name):
        return f"<b>العداد:</b> {mid}<br><b>الاسم:</b> {safe_str(name)}"

    points = [
        [row[lat_col], row[lon_col], minimal_popup(str(row["METER_ID_STR"]), row.get("Name", "—"))]
        for _, row in df.iterrows()
    ]
    return points, marker_lookup


"""Loader for site visits data."""
from __future__ import annotations

import pandas as pd
import streamlit as st
from pathlib import Path

import config


@st.cache_data
def load_visits_data() -> pd.DataFrame:
    """Load and normalize the site visits data.
    
    Returns DataFrame with columns:
    - رقم عداد الكهرباء (normalized meter ID)
    - اسم الجامع/مسجد (mosque name)
    - الموقع (location)
    - تاريخ الزيارة (هجري) (visit date hijri)
    - التاريخ الميلادي (تقريبي) (visit date gregorian)
    - المسببات (causes)
    - الإجراء المتخذ (action taken)
    - نوع المخالفة (violation type)
    """
    visits_file = config.VISITS_FILE
    
    if not visits_file.exists():
        return pd.DataFrame()
    
    try:
        # Try cp1256 encoding first (Windows Arabic)
        df = pd.read_csv(visits_file, encoding='cp1256')
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(visits_file, encoding='utf-8-sig')
        except Exception:
            return pd.DataFrame()
    
    # Normalize meter ID column for matching
    meter_col = 'رقم عداد الكهرباء'
    if meter_col in df.columns:
        df[meter_col] = df[meter_col].astype(str).str.strip()
    
    # Drop unnamed columns
    df = df.loc[:, ~df.columns.str.startswith('Unnamed')]
    
    return df


def get_visit_status(meter_id: str, visits_df: pd.DataFrame) -> dict:
    """Get visit status for a specific meter.
    
    Returns dict with:
    - visited: bool
    - visit_date: str or None
    - action_status: str or None (تمت المعالجة / تحت الإجراء)
    - causes: str or None
    - violation_type: str or None
    """
    if visits_df.empty:
        return {'visited': False, 'visit_date': None, 'action_status': None, 'causes': None, 'violation_type': None}
    
    meter_col = 'رقم عداد الكهرباء'
    if meter_col not in visits_df.columns:
        return {'visited': False, 'visit_date': None, 'action_status': None, 'causes': None, 'violation_type': None}
    
    # Find matching visit
    match = visits_df[visits_df[meter_col] == str(meter_id).strip()]
    
    if match.empty:
        return {'visited': False, 'visit_date': None, 'action_status': None, 'causes': None, 'violation_type': None}
    
    row = match.iloc[0]
    
    # Parse date
    visit_date_obj = None
    visit_date_str = row.get('التاريخ الميلادي (تقريبي)', None)
    if isinstance(visit_date_str, str) and visit_date_str:
        try:
            # Parse with dayfirst=True to handle DD/MM/YYYY correcty
            visit_date_obj = pd.to_datetime(visit_date_str, dayfirst=True).to_pydatetime()
        except:
            pass
            
    return {
        'visited': True,
        'visit_date': visit_date_str,
        'visit_date_obj': visit_date_obj,
        'action_status': row.get('الإجراء المتخذ', None),
        'causes': row.get('المسببات', None),
        'violation_type': row.get('نوع المخالفة', None),
    }


def get_visited_meter_ids(visits_df: pd.DataFrame) -> set:
    """Get set of all visited meter IDs for fast lookup."""
    if visits_df.empty:
        return set()
    
    meter_col = 'رقم عداد الكهرباء'
    if meter_col not in visits_df.columns:
        return set()
    
    return set(visits_df[meter_col].dropna().astype(str).str.strip().unique())


def get_visit_stats(visits_df: pd.DataFrame, violator_meter_ids: set) -> dict:
    """Calculate visit statistics.
    
    Returns dict with:
    - total_visited: int
    - total_resolved: int (تمت المعالجة)
    - total_pending: int (تحت الإجراء)
    - visit_rate: float (0-100)
    """
    if visits_df.empty:
        return {'total_visited': 0, 'total_resolved': 0, 'total_pending': 0, 'visit_rate': 0.0}
    
    visited_ids = get_visited_meter_ids(visits_df)
    
    # Count how many violators have been visited
    visited_violators = visited_ids.intersection(violator_meter_ids)
    total_visited = len(visited_violators)
    
    # Count resolved vs pending
    action_col = 'الإجراء المتخذ'
    meter_col = 'رقم عداد الكهرباء'
    
    if action_col in visits_df.columns and meter_col in visits_df.columns:
        # Filter to only violators that were visited
        relevant_visits = visits_df[visits_df[meter_col].astype(str).str.strip().isin(violator_meter_ids)]
        total_resolved = len(relevant_visits[relevant_visits[action_col].str.contains('تمت المعالجة', na=False)])
        total_pending = len(relevant_visits[relevant_visits[action_col].str.contains('تحت الإجراء', na=False)])
    else:
        total_resolved = 0
        total_pending = 0
    
    # Calculate visit rate
    total_violators = len(violator_meter_ids)
    visit_rate = (total_visited / total_violators * 100) if total_violators > 0 else 0.0
    
    return {
        'total_visited': total_visited,
        'total_resolved': total_resolved,
        'total_pending': total_pending,
        'visit_rate': visit_rate,
    }

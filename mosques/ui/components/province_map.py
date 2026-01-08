from __future__ import annotations

import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import json

import config
from data import find_coord_cols, load_visits_data, get_visit_status, normalize_id
from domain import simplify_geom
from .header import render_header
from folium.plugins import FastMarkerCluster




@st.cache_data
def _get_province_geometry(_regions, province_param: str):
    """Cache province geometry and centroid calculation."""
    try:
        # Robust lookup: normalize case and strip whitespace
        p_param_clean = str(province_param).strip().upper()
        match = _regions[_regions["province_en"].fillna("").str.upper().str.strip() == p_param_clean]
        
        if not match.empty:
            province_geom = match.iloc[0].geometry
            province_geom_s = simplify_geom(province_geom, tolerance=0.02)
            return {
                "geometry": province_geom_s,
                "center_lat": province_geom_s.centroid.y,
                "center_lon": province_geom_s.centroid.x,
            }
        return None
    except Exception:
        return None


@st.cache_data
def _get_map_payload(
    _metadata: pd.DataFrame,
    _quarter_violator_data: pd.DataFrame,
    _visits_df: pd.DataFrame,
    quarter: str,
    province_param: str,
    view_mode: str,
    all_label: str,
):
    """
    Consolidated, high-performance data pipeline for the map.
    Ensures the total mosque count for the province remains consistent.
    """
    # 1. Filter metadata for province - vectorized (Master List)
    p_param_clean = str(province_param).strip()
    p_mask = _metadata["Province"].astype(str).str.strip() == p_param_clean
    province_metadata = _metadata[p_mask].copy()
    
    # Coordinates are essential
    lon_col, lat_col = find_coord_cols(province_metadata)
    if not lon_col or not lat_col:
        return None

    # 2. Identify Violators within this province for the selected quarter
    violator_meters = set()
    governorate_map = {}
    
    table_q = _quarter_violator_data
    if not table_q.empty and "رقم العداد" in table_q.columns:
        # Note: METER_ID_STR in metadata is already normalized by normalize_id in loaders.py
        allowed_meters = set(province_metadata["METER_ID_STR"].unique())
        
        # Strip/clean local copy of quarterly data
        # Use a copy to avoid in-place modification of cached data
        temp_q = table_q.copy()
        temp_q["رقم العداد"] = temp_q["رقم العداد"].apply(normalize_id)
        
        violator_in_prov = temp_q[temp_q["رقم العداد"].isin(allowed_meters)]
        violator_meters = set(violator_in_prov["رقم العداد"].unique())
        
        # Prepare governorate map from violator data if available
        if "المحافظة" in violator_in_prov.columns:
            grouped = violator_in_prov.dropna(subset=["المحافظة"]).drop_duplicates("رقم العداد")
            governorate_map = dict(zip(grouped["رقم العداد"], grouped["المحافظة"]))

    # 3. Partition Master List into Violators and Non-Violators
    violator_mask = province_metadata["METER_ID_STR"].isin(violator_meters)
    violator_master_df = province_metadata[violator_mask].copy()
    non_violator_master_df = province_metadata[~violator_mask].copy()

    # Process Violators (With Visits Merge)
    v_payload = []
    if not violator_master_df.empty:
        violator_master_df = violator_master_df.dropna(subset=[lat_col, lon_col])
        violator_master_df[lat_col] = violator_master_df[lat_col].astype(float).round(5)
        violator_master_df[lon_col] = violator_master_df[lon_col].astype(float).round(5)
        
        v_visits = _visits_df.copy()
        if not v_visits.empty and "رقم عداد الكهرباء" in v_visits.columns:
            # Normalize v_visits key for reliable merging
            v_visits["رقم عداد الكهرباء"] = v_visits["رقم عداد الكهرباء"].apply(normalize_id)
            v_visits = v_visits.drop_duplicates(subset=["رقم عداد الكهرباء"])
            merged_v = pd.merge(
                violator_master_df, 
                v_visits[['رقم عداد الكهرباء', 'التاريخ الميلادي (تقريبي)', 'الإجراء المتخذ', 'المسببات', 'نوع المخالفة']], 
                left_on="METER_ID_STR", 
                right_on="رقم عداد الكهرباء", 
                how="left"
            )
        else:
            merged_v = violator_master_df.copy()
            for col in ['رقم عداد الكهرباء', 'التاريخ الميلادي (تقريبي)', 'الإجراء المتخذ', 'المسببات', 'نوع المخالفة']:
                merged_v[col] = pd.NA

        merged_v["marker_color"] = "R"
        merged_v["visit_status_display"] = "UV"
        merged_v["visit_date_display"] = ""
        merged_v["causes_display"] = ""
        merged_v["violation_display"] = ""

        visited_mask = merged_v["رقم عداد الكهرباء"].notna()
        if quarter != all_label and quarter in config.QUARTER_DATES:
            q_start, q_end = config.QUARTER_DATES[quarter]
            dt_temp = pd.to_datetime(merged_v["التاريخ الميلادي (تقريبي)"], dayfirst=True, errors='coerce')
            visited_mask = visited_mask & (dt_temp >= q_start) & (dt_temp <= q_end)

        if visited_mask.any():
            merged_v.loc[visited_mask, "visit_date_display"] = merged_v.loc[visited_mask, "التاريخ الميلادي (تقريبي)"].fillna("")
            merged_v.loc[visited_mask, "causes_display"] = merged_v.loc[visited_mask, "المسببات"].fillna("")
            merged_v.loc[visited_mask, "violation_display"] = merged_v.loc[visited_mask, "نوع المخالفة"].fillna("")
            action_col = merged_v.loc[visited_mask, "الإجراء المتخذ"].astype(str).fillna("")
            merged_v.loc[visited_mask & action_col.str.contains("تمت المعالجة"), "marker_color"] = "G"
            merged_v.loc[visited_mask & action_col.str.contains("تمت المعالجة"), "visit_status_display"] = "VV"
            merged_v.loc[visited_mask & action_col.str.contains("تحت الإجراء"), "marker_color"] = "O"
            merged_v.loc[visited_mask & action_col.str.contains("تحت الإجراء"), "visit_status_display"] = "PI"

        merged_v["governorate_display"] = merged_v["METER_ID_STR"].map(governorate_map).fillna(merged_v["GOVERNORATE_NAME_AR"] if "GOVERNORATE_NAME_AR" in merged_v.columns else "").fillna("")
        
        v_payload = merged_v[[lat_col, lon_col, "Name", "METER_ID_STR", "governorate_display", "marker_color", "visit_status_display", "visit_date_display", "causes_display", "violation_display"]].values.tolist()

    # If we only want violators, return now
    if view_mode == "المتجاوزين فقط":
        return v_payload

    # Otherwise, also process Non-Violators (The rest of the master list)
    nv_payload = []
    if not non_violator_master_df.empty:
        non_violator_master_df = non_violator_master_df.dropna(subset=[lat_col, lon_col])
        non_violator_master_df[lat_col] = non_violator_master_df[lat_col].astype(float).round(5)
        non_violator_master_df[lon_col] = non_violator_master_df[lon_col].astype(float).round(5)
        
        # Static fields for NV
        non_violator_master_df["governorate_display"] = non_violator_master_df["GOVERNORATE_NAME_AR"] if "GOVERNORATE_NAME_AR" in non_violator_master_df.columns else ""
        non_violator_master_df["marker_color"] = "GY"
        non_violator_master_df["visit_status_display"] = "NV"
        non_violator_master_df["visit_date_display"] = ""
        non_violator_master_df["causes_display"] = ""
        non_violator_master_df["violation_display"] = ""
        
        nv_payload = non_violator_master_df[[lat_col, lon_col, "Name", "METER_ID_STR", "governorate_display", "marker_color", "visit_status_display", "visit_date_display", "causes_display", "violation_display"]].values.tolist()

    # Stable Sorting & Zero-Filtering:
    # 1. Filter out (0,0) coordinates which represent missing data (off Africa coast)
    # 2. Sort ensures deterministic clustering (Lat, Lon, ID)
    final_payload = [x for x in (v_payload + nv_payload) if not (x[0] == 0.0 and x[1] == 0.0)]
    
    # Sort by: Lat (0), Lon (1), Meter ID (3)
    final_payload.sort(key=lambda x: (x[0], x[1], x[3]))
    
    return final_payload


def render_province_map(
    province_param: str,
    regions,
    metadata,
    all_violator_data: dict,
):
    if st.query_params.get("view", "") != "map" or not province_param:
        return False

    # Render header with ministry logo
    render_header()

    # --- Header & Controls ---
    col_back, col_title, col_filter = st.columns([0.6, 2.8, 0.6])
    with col_back:
        if st.button(" رجوع", key="btn_back_from_map", use_container_width=True):
            back_q = st.query_params.get("quarter", config.QUARTERS[0])
            st.query_params.update(province=province_param, quarter=back_q)
            if "view" in st.query_params:
                del st.query_params["view"]
            st.rerun()

    with col_title:
        ar_province_map = regions.loc[regions["province_en"] == province_param, "name_ar"].iloc[0]
        st.markdown(
            f"<h2 style='text-align:center; margin: 0; padding-top: 5px; color: #1a2f29;'>{ar_province_map}</h2>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # --- View Toggle & Quarter Selection ---
    # --- View Toggle & Quarter Selection ---
    st.markdown("""
        <style>
        .map-section-label {
            text-align: center !important;
            width: 100% !important;
            margin: 0 auto 8px auto !important;
            font-size: 20px !important;
            font-weight: 700 !important;
            color: #2b5d4a !important;
            display: block !important;
        }
        /* Broad centering for Streamlit vertical blocks in these columns */
        [data-testid="column"] [data-testid="stVerticalBlock"] {
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
        }
        /* Radio group styling: centered and compact */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            justify-content: center !important;
            display: flex !important;
            width: 100% !important;
            gap: 24px !important;
            margin: 0 auto !important;
        }
        div[data-testid="stRadio"] label p {
            color: #000000 !important;
            font-weight: 600 !important;
            font-size: 16px !important;
        }
        /* Selectbox styling: centered and fixed width */
        div[data-testid="stSelectbox"] {
            margin: 0 auto !important;
            width: 100% !important;
            max-width: 250px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Use a tighter 5-column layout to bring controls closer to the center
    # [spacer, view_mode, middle_spacer, quarter, spacer]
    # In RTL, these render from right-to-left
    _, col_toggle, _mid, col_q, _ = st.columns([3, 3, 0.5, 8, 1], gap="large")
    
    with col_toggle:
        st.markdown("<p class='map-section-label'>نطاق العرض</p>", unsafe_allow_html=True)
        view_mode = st.radio(
            "عرض المساجد",
            ["المتجاوزين فقط", "جميع المساجد"],
            index=0, 
            horizontal=True, 
            label_visibility="collapsed", 
            key="p_map_vmode_v7"
        )

    all_label = "كل الأرباع"
    with col_q:
        st.markdown("<p class='map-section-label'>اختر الربع</p>", unsafe_allow_html=True)
        
        opts = [all_label] + config.QUARTERS
        q_in_url = st.query_params.get("quarter", config.QUARTERS[0])
        q_idx = opts.index(q_in_url) if q_in_url in opts else 0
        
        sel_q_map = st.selectbox(
            "الربع",
            opts,
            index=q_idx,
            label_visibility="collapsed",
            key="p_map_qtr_v7",
        )

    # --- Legend ---
    st.markdown("""
        <style>
        .map-legend {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 32px;
            padding: 12px 24px;
            background-color: #faf8f3;
            border-radius: 12px;
            margin: 16px auto;
            max-width: fit-content;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
            border: 1px solid #e1d9c6;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-marker {
            width: 16px;
            height: 16px;
            border-radius: 50%;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
        }
        .legend-label {
            font-family: 'Tajawal', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: #1a2f29;
        }
        </style>
        <div class="map-legend">
            <div class="legend-item">
                <div class="legend-marker" style="background-color: #808080;"></div>
                <span class="legend-label">غير متجاوز</span>
            </div>
            <div class="legend-item">
                <div class="legend-marker" style="background-color: #0B9444;"></div>
                <span class="legend-label">متجاوز وتمت زيارته</span>
            </div>
            <div class="legend-item">
                <div class="legend-marker" style="background-color: #dc3545;"></div>
                <span class="legend-label">متجاوز ولم تتم زيارته</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- Consolidated Data Preparation (CACHED - NO HASHING) ---
    all_label = "كل الأرباع"
    visits_df = load_visits_data()
    
    # Pass only the relevant quarter's data to avoid hashing the whole dict
    if sel_q_map == all_label:
        quarter_violator_data = pd.concat(all_violator_data.values(), ignore_index=True)
    else:
        quarter_violator_data = all_violator_data.get(sel_q_map, pd.DataFrame())

    map_data = _get_map_payload(
        metadata,
        quarter_violator_data,
        visits_df,
        sel_q_map,
        province_param,
        view_mode,
        all_label
    )
    
    if not map_data:
        st.warning("لا توجد بيانات للمتجاوزين")
        st.stop()

    # --- Map Center & Zoom (CACHED - NO HASHING) ---
    geom_data = _get_province_geometry(regions, province_param)
    
    if geom_data:
        center_lat = geom_data["center_lat"]
        center_lon = geom_data["center_lon"]
        province_geom_s = geom_data["geometry"]
        zoom_level = 6
    else:
        # Fallback center: Mean of valid coordinates (centers on highest density cluster)
        valid_coords = [p for p in map_data if not (p[0] == 0.0 and p[1] == 0.0)]
        if valid_coords:
            import numpy as np
            lats = [p[0] for p in valid_coords]
            lons = [p[1] for p in valid_coords]
            center_lat = float(np.mean(lats))
            center_lon = float(np.mean(lons))
        else:
            center_lat = 24.7136  # Ultimate fallback to Riyadh
            center_lon = 46.6753
        zoom_level = 6
        province_geom_s = None

    # --- Folium Map Construction ---
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles="CartoDB positron",
        control_scale=True
    )

    # Inject Custom CSS for Font and Popup Styling
    map_custom_css = """
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        /* Force font on everything in the map */
        .leaflet-container {
            font-family: 'Tajawal', sans-serif !important;
        }
        
        /* Customize marker cluster styling - Orange background with white text */
        .marker-cluster-small,
        .marker-cluster-medium,
        .marker-cluster-large {
            background-color: rgba(255, 140, 0, 0.6) !important;
        }
        
        .marker-cluster-small div,
        .marker-cluster-medium div,
        .marker-cluster-large div {
            background-color: #ff8c00 !important;
            color: white !important;
        }
        
        /* Customize the popup wrapper to match theme */
        .custom-popup .leaflet-popup-content-wrapper {
            background: #faf8f3 !important;
            color: #1a2f29 !important;
            border-radius: 12px !important;
            padding: 0 !important; /* Remove default padding */
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }
        
        /* Customize the popup tip */
        .custom-popup .leaflet-popup-tip {
            background: #faf8f3 !important;
        }
        
        /* Remove default margin/width constraints from content */
        .custom-popup .leaflet-popup-content {
            margin: 0 !important;
            width: auto !important;
        }
        
        /* Style the close button */
        .custom-popup .leaflet-popup-close-button {
            color: #8a7a63 !important;
            font-size: 18px !important;
            padding: 8px !important;
        }
    </style>
    """
    m.get_root().html.add_child(folium.Element(map_custom_css))

    # 1. Add Province Boundary
    if province_geom_s is not None:
        folium.GeoJson(
            province_geom_s,
            name="Province Boundary",
            style_function=lambda x: {
                "fillColor": "#0B9444",
                "color": "#0B9444",
                "weight": 2,
                "fillOpacity": 0.1,
            },
            tooltip=ar_province_map
        ).add_to(m)

    # 2. Add Mosque Markers with FastMarkerCluster

    callback = f"""
    function (row) {{
        var lat = row[0];
        var lon = row[1];
        var name = row[2];
        var meter_id = row[3];
        var governorate = row[4] || "";
        
        // Decoding Mapping
        var color_map = {{'R': 'red', 'G': 'green', 'O': 'orange', 'GY': 'gray'}};
        var status_map = {{
            'NV': 'غير متجاوز',
            'UV': 'متجاوز ولم تتم زيارته',
            'VV': 'متجاوز وتمت زيارته',
            'PI': 'تحت الإجراء'
        }};
        
        var marker_color_code = row[5] || "R";
        var visit_status_code = row[6] || "UV";
        
        var marker_color = color_map[marker_color_code] || 'red';
        var visit_status = status_map[visit_status_code] || 'متجاوز ولم تتم زيارته';
        
        var visit_date = row[7] || "";
        var causes = row[8] || "";
        var violation_type = row[9] || "";
        
        var details_link = "/?meter=" + meter_id + "&province={province_param}&quarter={sel_q_map}";
        var google_maps_link = "https://www.google.com/maps/search/?api=1&query=" + lat + "," + lon;
        
        var badge_color = marker_color === 'green' ? '#0B9444' : (marker_color === 'orange' ? '#ff8c00' : (marker_color === 'gray' ? '#808080' : '#dc3545'));
        
        var visit_info_html = '';
        if (visit_date) {{
            visit_info_html += `
                <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #8a7a63; font-size: 12px;">تاريخ الزيارة:</span>
                    <span style="color: #1a2f29; font-size: 13px; font-weight: 600;">${{visit_date}}</span>
                </div>
            `;
        }}
        if (causes) {{
            visit_info_html += `
                <div style="margin-bottom: 8px;">
                    <span style="color: #8a7a63; font-size: 12px; display: block; margin-bottom: 4px;">المسببات:</span>
                    <span style="color: #1a2f29; font-size: 12px; line-height: 1.4;">${{causes}}</span>
                </div>
            `;
        }}
        
        var popup_html = `
            <div style="
                font-family: 'Tajawal', sans-serif; 
                direction: rtl; 
                text-align: right; 
                min-width: 300px;
                padding: 12px;
                background-color: #faf8f3;
                border-radius: 12px;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
            ">
                <h4 style="
                    margin: 0 0 10px 0; 
                    color: #0B9444; 
                    font-size: 16px; 
                    font-weight: 700;
                    border-bottom: 1px solid #f0f0f0;
                    padding-bottom: 10px;
                ">${{name}}</h4>
                
                <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #8a7a63; font-size: 13px;">رقم العداد:</span>
                    <span style="color: #1a2f29; font-size: 14px; font-weight: 700; font-family: 'Tajawal', sans-serif;">${{meter_id}}</span>
                </div>
                <div style="margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #8a7a63; font-size: 13px;">المحافظة:</span>
                    <span style="color: #1a2f29; font-size: 14px; font-weight: 700; font-family: 'Tajawal', sans-serif;">${{governorate}}</span>
                </div>
                <div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #8a7a63; font-size: 13px;">الحالة:</span>
                    <span style="
                        background-color: ${{badge_color}};
                        color: white;
                        padding: 3px 10px;
                        border-radius: 12px;
                        font-size: 12px;
                        font-weight: 600;
                    ">${{visit_status}}</span>
                </div>
                
                ${{visit_info_html}}
                
                <div style="display: flex; gap: 10px; margin-top: 10px;">
                    <a href="${{details_link}}" target="_blank" style="
                        flex: 1;
                        background-color: #f4efe2; 
                        color: #1a2f29; 
                        padding: 8px 12px; 
                        text-decoration: none; 
                        border-radius: 8px; 
                        font-size: 13px;
                        font-weight: 600;
                        text-align: center;
                        transition: all 0.2s;
                        border: 1px solid #e1d9c6;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
                    "
                    onmouseover="this.style.backgroundColor='#eaddc5'; this.style.borderColor='#d4c8b0';"
                    onmouseout="this.style.backgroundColor='#f4efe2'; this.style.borderColor='#e1d9c6';"
                    >
                        تفاصيل اكثر
                    </a>
                    <a href="${{google_maps_link}}" target="_blank" style="
                        flex: 1;
                        background-color: #f4efe2; 
                        color: #1a2f29; 
                        padding: 8px 12px; 
                        text-decoration: none; 
                        border-radius: 8px; 
                        font-size: 13px;
                        font-weight: 600;
                        text-align: center;
                        transition: all 0.2s;
                        border: 1px solid #e1d9c6;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
                    "
                    onmouseover="this.style.backgroundColor='#eaddc5'; this.style.borderColor='#d4c8b0';"
                    onmouseout="this.style.backgroundColor='#f4efe2'; this.style.borderColor='#e1d9c6';"
                    >
                        موقع قوقل ماب
                    </a>
                </div>
            </div>
        `;
        
        var marker = L.marker(new L.LatLng(lat, lon));
        marker.bindPopup(popup_html, {{
            maxWidth: 400,
            className: 'custom-popup' 
        }});
        
        var icon = L.AwesomeMarkers.icon({{
            icon: 'mosque',
            markerColor: marker_color,
            prefix: 'fa'
        }});
        marker.setIcon(icon);
        return marker;
    }}
    """

    # Combined Cluster Layer (Fixes overlapping circles from image)
    FastMarkerCluster(
        data=map_data,
        callback=callback,
        name="المساجد",
        overlay=True,
        control=False
    ).add_to(m)

    # --- Render Map ---
    st_folium(
        m,
        width="100%",
        height=700,
        returned_objects=[],
        debug=False,
        key=f"map_{province_param}_{sel_q_map}_{view_mode}"
    )

    return True

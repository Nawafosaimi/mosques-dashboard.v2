from __future__ import annotations

import pandas as pd
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import json

import config
from data import find_coord_cols
from domain import simplify_geom


def render_province_map(
    province_param: str,
    regions,
    metadata,
    all_violator_data: dict,
):
    if st.query_params.get("view", "") != "map" or not province_param:
        return False

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

    with col_filter:
        all_label = "كل الأرباع"
        opts = [all_label] + config.QUARTERS
        q_in_url = st.query_params.get("quarter", config.QUARTERS[0])
        q_idx = opts.index(q_in_url) if q_in_url in opts else 0
        
        # Styled selectbox for quarter
        st.markdown("<p class='filter-label'>اختر الربع </p>", unsafe_allow_html=True)
        sel_q_map = st.selectbox(
            "الربع",
            opts,
            index=q_idx,
            label_visibility="collapsed",
            key="map_quarter",
        )
        if sel_q_map != q_in_url:
            st.query_params.update(quarter=sel_q_map, view="map", province=province_param)
            st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # --- Data Preparation ---
    if sel_q_map == "كل الأرباع":
        table_q_all_provinces = pd.concat(all_violator_data.values(), ignore_index=True)
    else:
        table_q_all_provinces = all_violator_data.get(sel_q_map, pd.DataFrame()).copy()

    if table_q_all_provinces.empty or "رقم العداد" not in table_q_all_provinces.columns:
        st.warning("لا توجد بيانات لعرض الخريطة.")
        st.stop()

    allowed_meters = set(
        metadata[metadata["Province"] == province_param]["METER_ID_STR"].astype(str).unique()
    ) if "Province" in metadata.columns else set()

    temp = table_q_all_provinces.copy()
    temp["رقم العداد"] = temp["رقم العداد"].astype(str)
    violator_meters = temp[temp["رقم العداد"].isin(allowed_meters)]["رقم العداد"].unique()

    lon_col, lat_col = find_coord_cols(metadata)
    if not lon_col or not lat_col:
        st.info("لا تتوفر إحداثيات X,Y لعرض الخريطة.")
        st.stop()

    # Get mosque data with coordinates
    mosque_df = metadata[metadata["METER_ID_STR"].isin(violator_meters)].dropna(subset=[lat_col, lon_col]).copy()
    
    if mosque_df.empty:
        st.info("لا توجد مواقع لعرضها.")
        st.stop()

    mosque_df[lat_col] = mosque_df[lat_col].astype(float)
    mosque_df[lon_col] = mosque_df[lon_col].astype(float)
    mosque_df["METER_ID_STR"] = mosque_df["METER_ID_STR"].astype(str)
    mosque_df["Name"] = mosque_df["Name"].fillna("—")

    # --- Map Center & Zoom ---
    try:
        province_geom = regions[regions["province_en"] == province_param].iloc[0].geometry
        province_geom_s = simplify_geom(province_geom, tolerance=0.02)
        # Calculate centroid for initial view
        center_lat = province_geom_s.centroid.y
        center_lon = province_geom_s.centroid.x
        zoom_level = 6
    except Exception:
        center_lat = mosque_df[lat_col].mean()
        center_lon = mosque_df[lon_col].mean()
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
    # We use FastMarkerCluster with a custom JS callback to handle popups efficiently
    # This avoids creating thousands of Marker objects in Python, which is slow.
    
    from folium.plugins import FastMarkerCluster

    # Prepare data for FastMarkerCluster: [[lat, lon, name, meter_id], ...]
    # Optimization: Send only raw data, generate HTML in JS to reduce payload size
    map_data = []
    
    for _, row in mosque_df.iterrows():
        meter_id = row["METER_ID_STR"]
        name = row["Name"]
        lat = row[lat_col]
        lon = row[lon_col]
        map_data.append([lat, lon, name, meter_id])

    # Define JS callback to create markers with popups
    # 'row' corresponds to an item in map_data: [lat, lon, name, meter_id]
    # We construct the HTML entirely on the client side
    callback = f"""
    function (row) {{
        var lat = row[0];
        var lon = row[1];
        var name = row[2];
        var meter_id = row[3];
        
        // Use root-relative path '/' to ensure we link to the main app, not the iframe's path
        var details_link = "/?meter=" + meter_id + "&province={province_param}&quarter={sel_q_map}";
        var google_maps_link = "https://www.google.com/maps/search/?api=1&query=" + lat + "," + lon;
        
        var popup_html = `
            <div style="
                font-family: 'Tajawal', sans-serif; 
                direction: rtl; 
                text-align: right; 
                min-width: 300px;
                padding: 12px;
                background-color: #faf8f3;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            ">
                <h4 style="
                    margin: 0 0 10px 0; 
                    color: #0B9444; 
                    font-size: 16px; 
                    font-weight: 700;
                    border-bottom: 1px solid #f0f0f0;
                    padding-bottom: 10px;
                ">${{name}}</h4>
                
                <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center;">
                    <span style="color: #8a7a63; font-size: 13px;">رقم العداد:</span>
                    <span style="color: #1a2f29; font-size: 14px; font-weight: 700; font-family: 'Tajawal', sans-serif;">${{meter_id}}</span>
                </div>
                
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
            markerColor: 'red',
            prefix: 'fa'
        }});
        marker.setIcon(icon);
        return marker;
    }}
    """

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
        returned_objects=[], # We rely on HTML links for interaction now
        debug=False,
    )

    st.stop()

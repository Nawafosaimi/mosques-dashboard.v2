from __future__ import annotations

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
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
    col_back, col_title, col_filter = st.columns([1, 2, 1])
    with col_back:
        if st.button("رجوع", key="btn_back_from_map"):
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

    # --- Plotly Map Construction ---
    
    # Base Map Configuration
    fig = go.Figure()

    # 1. Add Province Boundary (Polygon)
    if province_geom_s is not None:
        # Convert Shapely geometry to GeoJSON
        geo_json = json.loads(json.dumps(province_geom_s.__geo_interface__))
        
        # We need to wrap it in a FeatureCollection for Plotly
        feature_collection = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": geo_json, "id": "province_boundary"}]
        }

        fig.add_trace(go.Choroplethmapbox(
            geojson=feature_collection,
            locations=["province_boundary"],
            z=[1], # Dummy value
            colorscale=[[0, "rgba(11, 148, 68, 0.1)"], [1, "rgba(11, 148, 68, 0.1)"]],
            showscale=False,
            marker_line_color="#0B9444",
            marker_line_width=2,
            hoverinfo="skip"
        ))

    # 2. Add Mosque Markers (Clean Premium View)
    # We use Scattermapbox for clickable points
    fig.add_trace(go.Scattermapbox(
        lat=mosque_df[lat_col],
        lon=mosque_df[lon_col],
        mode='markers',
        marker=go.scattermapbox.Marker(
            size=16,
            color='#0B9444', # Brand Green
            opacity=0.95,
            allowoverlap=True,
        ),
        text=mosque_df["Name"],
        customdata=mosque_df["METER_ID_STR"],
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "رقم العداد: %{customdata}<br>" +
            "<extra></extra>" # Hides the secondary box
        ),
        name="المساجد",
        # IDs for selection
        ids=mosque_df["METER_ID_STR"],
        # Enable Native Clustering
        cluster=dict(
            enabled=True,
            color="#0B9444", 
            opacity=0.95,
            step=10011, # Increased radius to group more points (bigger numbers)
            size=25, # Visual size
        )
    ))

    # Layout Configuration
    fig.update_layout(
        mapbox=dict(
            style="carto-positron", # Premium clean style
            center=dict(lat=center_lat, lon=center_lon),
            zoom=zoom_level,
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=700,
        showlegend=False,
        clickmode='event+select' # Enable selection events
    )

    # --- Render & Handle Interaction ---
    
    # Use st.plotly_chart with selection handling
    # Note: 'on_select' is available in recent Streamlit versions.
    # If using an older version, we might need a fallback, but we'll assume modern.
    
    selection = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun", # Rerun app when a point is selected
        key=f"map_selection_{province_param}_{sel_q_map}",
        config={'scrollZoom': True, 'displayModeBar': True}
    )

    # Check for selection and redirect instantly
    selected_points = selection.get("selection", {}).get("points", [])
    
    if selected_points:
        # Get the first selected point (assuming single select or taking first)
        point = selected_points[0]
        # In Scattermapbox, 'point_index' maps back to the dataframe
        point_index = point.get("point_index")
        
        if point_index is not None:
            clicked_meter_id = mosque_df.iloc[point_index]["METER_ID_STR"]
            # Instant redirect to meter details page
            st.query_params.update(meter=clicked_meter_id, province=province_param, quarter=sel_q_map)
            st.rerun()

    st.stop()

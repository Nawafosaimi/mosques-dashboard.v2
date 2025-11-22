from __future__ import annotations

import folium
import pandas as pd
import streamlit as st
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

import config
from data import find_coord_cols
from domain import simplify_geom


@st.cache_data(ttl=300)
def _prepare_marker_data(mosque_records, lat_col, lon_col, province_param, sel_q_map):
    """Prepare marker data for FastMarkerCluster (cached for 5 minutes)"""
    marker_data = []
    marker_lookup = {}
    
    for row in mosque_records:
        meter_id = str(row["METER_ID_STR"])
        mosque_name = row.get("Name", "—")
        lat = float(row[lat_col])
        lon = float(row[lon_col])
        
        # Create popup with mosque info and direct link to meter details page
        from urllib.parse import quote_plus
        meter_link = f"?meter={quote_plus(meter_id)}&province={quote_plus(province_param)}&quarter={quote_plus(sel_q_map)}"
        
        popup_html = f"""
        <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
        <div style="font-family:'Tajawal',sans-serif;direction:rtl;min-width:200px;background:#faf8f3;border:1px solid #e1d9c6;border-radius:12px;padding:12px;text-align:center">
            <h4 style="margin:0 0 8px 0;color:#2b5d4a;font-size:15px;border-bottom:2px solid #0B9444;padding-bottom:4px;font-weight:700;font-family:'Tajawal',sans-serif">معلومات المسجد</h4>
            <p style="margin:5px 0;font-size:13px;font-family:'Tajawal',sans-serif"><b style="color:#2b5d4a">اسم المسجد:</b><br><span style="color:#1a2f29">{mosque_name}</span></p>
            <p style="margin:5px 0 10px 0;font-size:13px;font-family:'Tajawal',sans-serif"><b style="color:#2b5d4a">رقم العداد:</b><br><span style="color:#1a2f29">{meter_id}</span></p>
            <div style="margin-top:10px">
                <a href="{meter_link}" target="_self" style="display:inline-block;background:#0B9444;color:white;padding:8px 16px;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;font-family:'Tajawal',sans-serif">
                    عرض التفاصيل ←
                </a>
            </div>
        </div>
        """
        
        marker_data.append([lat, lon, popup_html])
        marker_lookup[(round(lat, 6), round(lon, 6))] = meter_id
    
    return marker_data, marker_lookup


def render_province_map(
    province_param: str,
    regions,
    metadata,
    all_violator_data: dict,
):
    if st.query_params.get("view", "") != "map" or not province_param:
        return False

    top_l, top_c, top_r = st.columns([1, 2, 1])
    with top_l:
        if st.button("رجوع", key="btn_back_from_map"):
            back_q = st.query_params.get("quarter", config.QUARTERS[0])
            st.query_params.update(province=province_param, quarter=back_q)
            if "view" in st.query_params:
                del st.query_params["view"]
            st.rerun()
    with top_c:
        ar_province_map = regions.loc[regions["province_en"] == province_param, "name_ar"].iloc[0]
        st.markdown(
            f"<h2 style='text-align:center;'>الخريطة التفاعلية {ar_province_map}</h2>",
            unsafe_allow_html=True,
        )
    with top_r:
        all_label = "كل الأرباع"
        opts = [all_label] + config.QUARTERS
        q_in_url = st.query_params.get("quarter", config.QUARTERS[0])
        q_idx = opts.index(q_in_url) if q_in_url in opts else 0
        sel_q_map = st.selectbox(
            "الربع على الخريطة",
            opts,
            index=q_idx,
            label_visibility="collapsed",
            key="map_quarter",
        )
        if sel_q_map != q_in_url:
            st.query_params.update(quarter=sel_q_map, view="map", province=province_param)
            st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

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
    
    # Create marker lookup for click handling
    marker_lookup = {
        (round(row[lat_col], 6), round(row[lon_col], 6)): str(row["METER_ID_STR"])
        for _, row in mosque_df.iterrows()
    }

    # Reset map state if returning from a redirect
    if "last_meter_redirect" in st.session_state:
        del st.session_state["last_meter_redirect"]
        st.session_state.province_map_nonce = st.session_state.get("province_map_nonce", 0) + 1

    if "province_map_nonce" not in st.session_state:
        st.session_state.province_map_nonce = 0

    try:
        province_geom = regions[regions["province_en"] == province_param].iloc[0].geometry
        province_geom_s = simplify_geom(province_geom, tolerance=0.02)
        map_center = [province_geom_s.centroid.y, province_geom_s.centroid.x]
    except Exception:
        map_center = [mosque_df[lat_col].mean(), mosque_df[lon_col].mean()]
        province_geom_s = None

    map_key = f"province_map_{province_param}_{sel_q_map}_{st.session_state.province_map_nonce}"
    fmap = folium.Map(location=map_center, zoom_start=7, tiles="CartoDB positron")
    
    # Add custom CSS for pin icons
    custom_css = """
    <style>
        .custom-pin-icon {
            background: none;
            border: none;
        }
        .custom-pin-icon i {
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
    </style>
    """
    fmap.get_root().html.add_child(folium.Element(custom_css))
    
    # Add province boundary
    if province_geom_s is not None:
        try:
            folium.GeoJson(
                data=province_geom_s.__geo_interface__,
                name="حدود المنطقة",
                style_function=lambda x: {"color": "#0B9444", "weight": 1.5, "fillOpacity": 0.04},
            ).add_to(fmap)
        except Exception:
            pass

    # Prepare marker data using cached function
    marker_data, marker_lookup = _prepare_marker_data(
        mosque_df.to_dict('records'),  # Convert to dict for caching
        lat_col,
        lon_col,
        province_param,
        sel_q_map
    )
    
    # JavaScript callback to create custom pin icons
    callback = """\
    function (row) {
        // Create a custom red pin icon using DivIcon with FontAwesome
        var icon = L.divIcon({
            html: '<i class="fa-solid fa-map-pin" style="color: #ff0000; font-size: 24px;"></i>',
            iconSize: [24, 24],
            iconAnchor: [12, 24],
            popupAnchor: [0, -24],
            className: 'custom-pin-icon'
        });
        var marker = L.marker(new L.LatLng(row[0], row[1]), {icon: icon});
        marker.bindPopup(row[2], {maxWidth: 300});
        return marker;
    }
    """
    
    # Add FastMarkerCluster with custom pin icons
    FastMarkerCluster(
        data=marker_data,
        callback=callback,
        name="مساجد مخالفة"
    ).add_to(fmap)

    # Display map with smart click detection
    ms = st_folium(
        fmap,
        width=None,
        height=700,
        key=map_key,
        returned_objects=["last_object_clicked"]
    )

    # Handle marker click - show details button below map
    clicked_meter_id = None
    clicked_mosque_name = None

    if ms and isinstance(ms.get("last_object_clicked"), dict):
        clicked_lat = ms["last_object_clicked"].get("lat")
        clicked_lon = ms["last_object_clicked"].get("lng") or ms["last_object_clicked"].get("lon")

        if clicked_lat is not None and clicked_lon is not None:
            key = (round(float(clicked_lat), 6), round(float(clicked_lon), 6))
            clicked_meter_id = marker_lookup.get(key)

            if clicked_meter_id:
                # Find mosque name for display
                mosque_row = mosque_df[mosque_df["METER_ID_STR"].astype(str) == clicked_meter_id]
                if not mosque_row.empty:
                    clicked_mosque_name = mosque_row.iloc[0].get("Name", "—")

    # Show navigation button when a marker is clicked
    if clicked_meter_id:
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown(
                f"""
                <div style="text-align:center;font-family:'Tajawal',sans-serif;direction:rtl;padding:15px;background:#f8f9fa;border-radius:10px;border:2px solid #0B9444;">
                    <p style="margin:0 0 5px 0;font-size:14px;color:#666;">المسجد المحدد:</p>
                    <p style="margin:0 0 10px 0;font-size:18px;font-weight:bold;color:#2b5d4a;">{clicked_mosque_name or clicked_meter_id}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
            if st.button("المزيد من التفاصيل ←", key="btn_goto_meter", type="primary", use_container_width=True):
                st.query_params.update(meter=clicked_meter_id, province=province_param, quarter=sel_q_map)
                st.rerun()

    st.stop()


from __future__ import annotations

from urllib.parse import quote_plus

import folium
import pandas as pd
import streamlit as st
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

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

    # Prepare data for FastMarkerCluster: [lat, lon, popup_html]
    marker_data = []
    for _, row in mosque_df.iterrows():
        meter_id = str(row["METER_ID_STR"])
        mosque_name = row.get("Name", "—")
        lat = row[lat_col]
        lon = row[lon_col]
        
        # Create popup HTML (compact design matching site theme)
        popup_html = f"""
        <div style="font-family: 'Tajawal', sans-serif; direction: rtl; min-width: 180px; 
                    background: #faf8f3; border: 1px solid #e1d9c6; border-radius: 12px; padding: 8px;">
            <h4 style="margin: 0 0 5px 0; color: #2b5d4a; font-size: 14px; border-bottom: 2px solid #0B9444; 
                       padding-bottom: 3px; font-weight: 700;">
                معلومات المسجد
            </h4>
            <p style="margin: 3px 0; font-size: 12px; line-height: 1.4;">
                <b style="color: #2b5d4a;">اسم المسجد:</b>
                <span style="color: #1a2f29; display: block; margin-top: 2px;">{mosque_name}</span>
            </p>
            <p style="margin: 3px 0 5px 0; font-size: 12px; line-height: 1.4;">
                <b style="color: #2b5d4a;">رقم العداد:</b>
                <span style="color: #1a2f29; display: block; margin-top: 2px;">{meter_id}</span>
            </p>
            <div style="margin-top: 8px; padding: 6px; background: #e7f4ee; border-radius: 6px; text-align: center;">
                <small style="color: #2b5d4a; font-size: 11px;">
                    انقر على المسجد لعرض التفاصيل
                </small>
            </div>
        </div>
        """
        
        marker_data.append([lat, lon, popup_html])
    
    # JavaScript callback to create custom pin icons
    callback = """\
    function (row) {
        // Create a custom blue mosque icon using DivIcon with FontAwesome
        var icon = L.divIcon({
            html: '<i class="fa fa-mosque fa-3x" style="color: #0b7fc4;"></i>',
            iconSize: [10, 10],
            iconAnchor: [17, 35],
            popupAnchor: [0, -35],
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

    # Display map with click detection
    ms = st_folium(
        fmap,
        width=None,
        height=650,
        key=map_key,
        returned_objects=["last_object_clicked", "last_clicked"],
    )

    # Handle marker clicks - navigate to meter details
    clicked_lat, clicked_lon = None, None
    if ms and isinstance(ms.get("last_object_clicked"), dict):
        clicked_lat = ms["last_object_clicked"].get("lat")
        clicked_lon = ms["last_object_clicked"].get("lng") or ms["last_object_clicked"].get("lon")
    if (clicked_lat is None or clicked_lon is None) and ms and isinstance(ms.get("last_clicked"), dict):
        clicked_lat = ms["last_clicked"].get("lat")
        clicked_lon = ms["last_clicked"].get("lng")

    if clicked_lat is not None and clicked_lon is not None:
        key = (round(float(clicked_lat), 6), round(float(clicked_lon), 6))
        meter_id = marker_lookup.get(key)
        if meter_id:
            if st.session_state.get("last_meter_redirect") != meter_id:
                st.session_state["last_meter_redirect"] = meter_id
                st.query_params.update(meter=meter_id, province=province_param, quarter=sel_q_map)
                st.rerun()

    st.stop()


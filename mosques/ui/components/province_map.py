from __future__ import annotations

import folium
import pandas as pd
import streamlit as st
from folium.plugins import FastMarkerCluster
from streamlit_folium import st_folium

from config import QUARTERS
from data import find_coord_cols
from domain import build_marker_payload, simplify_geom


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
        if st.button("⬅️ رجوع", key="btn_back_from_map"):
            back_q = st.query_params.get("quarter", QUARTERS[0])
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
        opts = [all_label] + QUARTERS
        q_in_url = st.query_params.get("quarter", QUARTERS[0])
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

    points, marker_lookup = build_marker_payload(metadata, violator_meters, lat_col, lon_col)
    if not points:
        st.info("لا توجد مواقع لعرضها.")
        st.stop()

    try:
        province_geom = regions[regions["province_en"] == province_param].iloc[0].geometry
        province_geom_s = simplify_geom(province_geom, tolerance=0.02)
        map_center = [province_geom_s.centroid.y, province_geom_s.centroid.x]
    except Exception:
        lat_mean = sum(p[0] for p in points) / len(points)
        lon_mean = sum(p[1] for p in points) / len(points)
        map_center = [lat_mean, lon_mean]
        province_geom_s = None

    map_key = f"province_map_{province_param}_{sel_q_map}"
    fmap = folium.Map(location=map_center, zoom_start=7, tiles="CartoDB positron")
    if province_geom_s is not None:
        try:
            folium.GeoJson(
                data=province_geom_s.__geo_interface__,
                name="حدود المنطقة",
                style_function=lambda x: {"color": "#0B9444", "weight": 1.5, "fillOpacity": 0.04},
            ).add_to(fmap)
        except Exception:
            pass

    FastMarkerCluster(data=points).add_to(fmap)

    ms = st_folium(
        fmap,
        width=None,
        height=650,
        key=map_key,
        returned_objects=["last_object_clicked", "last_clicked"],
    )

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
            st.query_params.update(meter=meter_id, province=province_param, quarter=sel_q_map)
            st.rerun()

    st.stop()


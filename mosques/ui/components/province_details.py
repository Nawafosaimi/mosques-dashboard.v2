from __future__ import annotations

import io
import math
import re
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

from config import QUARTERS
from domain import localize_booleans


def render_province_details(
    province_param: str,
    quarter_param: str,
    regions,
    metadata: pd.DataFrame,
    all_violator_data: dict,
):
    if not province_param or st.query_params.get("view", "") == "map":
        return False

    ar_province = regions.loc[regions["province_en"] == province_param, "name_ar"].iloc[0]
    hdr_left, hdr_center, hdr_right = st.columns([1, 2, 1])
    with hdr_left:
        if st.button("⬅️ رجوع", key="btn_back"):
            st.query_params.clear()
            st.rerun()
    with hdr_center:
        st.markdown(
            f'<div style="text-align:center;"><span style="font-size:40px;font-weight:600;">تفاصيل {ar_province}</span></div>',
            unsafe_allow_html=True,
        )
    with hdr_right:
        st.markdown("<div class='quarter-wrap'><p>الربع</p></div>", unsafe_allow_html=True)
        all_quarters_label = "كل الأرباع"
        quarter_options = [all_quarters_label] + QUARTERS
        q_idx = quarter_options.index(quarter_param) if quarter_param in quarter_options else 0
        selected_quarter = st.selectbox(
            "الربع التفصيلي",
            quarter_options,
            index=q_idx,
            label_visibility="collapsed",
            key="detail_quarter",
        )
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    open_map_col, _ = st.columns([1, 3])
    with open_map_col:
        if st.button("🗺️ فتح الخريطة التفاعلية", use_container_width=True, key="btn_open_map"):
            st.query_params.update(province=province_param, quarter=selected_quarter, view="map")
            st.rerun()

    if selected_quarter == all_quarters_label:
        table_q_all_provinces = pd.concat(all_violator_data.values(), ignore_index=True)
    else:
        table_q_all_provinces = all_violator_data.get(selected_quarter, pd.DataFrame()).copy()

    if table_q_all_provinces.empty:
        st.warning(f"لا توجد بيانات مخالفات متاحة لـ {selected_quarter}")
        st.stop()

    if "رقم العداد" in table_q_all_provinces.columns and "Province" in metadata.columns:
        allowed_meters = (
            metadata[metadata["Province"] == province_param]["METER_ID_STR"].astype(str).unique()
        )
        temp = table_q_all_provinces.copy()
        temp["رقم العداد"] = temp["رقم العداد"].astype(str)
        table_q = temp[temp["رقم العداد"].isin(allowed_meters)].copy()
    else:
        table_q = pd.DataFrame()

    total_mosques = (
        len(metadata[metadata["Province"] == province_param])
        if "Province" in metadata.columns
        else len(metadata)
    )
    violations_count = len(table_q.dropna(how="all"))

    k1, k2 = st.columns(2)
    k1.markdown(
        f"<div class='kpi'><div class='t'><b>عدد المساجد</b></div><div class='v'>{total_mosques:,}</div></div>",
        unsafe_allow_html=True,
    )
    k2.markdown(
        f"<div class='kpi'><div class='t'><b>عدد المساجد المتجاوزة</b></div><div class='v red'>{violations_count:,}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    display = table_q.dropna(how="all").reset_index(drop=True).copy()
    if "الموقع" in display.columns:
        display["الموقع"] = display["الموقع"].fillna("")

    display = localize_booleans(display)

    st.subheader("قائمة المساجد المتجاوزة")

    search_col, sort_col, order_col, export_col = st.columns([2, 1, 1, 1])
    with search_col:
        search_query = st.text_input("بحث", placeholder="ابحث...", label_visibility="collapsed")

    sortable_columns = [c for c in display.columns if c != "الموقع"]
    with sort_col:
        sort_column = st.selectbox("ترتيب حسب", options=[""] + sortable_columns, index=0)
    with order_col:
        sort_order = st.selectbox("الترتيب", options=["تصاعدي", "تنازلي"], index=1)

    df_filtered = display.copy()

    if search_query and search_query.strip():
        pattern = re.escape(search_query.strip())
        mask = df_filtered.astype(str).apply(lambda r: r.str.contains(pattern, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]

    if sort_column:
        ascending = sort_order == "تصاعدي"
        try:
            df_filtered[sort_column] = pd.to_numeric(df_filtered[sort_column], errors="coerce")
            df_filtered = df_filtered.sort_values(by=sort_column, ascending=ascending, na_position="last")
        except Exception:
            df_filtered = df_filtered.sort_values(
                by=sort_column,
                ascending=ascending,
                na_position="last",
                key=lambda col: col.astype(str),
            )

    df_filtered.reset_index(drop=True, inplace=True)

    export_df = df_filtered.copy()
    csv_bytes = io.BytesIO()
    export_df.to_csv(csv_bytes, index=False, encoding="utf-8-sig")
    csv_bytes.seek(0)
    with export_col:
        st.download_button(
            "⬇️ تصدير",
            data=csv_bytes,
            file_name=f"{ar_province}_{selected_quarter}.csv",
            mime="text/csv",
        )

    st.session_state.setdefault("detail_rows_per_page", 25)
    pag_col1, pag_col2, pag_col3 = st.columns([1, 1, 2])

    with pag_col1:
        rows_per_page = st.selectbox(
            "صفوف",
            [10, 25, 50, 100],
            key="detail_rows_per_page",
            label_visibility="collapsed",
        )

    total_rows = len(df_filtered)
    total_pages = max(1, math.ceil(total_rows / rows_per_page))

    if st.session_state.get("detail_last_quarter") != selected_quarter:
        st.session_state.detail_last_quarter = selected_quarter
        st.session_state.detail_page_idx = 0

    with pag_col2:
        page_num = st.number_input(
            "صفحة",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.detail_page_idx + 1,
            step=1,
            label_visibility="collapsed",
        )
        st.session_state.detail_page_idx = page_num - 1

    start = st.session_state.detail_page_idx * rows_per_page

    with pag_col3:
        st.markdown(
            f"<div class='pagination-summary'><small>عرض {min(start + 1, total_rows)}-{min(start + rows_per_page, total_rows)} من {total_rows} نتيجة</small></div>",
            unsafe_allow_html=True,
        )

    slice_df = df_filtered.iloc[start : start + rows_per_page].copy()

    q_enc, prov_enc = quote_plus(selected_quarter), quote_plus(province_param)
    if "رقم العداد" in slice_df.columns:
        slice_df["رقم العداد"] = slice_df["رقم العداد"].astype(str).apply(
            lambda x: f'<a href="?meter={quote_plus(x)}&quarter={q_enc}&province={prov_enc}" target="_self">{x}</a>'
        )
    if "الموقع" in slice_df.columns:
        slice_df["الموقع"] = slice_df["الموقع"].apply(
            lambda u: f'<a href="{u}" target="_blank">عرض</a>' if isinstance(u, str) and u.strip() else ""
        )

    html_table = slice_df.to_html(escape=False, index=False, classes="nice-table")
    st.markdown(f'<div class="tbl-card"><div class="tbl-scroll">{html_table}</div></div>', unsafe_allow_html=True)
    st.stop()


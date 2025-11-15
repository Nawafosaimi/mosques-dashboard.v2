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
    
    # Back button on the left
    back_col, _ = st.columns([1, 5])
    with back_col:
        if st.button("⬅️ رجوع", key="btn_back"):
            st.query_params.clear()
            st.rerun()
    
    # Title centered at the top
    st.markdown(
        f"<h1 style='text-align: center;'>تفاصيل  {ar_province}</h1>",
        unsafe_allow_html=True,
    )
    
    all_quarters_label = "كل الأرباع"
    quarter_options = [all_quarters_label] + QUARTERS
    q_idx = quarter_options.index(quarter_param) if quarter_param in quarter_options else 0

    # Row with KPIs and Filter + Map button
    _, kpi_col, filter_col, _ = st.columns([1.6, 1.5, 0.9, 0.6])
    
    with filter_col:
        st.markdown("<p class='filter-label'>اختر الربع</p>", unsafe_allow_html=True)
        selected_quarter = st.selectbox(
            "الربع",
            quarter_options,
            index=q_idx,
            key="detail_quarter",
            label_visibility="hidden",
        )
    
    # Map button below
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

    # Render KPIs in the middle column (same row as filter)
    with kpi_col:
        k1, k2 = st.columns([1, 1], gap="small")
        
        with k1:
            st.markdown(
                f"<div class='kpi'><div class='t'><b>عدد المساجد</b></div><div class='v'>{total_mosques:,}</div></div>",
                unsafe_allow_html=True,
            )
        
        with k2:
            st.markdown(
                f"<div class='kpi'><div class='t'><b>عدد المساجد المتجاوزة</b></div><div class='v red'>{violations_count:,}</div></div>",
                unsafe_allow_html=True,
            )

    display = table_q.dropna(how="all").reset_index(drop=True).copy()
    if "الموقع" in display.columns:
        display["الموقع"] = display["الموقع"].fillna("")

    display = localize_booleans(display)

    def _control_label(text: str) -> None:
        st.markdown(f"<p class='control-label'>{text}</p>", unsafe_allow_html=True)

    st.subheader("قائمة المساجد المتجاوزة")

    governorate_col_name = "المحافظة"
    period_col_name = next((c for c in display.columns if "الفترة" in c), None)

    search_col, sort_col, order_col, export_col = st.columns([3, 1.2, 1, 0.9])

    with search_col:
        _control_label("البحث")
        search_query = st.text_input(
            "بحث",
            placeholder="ابحث...",
            label_visibility="collapsed",
            key="detail_search",
        )

    sortable_columns = [c for c in display.columns if c != "الموقع"]
    with sort_col:
        _control_label("ترتيب حسب")
        sort_column = st.selectbox(
            "ترتيب حسب",
            options=[""] + sortable_columns,
            index=0,
            label_visibility="collapsed",
            key="detail_sort_column",
        )
    with order_col:
        _control_label("نوع الترتيب")
        sort_order = st.selectbox(
            "الترتيب",
            options=["تصاعدي", "تنازلي"],
            index=1,
            label_visibility="collapsed",
            key="detail_sort_order",
        )

    with export_col:
        _control_label("&nbsp;")
        export_placeholder = st.container()

    selected_governorate = ""
    selected_period = ""
    filter_row = st.columns([1.2, 1.2, 1.2])

    with filter_row[0]:
        if governorate_col_name in display.columns:
            _control_label("المحافظة")
            governorate_options = [""] + sorted(
                display[governorate_col_name].dropna().astype(str).unique().tolist()
            )
            selected_governorate = st.selectbox(
                "المحافظة",
                governorate_options,
                index=0,
                label_visibility="collapsed",
                key="detail_governorate",
            )
        else:
            st.markdown("&nbsp;", unsafe_allow_html=True)

    with filter_row[1]:
        if period_col_name and period_col_name in display.columns:
            _control_label("الفترة")
            period_options = [""] + sorted(
                display[period_col_name].dropna().astype(str).unique().tolist()
            )
            selected_period = st.selectbox(
                "الفترة",
                period_options,
                index=0,
                label_visibility="collapsed",
                key="detail_period",
            )
        else:
            st.markdown("&nbsp;", unsafe_allow_html=True)

    with filter_row[2]:
        st.markdown("&nbsp;", unsafe_allow_html=True)

    df_filtered = display.copy()
    search_term = search_query.strip() if search_query else ""

    if search_term:
        pattern = re.escape(search_term)
        mask = df_filtered.astype(str).apply(lambda r: r.str.contains(pattern, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask]

    if selected_governorate:
        df_filtered = df_filtered[df_filtered[governorate_col_name].astype(str) == selected_governorate]

    if selected_period and period_col_name in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[period_col_name].astype(str) == selected_period]

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

    st.session_state.setdefault("detail_rows_per_page", 25)
    st.session_state.setdefault("detail_page_idx", 0)

    pag_col1, pag_col2, pag_col3, pag_col4 = st.columns([2, 1, 1, 2])

    with pag_col1:
        _control_label("عدد الصفوف")
        rows_per_page = st.selectbox(
            "صفوف في الصفحة",
            [10, 25, 50, 100],
            key="detail_rows_per_page",
            label_visibility="collapsed",
        )

    total_rows = len(df_filtered)
    total_pages = max(1, math.ceil(total_rows / rows_per_page))

    if st.session_state.get("detail_last_quarter") != selected_quarter:
        st.session_state.detail_last_quarter = selected_quarter
        st.session_state.detail_page_idx = 0

    current_page_idx = st.session_state.detail_page_idx

    with pag_col2:
        _control_label("رقم الصفحة")
        page_num = st.number_input(
            "صفحة",
            min_value=1,
            max_value=total_pages,
            value=current_page_idx + 1,
            step=1,
            label_visibility="collapsed",
        )
        st.session_state.detail_page_idx = page_num - 1

    with pag_col3:
        _control_label("التنقل")
        prev_disabled = st.session_state.detail_page_idx <= 0
        next_disabled = st.session_state.detail_page_idx >= total_pages - 1
        prev_btn, next_btn = st.columns(2)
        if prev_btn.button("◀", disabled=prev_disabled, use_container_width=True, key="detail_prev_page"):
            st.session_state.detail_page_idx = max(0, st.session_state.detail_page_idx - 1)
            st.rerun()
        if next_btn.button("▶", disabled=next_disabled, use_container_width=True, key="detail_next_page"):
            st.session_state.detail_page_idx = min(total_pages - 1, st.session_state.detail_page_idx + 1)
            st.rerun()

    start = st.session_state.detail_page_idx * rows_per_page

    with pag_col4:
        st.markdown(
            f"<div class='pagination-summary'><small>عرض {min(start + 1, total_rows)}-{min(start + rows_per_page, total_rows)} من {total_rows} نتيجة</small></div>",
            unsafe_allow_html=True,
        )

    slice_df = df_filtered.iloc[start : start + rows_per_page].copy()

    # Export the rows currently displayed to the user
    export_bytes = io.BytesIO()
    slice_df.to_csv(export_bytes, index=False, encoding="utf-8-sig")
    export_bytes.seek(0)
    export_placeholder.download_button(
        "⬇️ تصدير النتائج الظاهرة",
        data=export_bytes,
        file_name=f"{ar_province}_{selected_quarter}_page_{st.session_state.detail_page_idx + 1}.csv",
        mime="text/csv",
    )

    slice_render_df = slice_df.copy()
    highlight_pattern = re.compile(re.escape(search_term), re.IGNORECASE) if search_term else None

    def _format_value(value: object) -> str:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        text = str(value)
        if highlight_pattern:
            return highlight_pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", text)
        return text

    for column in slice_render_df.columns:
        slice_render_df[column] = slice_render_df[column].apply(_format_value)

    q_enc, prov_enc = quote_plus(selected_quarter), quote_plus(province_param)
    meter_column = "رقم العداد"
    if meter_column in slice_df.columns:
        plain_series = slice_df[meter_column].astype(str)
        display_series = slice_render_df[meter_column].astype(str)
        slice_render_df[meter_column] = [
            f'<a href="?meter={quote_plus(plain)}&quarter={q_enc}&province={prov_enc}" target="_self">{display}</a>'
            for plain, display in zip(plain_series, display_series)
        ]

    if "الموقع" in slice_df.columns:
        slice_render_df["الموقع"] = [
            f'<a href="{link}" target="_blank">عرض</a>' if isinstance(link, str) and link.strip() else ""
            for link in slice_df["الموقع"]
        ]

    html_table = slice_render_df.to_html(escape=False, index=False, classes="nice-table")
    st.markdown(f'<div class="tbl-card"><div class="tbl-scroll">{html_table}</div></div>', unsafe_allow_html=True)
    st.stop()


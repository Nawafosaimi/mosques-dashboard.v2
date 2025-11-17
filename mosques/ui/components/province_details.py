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

    # Title at the top
    st.markdown(f"<h1 style='text-align: center;'>تفاصيل {ar_province}</h1>", unsafe_allow_html=True)

    # Navigation buttons on the left
    back_col, map_col, _ = st.columns([1, 1, 3.5])
    with back_col:
        if st.button("⬅️ رجوع", key="btn_back", use_container_width=True):
            st.query_params.clear()
            st.rerun()
    with map_col:
        if st.button("🗺️ فتح الخريطة", key="btn_open_map", use_container_width=True):
            st.query_params.update(province=province_param, quarter=quarter_param, view="map")
            st.rerun()

    # Setup quarters and selection
    all_quarters_label = "كل الأرباع"
    quarter_options = [all_quarters_label] + QUARTERS
    q_idx = quarter_options.index(quarter_param) if quarter_param in quarter_options else 0

    # Row with KPIs on left and Filter on right (same layout as overview)
    _, kpi_col, _, filter_col = st.columns([0.1, 1.2, 0.2, 2])

    with filter_col:
        spacer, filter_inner_col, _ = st.columns([0.5, 0.9, 0.6])
        with filter_inner_col:
            st.markdown("<p class='filter-label'>اختر الربع</p>", unsafe_allow_html=True)
            selected_quarter = st.selectbox(
                "الربع",
                quarter_options,
                index=q_idx,
                key="detail_quarter",
                label_visibility="hidden",
            )

    # Get data for selected quarter
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

    # Helper function for delta calculation (same as overview)
    def _quarter_count(label: str | None) -> int:
        if not label:
            return 0
        df = all_violator_data.get(label)
        if df is None or not isinstance(df, pd.DataFrame):
            return 0
        if "رقم العداد" not in df.columns or "Province" not in metadata.columns:
            return 0
        allowed_meters = (
            metadata[metadata["Province"] == province_param]["METER_ID_STR"].astype(str).unique()
        )
        temp = df.copy()
        temp["رقم العداد"] = temp["رقم العداد"].astype(str)
        filtered = temp[temp["رقم العداد"].isin(allowed_meters)]
        return len(filtered.dropna(how="all"))

    def _build_delta_html(
        current_count: int,
        previous_count: int | None,
        previous_label: str | None,
        prefer_lower: bool = False,
    ) -> str:
        if previous_label is None or previous_count is None:
            return "<div class='delta neutral'>أول فترة متاحة</div>"
        if previous_count == 0:
            return "<div class='delta neutral'>لا توجد بيانات للمقارنة</div>"
        diff = current_count - previous_count
        if diff == 0:
            return f"<div class='delta flat'>بدون تغيير مقارنة بـ {previous_label}</div>"
        pct = (diff / previous_count) * 100
        if prefer_lower:
            direction = "up" if diff < 0 else "down"
        else:
            direction = "up" if diff > 0 else "down"
        diff_text = f"{diff:+,}"
        pct_text = f"{pct:+.1f}%"
        return f"<div class='delta {direction}'>{diff_text} ({pct_text}) مقارنة بـ {previous_label}</div>"

    # Prepare delta HTML for violations
    if selected_quarter == all_quarters_label:
        violations_delta_html = f"<div class='delta neutral'>إجمالي {len(QUARTERS)} أرباع</div>"
        mosques_delta_html = f"<div class='delta neutral'>مجموع {len(QUARTERS)} أرباع</div>"
    else:
        current_idx = QUARTERS.index(selected_quarter)
        previous_label = QUARTERS[current_idx - 1] if current_idx > 0 else None
        previous_count = _quarter_count(previous_label) if previous_label else None
        current_count = _quarter_count(selected_quarter)
        violations_delta_html = _build_delta_html(
            current_count, previous_count, previous_label, prefer_lower=True
        )
        mosques_delta_html = f"<div class='delta neutral'>محدّث حتى {selected_quarter}</div>"

    # Render KPIs in the middle column (same style as overview page)
    with kpi_col:
        k1, k2 = st.columns([1, 1], gap="small")

        with k1:
            st.markdown(
                (
                    "<div class='kpi'>"
                    "<div class='t'><b>عدد المساجد</b></div>"
                    f"<div class='v'>{total_mosques:,}</div>"
                    f"{mosques_delta_html}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

        with k2:
            st.markdown(
                (
                    "<div class='kpi'>"
                    "<div class='t'><b>عدد المساجد المتجاوزة</b></div>"
                    f"<div class='v red'>{violations_count:,}</div>"
                    f"{violations_delta_html}"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    # Prepare display dataframe
    display = table_q.dropna(how="all").reset_index(drop=True).copy()
    if "الموقع" in display.columns:
        display["الموقع"] = display["الموقع"].fillna("")

    display = localize_booleans(display)

    # Section title
    st.subheader("قائمة المساجد المتجاوزة")

    governorate_col_name = "المحافظة"
    period_col_name = next((c for c in display.columns if "الفترة" in c), None)

    def _control_label(text: str) -> None:
        st.markdown(f"<p class='control-label'>{text}</p>", unsafe_allow_html=True)

    # Search and Export Row
    search_col, export_col = st.columns([4, 1])

    with search_col:
        _control_label("البحث")
        search_query = st.text_input(
            "بحث",
            placeholder="ابحث...",
            label_visibility="collapsed",
            key="detail_search",
        )

    with export_col:
        _control_label("تصدير")
        export_placeholder = st.container()

    # Sort and Filter Row
    st.markdown('<div data-table-controls="province-filters">', unsafe_allow_html=True)
    sortable_columns = [c for c in display.columns if c != "الموقع"]
    sort_options = [""] + sortable_columns
    
    # Initialize session state for sorting
    if "detail_sort_column" not in st.session_state:
        st.session_state.detail_sort_column = ""
    if "detail_sort_order" not in st.session_state:
        st.session_state.detail_sort_order = "تنازلي"
    
    # Find current index
    try:
        sort_idx = sort_options.index(st.session_state.detail_sort_column)
    except ValueError:
        sort_idx = 0
    
    order_options = ["تصاعدي", "تنازلي"]
    try:
        order_idx = order_options.index(st.session_state.detail_sort_order)
    except ValueError:
        order_idx = 1
    
    sort_col, order_col, gov_col_widget, period_col_widget = st.columns([1, 1, 1, 1])

    with sort_col:
        _control_label("ترتيب حسب")
        sort_column = st.selectbox(
            "ترتيب حسب",
            options=sort_options,
            index=sort_idx,
            label_visibility="collapsed",
            key="_detail_sort_column_widget",
        )
        if sort_column != st.session_state.detail_sort_column:
            st.session_state.detail_sort_column = sort_column
            st.rerun()

    with order_col:
        _control_label("الترتيب")
        sort_order = st.selectbox(
            "الترتيب",
            options=order_options,
            index=order_idx,
            label_visibility="collapsed",
            key="_detail_sort_order_widget",
        )
        if sort_order != st.session_state.detail_sort_order:
            st.session_state.detail_sort_order = sort_order
            st.rerun()

    selected_governorate = ""
    selected_period = ""

    with gov_col_widget:
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

    with period_col_widget:
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

    st.markdown('</div>', unsafe_allow_html=True)

    # Apply filters - use deep copy to prevent modification of original data
    df_filtered = display.copy(deep=True)
    search_term = search_query.strip() if search_query else ""

    if search_term:
        pattern = re.escape(search_term)
        mask = df_filtered.astype(str).apply(lambda r: r.str.contains(pattern, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask].copy()

    if selected_governorate:
        df_filtered = df_filtered[df_filtered[governorate_col_name].astype(str) == selected_governorate].copy()

    if selected_period and period_col_name in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[period_col_name].astype(str) == selected_period].copy()

    # Use session state values for sorting
    sort_column = st.session_state.detail_sort_column
    sort_order = st.session_state.detail_sort_order
    
    if sort_column and sort_column != "":
        ascending = sort_order == "تصاعدي"
        # Debug: Show what we're sorting
        # st.write(f"DEBUG: Sorting by '{sort_column}' - {'تصاعدي' if ascending else 'تنازلي'}")
        
        try:
            # Try numeric sorting first
            sort_series = pd.to_numeric(df_filtered[sort_column], errors="coerce")
            # Check if we have any valid numeric values
            if sort_series.notna().any():
                # Numeric sorting - create sorted index
                df_filtered["_sort_key"] = sort_series
                df_filtered = df_filtered.sort_values(
                    by="_sort_key",
                    ascending=ascending,
                    na_position="last"
                ).drop(columns=["_sort_key"], errors="ignore").copy()
            else:
                # All values are non-numeric, use string sorting
                df_filtered = df_filtered.sort_values(
                    by=sort_column,
                    ascending=ascending,
                    na_position="last",
                    key=lambda x: x.astype(str).str.lower()
                ).copy()
        except Exception as e:
            # Fallback to simple string sorting
            st.warning(f"خطأ في الترتيب: {str(e)}")
            df_filtered = df_filtered.sort_values(
                by=sort_column,
                ascending=ascending,
                na_position="last"
            ).copy()

    df_filtered = df_filtered.reset_index(drop=True)

    # Pagination state
    st.session_state.setdefault("detail_rows_per_page", 50)
    st.session_state.setdefault("detail_page_idx", 0)

    # Pagination Controls
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

    # Clamp to valid range
    st.session_state.detail_page_idx = min(st.session_state.detail_page_idx, total_pages - 1)
    st.session_state.detail_page_idx = max(0, st.session_state.detail_page_idx)
    current_page_idx = st.session_state.detail_page_idx

    with pag_col3:
        _control_label("التنقل")
        prev_disabled = current_page_idx <= 0
        next_disabled = current_page_idx >= total_pages - 1
        next_btn, prev_btn = st.columns(2)
        if next_btn.button("▶", disabled=next_disabled, use_container_width=True, key="detail_next_page"):
            st.session_state.detail_page_idx = min(total_pages - 1, current_page_idx + 1)
            st.rerun()
        if prev_btn.button("◀", disabled=prev_disabled, use_container_width=True, key="detail_prev_page"):
            st.session_state.detail_page_idx = max(0, current_page_idx - 1)
            st.rerun()

    with pag_col2:
        _control_label("رقم الصفحة")
        page_options = list(range(1, total_pages + 1))
        selected_page = st.selectbox(
            "صفحة",
            options=page_options,
            index=current_page_idx,
            label_visibility="collapsed",
            key="detail_page_select",
        )
        # Only update if user changed it via dropdown (not via buttons)
        if selected_page - 1 != current_page_idx:
            st.session_state.detail_page_idx = selected_page - 1
            st.rerun()

    start = st.session_state.detail_page_idx * rows_per_page

    with pag_col4:
        st.markdown(
            f"<div class='pagination-summary'><small>عرض {min(start + 1, total_rows)}-{min(start + rows_per_page, total_rows)} من {total_rows} نتيجة</small></div>",
            unsafe_allow_html=True,
        )

    # Prepare data for table
    slice_df = df_filtered.iloc[start : start + rows_per_page].copy()

    # Export button
    export_bytes = io.BytesIO()
    slice_df.to_csv(export_bytes, index=False, encoding="utf-8-sig")
    export_bytes.seek(0)
    export_placeholder.download_button(
        "⬇️ تصدير النتائج الظاهرة",
        data=export_bytes,
        file_name=f"{ar_province}_{selected_quarter}_page_{st.session_state.detail_page_idx + 1}.csv",
        mime="text/csv",
    )

    # Format table data with search highlighting
    slice_render_df = slice_df.copy()
    highlight_pattern = re.compile(re.escape(search_term), re.IGNORECASE) if search_term else None

    def _format_value(value: object) -> str:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        text = str(value)
        if highlight_pattern:
            return highlight_pattern.sub(lambda m: f"<mark style='background:#ffe9b5;padding:2px 4px;border-radius:3px;'>{m.group(0)}</mark>", text)
        return text

    for column in slice_render_df.columns:
        slice_render_df[column] = slice_render_df[column].apply(_format_value)

    # Add clickable links
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
            f'<a href="{link}" target="_blank" title="عرض الموقع">رابط الموقع</a>' if isinstance(link, str) and link.strip() else ""
            for link in slice_df["الموقع"]
        ]

    # Render table with your custom styling
    html_table = slice_render_df.to_html(escape=False, index=False, classes="nice-table")
    st.markdown(f'<div class="tbl-card"><div class="tbl-scroll">{html_table}</div></div>', unsafe_allow_html=True)
    st.stop()

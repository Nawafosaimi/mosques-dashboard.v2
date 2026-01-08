from __future__ import annotations

import io
import math
import re
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

import config
from domain import localize_booleans
from data import load_visits_data, get_visited_meter_ids, get_visit_stats
from .kpi_card import render_kpi_card
from .header import render_header





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

    ar_province = regions.loc[regions["province_en"] == province_param, "name_ar"].iloc[0]

    # Render header with ministry logo
    render_header()

    # Title at the top
    st.markdown(f"<h1 style='text-align: center;'>تفاصيل {ar_province}</h1>", unsafe_allow_html=True)

    # Navigation buttons on the left - smaller and equal size
    _, back_col, map_col, _ = st.columns([0.2, 0.8, 0.8, 5.2])
    with back_col:
        if st.button(" رجوع", key="btn_back", use_container_width=True):
            st.query_params.clear()
            st.rerun()
    with map_col:
        if st.button(" فتح الخريطة التفاعلية", key="btn_open_map", use_container_width=True):
            st.query_params.update(province=province_param, quarter=quarter_param, view="map")
            st.rerun()

    # Setup quarters and selection
    all_quarters_label = "كل الأرباع"
    
    # Robust deduplication: ensure all labels are unique and stripped
    all_options = [all_quarters_label] + config.QUARTERS
    quarter_options = []
    seen = set()
    for opt in all_options:
        if not opt: continue
        clean_opt = str(opt).strip()
        if clean_opt and clean_opt not in seen:
            quarter_options.append(clean_opt)
            seen.add(clean_opt)
    
    # Determine index for selectbox
    if quarter_param in config.QUARTERS:
        q_idx = quarter_options.index(quarter_param)
    elif quarter_param == all_quarters_label:
        q_idx = 0
    else:
        q_idx = 0

    # Date legend helper
    def _get_quarter_legend(q_name):
        if q_name in config.QUARTER_DATES:
            start, end = config.QUARTER_DATES[q_name]
            # Format: 1 Jan - 31 Mar
            return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"
        return ""

    # Row with KPIs on left and Filter on right
    # Using more flexible proportions to allow dynamic KPI width
    _, kpi_col, _, filter_col = st.columns([0.08, 1.8, 0.15, 2.2], gap="medium")

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
        # Deduplicate by meter ID to count unique mosques
        if "رقم العداد" in table_q_all_provinces.columns:
            table_q_all_provinces = table_q_all_provinces.drop_duplicates(subset=["رقم العداد"], keep="first")
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

    # Load visits data and calculate stats
    visits_df = load_visits_data()
    
    # Filter visits_df based on selected quarter date range to match table logic
    if selected_quarter != all_quarters_label and selected_quarter in config.QUARTER_DATES:
        q_start, q_end = config.QUARTER_DATES[selected_quarter]
        # Ensure we have datetime objects for comparison
        if "التاريخ الميلادي (تقريبي)" in visits_df.columns:
            # Parse dates if strictly needed, or do it more efficiently
            # We reuse the logic from get_visit_status but vectorized
             try:
                visits_df["_dt_temp"] = pd.to_datetime(visits_df["التاريخ الميلادي (تقريبي)"], dayfirst=True, errors='coerce')
                visits_df = visits_df[
                    (visits_df["_dt_temp"] >= q_start) & 
                    (visits_df["_dt_temp"] <= q_end)
                ].copy()
             except Exception:
                 pass # Fallback to using all if parsing fails to avoid empty

    violator_meter_ids = set(table_q["رقم العداد"].astype(str).str.strip().unique()) if "رقم العداد" in table_q.columns else set()
    visited_meter_ids = get_visited_meter_ids(visits_df)
    visit_stats = get_visit_stats(visits_df, violator_meter_ids)

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
            return f"<div class='delta flat'>بدون تغيير مقارنة بالربع السابق {previous_label}</div>"
        pct = (diff / previous_count) * 100
        if diff > 0:
            direction = "up" if not prefer_lower else "down"
            arrow = "↑"
        elif diff < 0:
            direction = "down" if not prefer_lower else "up"
            arrow = "↓"
        else:
            direction = "neutral"
            arrow = ""

        diff_text = f"{diff:+,}"
        pct_text = f"{pct:+.1f}%"
        
        # Badge Style with Flexbox: Text [Right] | Badge [Left]
        badge_html = f"<span class='delta-badge {direction}'>{pct_text} {arrow}</span>"
        text_html = f"<span>{diff_text} مقارنة بالربع السابق </span>"
        return f"<div class='delta {direction}'>{text_html}{badge_html}</div>"

    # Prepare delta HTML for violations
    if selected_quarter == all_quarters_label:
        violations_delta_html = f"<div class='delta neutral'>إجمالي {len(config.QUARTERS)} أرباع</div>"
        mosques_delta_html = f"<div class='delta neutral'>مجموع {len(config.QUARTERS)} أرباع</div>"
    else:
        current_idx = config.QUARTERS.index(selected_quarter)
        previous_label = config.QUARTERS[current_idx - 1] if current_idx > 0 else None
        previous_count = _quarter_count(previous_label) if previous_label else None
        current_count = _quarter_count(selected_quarter)
        violations_delta_html = _build_delta_html(
            current_count, previous_count, previous_label, prefer_lower=True
        )
        mosques_delta_html = f"<div class='delta neutral'>محدّث حتى {selected_quarter}</div>"

    # Render KPIs in the middle column (dynamic width based on content)
    with kpi_col:
        # Increase width for Violations (middle) and Visited (right) cards to fit text
        k1, k2, k3 = st.columns([3.9, 4.8, 2.3], gap="medium")

        with k1:
            render_kpi_card(
                title=f"عدد المساجد في {ar_province}",
                value=f"{total_mosques:,}",
                delta_html=mosques_delta_html,
                tooltip="إجمالي عدد المساجد المسجلة في هذه المنطقة"
            )

        with k2:
            kpi_title = "عدد المساجد المتجاوزة"
            if selected_quarter != all_quarters_label:
                kpi_title = f"عدد المساجد المتجاوزة في {selected_quarter}"
            
            render_kpi_card(
                title=kpi_title,
                value=f"{violations_count:,}",
                delta_html=violations_delta_html,
                value_color_class="red",
                tooltip="المساجد المتاجاوزة خلال الربع"
            )

        with k3:
            render_kpi_card(
                title="تمت زيارتهم",
                value=f"{visit_stats['total_visited']:,}",
                delta_html=f"<div class='delta neutral'>من  {violations_count:,} مسجد</div>",
                tooltip="عدد المساجد المتجاوزة التي تمت زيارتها ميدانياً"
            )

    # Prepare display dataframe
    display = table_q.dropna(how="all").reset_index(drop=True).copy()
    if "الموقع" in display.columns:
        display["الموقع"] = display["الموقع"].fillna("")

    # Add merged "Visit Status" (حالة الزيارة) with date filtering
    if "رقم العداد" in display.columns:
        # Get quarter date range
        q_start, q_end = config.QUARTER_DATES.get(selected_quarter, (None, None))
        
        def _get_visit_display(meter_val):
            meter_id = str(meter_val).strip()
            if meter_id not in visited_meter_ids:
                return "لا"
                
            # If visited, check date
            # We need to look up the date for this specific meter
            # Optimization: Pre-fetch dates if not already done
            return "نعم" # Fallback if specific date logic needs the dataframe lookup below

        # Create map for visit dates
        visit_date_map = {}
        if not visits_df.empty and "رقم عداد الكهرباء" in visits_df.columns:
            date_col = 'التاريخ الميلادي (تقريبي)'
            if date_col in visits_df.columns:
                visit_date_map = dict(zip(
                    visits_df["رقم عداد الكهرباء"].astype(str).str.strip(), 
                    visits_df[date_col]
                ))

        def _resolve_visit_status(meter_val):
             meter_id = str(meter_val).strip()
             if meter_id not in visited_meter_ids:
                 return "لا"
             
             date_str = visit_date_map.get(meter_id)
             if not date_str:
                 return "تمت الزيارة (تاريخ غير محدد)"
                 
             # Check if date is in quarter range
             try:
                 visit_date = pd.to_datetime(date_str, dayfirst=True).to_pydatetime()
                 if q_start and q_end:
                     if q_start <= visit_date <= q_end:
                         return f"تمت الزيارة ({date_str})"
                     else:
                         # Visited but not in this quarter
                         return "لا"
                 else:
                     # No quarter selected (or 'All Quarters'), show date
                     return f"تمت الزيارة ({date_str})"
             except:
                 # Date parse failed, treat as visited
                 return f"تمت الزيارة ({date_str})"

        display["حالة الزيارة"] = display["رقم العداد"].astype(str).str.strip().apply(_resolve_visit_status)
    
    # Remove old columns if they exist (cleanup)
    display = display.drop(columns=["تمت الزيارة", "تاريخ الزيارة"], errors="ignore")

    display = localize_booleans(display)

    # Fix column name and values for Period
    if "الفترة صباحا/مساءا" in display.columns:
        display = display.rename(columns={"الفترة صباحا/مساءا": "الفترة صباحا/مساء"})
    
    if "الفترة صباحا/مساء" in display.columns:
        display["الفترة صباحا/مساء"] = display["الفترة صباحا/مساء"].replace("مساءا", "مساء")

    # Fix column name for Consumption
    if "قيمة الفاتورة الإجمالي" in display.columns:
        display = display.rename(columns={"قيمة الفاتورة الإجمالي": "قيمة الاستهلاك الإجمالي"})
    elif "قيمة الفاتورة" in display.columns:
        display = display.rename(columns={"قيمة الفاتورة": "قيمة الاستهلاك الإجمالي"})

    # Enforce consistent column order
    preferred_order = [
        "اسم المسجد",
        "رقم العداد",
        "المحافظة",
        "الفترة صباحا/مساء",
        "قيمة الاستهلاك الإجمالي",
        "مخالف سابقا",
        "حالة الزيارة",
        "الموقع",
    ]
    existing_cols = display.columns.tolist()
    ordered_cols = [col for col in preferred_order if col in existing_cols]
    # Keep المحافظة_الورقة in the dataframe for filtering, but don't include in display order
    remaining_cols = [col for col in existing_cols if col not in ordered_cols and col != "المحافظة_الورقة"]
    final_order = ordered_cols + remaining_cols
    # Add المحافظة_الورقة at the end if it exists (for filtering purposes)
    if "المحافظة_الورقة" in existing_cols:
        final_order = final_order + ["المحافظة_الورقة"]
    display = display[final_order]

    governorate_col_name = "المحافظة"
    period_col_name = next((c for c in display.columns if "الفترة" in c), None)

    def _control_label(text: str) -> None:
        st.markdown(f"<p class='control-label'>{text}</p>", unsafe_allow_html=True)

    # Initialize session state for sorting
    sortable_columns = [c for c in display.columns if c not in ["الموقع", "المحافظة_الورقة"]]
    sort_options = sortable_columns

    # Set default sort column to قيمة الاستهلاك الإجمالي if it exists
    default_sort_column = "قيمة الاستهلاك الإجمالي" if "قيمة الاستهلاك الإجمالي" in sortable_columns else (sortable_columns[0] if sortable_columns else "")

    if "detail_sort_column" not in st.session_state:
        st.session_state.detail_sort_column = default_sort_column
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

    # Pagination state setup (needed before building the row)
    st.session_state.setdefault("detail_rows_per_page", 50)
    st.session_state.setdefault("detail_page_idx", 0)

    # Sheet filter state setup
    st.session_state.setdefault("detail_sheet_filter", "الكل")

    # All controls in one row: title, search, sort, filters, and export (pagination moved to bottom)
    st.markdown('<div data-table-controls="province-filters">', unsafe_allow_html=True)
    title_col, search_col, sort_col, order_col, sheet_col, gov_col, period_col, visit_col, export_col = st.columns([1.3, 0.9, 0.8, 0.7, 0.7, 0.8, 0.7, 0.7, 0.5])

    with title_col:
        # We will update this later with the filtered count
        title_placeholder = st.empty()
        title_placeholder.markdown(f"<h4 style='margin-top: 10px; margin-bottom: 0;'>قائمة المساجد المتجاوزة</h4>", unsafe_allow_html=True)

    with search_col:
        _control_label("البحث")
        search_query = st.text_input(
            "بحث",
            placeholder="ابحث...",
            label_visibility="collapsed",
            key="detail_search",
        )

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

    # Sheet filter
    selected_sheet = ""
    with sheet_col:
        if "المحافظة_الورقة" in table_q.columns:
            _control_label("اتجاة المحافظات")
            
            # Get available sheet options
            sheet_values = table_q["المحافظة_الورقة"].dropna().astype(str).unique().tolist()
            
            # Only show dropdown if there are actual values to filter by
            if len(sheet_values) > 0:
                sheet_options = ["الكل"] + sorted(sheet_values)
                # Find current index
                try:
                    sheet_idx = sheet_options.index(st.session_state.detail_sheet_filter)
                except ValueError:
                    sheet_idx = 0

                selected_sheet = st.selectbox(
                    "اتجاة المحافظات",
                    sheet_options,
                    index=sheet_idx,
                    label_visibility="collapsed",
                    key="detail_sheet_filter",
                )
                # Value is automatically updated in st.session_state.detail_sheet_filter due to key
            else:
                # No sheet data available - show disabled dropdown
                st.selectbox(
                    "اتجاة المحافظات",
                    ["لا يوجد"],
                    index=0,
                    disabled=True,
                    label_visibility="collapsed",
                    key="detail_sheet_filter",
                )
                # Ensure state is consistent
                if st.session_state.detail_sheet_filter != "الكل":
                     st.session_state.detail_sheet_filter = "الكل"
                     st.rerun()

    selected_governorate = ""
    selected_period = ""

    with gov_col:
        if governorate_col_name in display.columns:
            _control_label("المحافظة")
            
            # Dependent Filter Logic: Filter options based on selected sheet (Direction)
            gov_source_df = display
            if selected_sheet and selected_sheet != "الكل" and "المحافظة_الورقة" in display.columns:
                gov_source_df = display[display["المحافظة_الورقة"].astype(str) == selected_sheet]
                
            governorate_options = ["الكل"] + sorted(
                gov_source_df[governorate_col_name].dropna().astype(str).unique().tolist()
            )
            
            # Handle case where previously selected governorate is no longer valid
            current_gov = st.session_state.get("detail_governorate", "الكل")
            gov_index = 0
            if current_gov in governorate_options:
                gov_index = governorate_options.index(current_gov)
            
            selected_governorate = st.selectbox(
                "المحافظة",
                governorate_options,
                index=gov_index,
                label_visibility="collapsed",
                key="detail_governorate",
            )


    with period_col:
        if period_col_name and period_col_name in display.columns:
            _control_label("الفترة")
            # Get unique period values safely
            period_series = display[period_col_name].dropna().astype(str)
            period_options = ["الكل"] + sorted(list(set(period_series)))
            selected_period = st.selectbox(
                "الفترة",
                period_options,
                index=0,
                label_visibility="collapsed",
                key="detail_period",
            )
        else:
            selected_period = ""

    # Visit status filter
    selected_visit_status = ""
    with visit_col:
        # Always show visit status filter
        _control_label("حالة الزيارة")
        visit_status_options = ["الكل", "تمت الزيارة", "لم تتم الزيارة"]
        selected_visit_status = st.selectbox(
            "حالة الزيارة",
            visit_status_options,
            index=0,
            label_visibility="collapsed",
            key="detail_visit_status",
        )


    with export_col:
        _control_label("‎ ")
        # Placeholder for export - will export filtered data
        export_placeholder = st.empty()

    st.markdown('</div>', unsafe_allow_html=True)

    # --- NEW: Floating HUD Pill Logic (Fast & Native) ---
    active_filters_count = 0
    if search_query and search_query.strip():
        active_filters_count += 1
    if st.session_state.get("detail_sheet_filter", "الكل") != "الكل":
        active_filters_count += 1
    if st.session_state.get("detail_governorate", "الكل") != "الكل":
        active_filters_count += 1
    if st.session_state.get("detail_period", "الكل") != "الكل":
        active_filters_count += 1
    if st.session_state.get("detail_visit_status", "الكل") != "الكل":
        active_filters_count += 1

    if active_filters_count > 0:
        def reset_filters_native():
            st.session_state.detail_search = ""
            st.session_state.detail_sheet_filter = "الكل"
            st.session_state.detail_governorate = "الكل"
            st.session_state.detail_period = "الكل"
            st.session_state.detail_visit_status = "الكل"
            st.session_state.detail_page_idx = 0
            
        # We render a button with a unique label structure for CSS targeting
        # Format: (Count) | فلاتر نشطة | مسح الكل ✕
        st.button(
            f"{active_filters_count} | فلاتر نشطة | مسح الكل ✕", 
            key="hud_pill_native_btn", 
            on_click=reset_filters_native
        )
    
    # Rows per page value - use session state default
    rows_per_page = st.session_state.get("detail_rows_per_page", 50)

    # Apply filters - use deep copy to prevent modification of original data
    df_filtered = display.copy(deep=True)
    search_term = search_query.strip() if search_query else ""

    if search_term:
        pattern = re.escape(search_term)
        mask = df_filtered.astype(str).apply(lambda r: r.str.contains(pattern, case=False, na=False)).any(axis=1)
        df_filtered = df_filtered[mask].copy()

    # Apply sheet filter
    if selected_sheet and selected_sheet != "الكل" and "المحافظة_الورقة" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["المحافظة_الورقة"].astype(str) == selected_sheet].copy()

    if selected_governorate and selected_governorate != "الكل":
        df_filtered = df_filtered[df_filtered[governorate_col_name].astype(str) == selected_governorate].copy()

    if selected_period and selected_period != "الكل" and period_col_name in df_filtered.columns:
        df_filtered = df_filtered[df_filtered[period_col_name].astype(str) == selected_period].copy()

    # Apply visit status filter
    if selected_visit_status and selected_visit_status != "الكل" and "حالة الزيارة" in df_filtered.columns:
        if selected_visit_status == "تمت الزيارة":
            # Match strictly "تمت الزيارة..." which includes the date
            df_filtered = df_filtered[df_filtered["حالة الزيارة"].astype(str).str.startswith("تمت الزيارة")].copy()
        elif selected_visit_status == "لم تتم الزيارة":
            df_filtered = df_filtered[df_filtered["حالة الزيارة"] == "لا"].copy()

    # Calculate pagination based on filtered data
    total_rows = len(df_filtered)
    
    # Update title with filtered count
    title_placeholder.markdown(
        f"<h4 style='margin-top: 10px; margin-bottom: 0;'>قائمة المساجد المتجاوزة <span style='font-size: 0.8em; color: #2b5d4a;'>({total_rows})</span></h4>",
        unsafe_allow_html=True
    )
    
    total_pages = max(1, math.ceil(total_rows / rows_per_page))
    
    
    total_pages = max(1, math.ceil(total_rows / rows_per_page))

    # Reset to page 1 if quarter changed
    if st.session_state.get("detail_last_quarter") != selected_quarter:
        st.session_state.detail_last_quarter = selected_quarter
        st.session_state.detail_page_idx = 0

    # Clamp to valid range (in case data shrinks)
    if st.session_state.detail_page_idx >= total_pages:
        st.session_state.detail_page_idx = total_pages - 1
    if st.session_state.detail_page_idx < 0:
        st.session_state.detail_page_idx = 0


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

    # Populate the export button with sorted and filtered data
    with export_placeholder.container():
        # Exclude internal tracking columns from export
        export_df = df_filtered.drop(columns=["المحافظة_الورقة"], errors="ignore")
        
        # Format links as Excel hyperlinks if column exists
        if "الموقع" in export_df.columns:
            export_df["الموقع"] = export_df["الموقع"].apply(
                lambda x: f'=HYPERLINK("{x}", "رابط الموقع")' if isinstance(x, str) and x.strip() else ""
            )
        
        # Generate timestamp for filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        export_bytes = io.BytesIO()
        export_df.to_csv(export_bytes, index=False, encoding="utf-8-sig")
        export_bytes.seek(0)
        st.download_button(
            " تصدير",
            data=export_bytes,
            file_name=f"{ar_province}_{selected_quarter}_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
            key="export_filtered_data",
        )

    # Calculate start index for slicing
    start = st.session_state.detail_page_idx * rows_per_page

    # Prepare data for table
    slice_df = df_filtered.iloc[start : start + rows_per_page].copy()

    # Format table data with search highlighting
    slice_render_df = slice_df.copy()
    highlight_pattern = re.compile(re.escape(search_term), re.IGNORECASE) if search_term else None
    
    # Identify violation percentage columns
    violation_pct_columns = [
        col for col in slice_render_df.columns 
        if "نسبة التجاوز" in col
    ]

    def _format_value(value: object, column_name: str = "") -> str:
        # Handle NaN values (both actual NaN and string 'nan')
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return ""
        if isinstance(value, str) and value.lower() in ['nan', 'none', 'null', '<na>']:
            return ""
        
        # Format violation percentages as percentages
        if column_name in violation_pct_columns:
            try:
                # Convert to float and multiply by 100 for percentage
                pct_value = float(value) * 100
                text = f"{pct_value:.0f}%"
            except (ValueError, TypeError):
                text = str(value)
        elif column_name == "قيمة الاستهلاك الإجمالي":
            try:
                # Format with commas, no decimals
                val_float = float(value)
                text = f"{int(val_float):,} ريال"
            except (ValueError, TypeError):
                text = f"{value} ريال"
        else:
            text = str(value)
        
        if highlight_pattern:
            return highlight_pattern.sub(lambda m: f"<mark style='background:#ffe9b5;padding:2px 4px;border-radius:3px;'>{m.group(0)}</mark>", text)
        return text

    for column in slice_render_df.columns:
        slice_render_df[column] = slice_render_df[column].apply(lambda x: _format_value(x, column))

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

    # Hide the sheet tracking column from display
    display_df = slice_render_df.drop(columns=["المحافظة_الورقة"], errors="ignore")

    # Build table HTML with proper thead/tbody for sticky headers
    header_html = "".join(f"<th>{col}</th>" for col in display_df.columns)
    rows_html = ""
    for _, row in display_df.iterrows():
        cells = "".join(f"<td>{val}</td>" for val in row)
        rows_html += f"<tr>{cells}</tr>"
    
    html_table = f'<table class="nice-table" id="province-table"><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>'
    st.markdown(f'<div class="tbl-card"><div class="tbl-scroll">{html_table}</div></div>', unsafe_allow_html=True)
    
    # Add resizable columns functionality using components.html
    import streamlit.components.v1 as components
    
    resize_html = """
    <script>
    (function() {
        // Wait for table to be available
        setTimeout(function() {
            const table = parent.document.querySelector('#province-table');
            if (!table) {
                console.log('Table not found');
                return;
            }
            
            const headers = table.querySelectorAll('th');
            let isResizing = false;
            let currentHeader = null;
            let startX = 0;
            let startWidth = 0;
            
            headers.forEach((header, index) => {
                // Skip last column
                if (index === headers.length - 1) return;
                
                // Create resize handle
                const resizeHandle = parent.document.createElement('div');
                resizeHandle.style.cssText = `
                    position: absolute;
                    right: 0;
                    top: 0;
                    width: 8px;
                    height: 100%;
                    cursor: col-resize;
                    user-select: none;
                    z-index: 10;
                `;
                
                // Add hover effect
                resizeHandle.addEventListener('mouseenter', () => {
                    resizeHandle.style.background = 'rgba(0,0,0,0.1)';
                });
                resizeHandle.addEventListener('mouseleave', () => {
                    if (!isResizing) resizeHandle.style.background = '';
                });
                
                header.style.position = 'relative';
                header.appendChild(resizeHandle);
                
                resizeHandle.addEventListener('mousedown', (e) => {
                    isResizing = true;
                    currentHeader = header;
                    startX = e.pageX;
                    startWidth = header.offsetWidth;
                    e.preventDefault();
                    parent.document.body.style.cursor = 'col-resize';
                    parent.document.body.style.userSelect = 'none';
                });
            });
            
            parent.document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                const width = startWidth + (e.pageX - startX);
                if (width > 50) {
                    currentHeader.style.width = width + 'px';
                    currentHeader.style.minWidth = width + 'px';
                }
            });
            
            parent.document.addEventListener('mouseup', () => {
                if (isResizing) {
                    isResizing = false;
                    currentHeader = null;
                    parent.document.body.style.cursor = '';
                    parent.document.body.style.userSelect = '';
                }
            });
            
            console.log('Resizable columns initialized');
        }, 100);
    })();
    </script>
    """
    
    components.html(resize_html, height=0)

    # Compact pagination info bar
    current_page = st.session_state.detail_page_idx
    start_row = current_page * rows_per_page + 1
    end_row = min((current_page + 1) * rows_per_page, total_rows)
    prev_disabled = current_page <= 0
    next_disabled = current_page >= total_pages - 1
    
    # Tightened centered pagination row
    _, content_col, _ = st.columns([2.5, 5, 2.5])
    
    with content_col:
        # Tighter internal row for all controls - adjusted for row selector space
        c1, c2, c3 = st.columns([3.2, 2.8, 4], gap="small")
        
        with c1:
            st.markdown(
                f"""<div style='
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    height: 40px;
                    font-size: 14px;
                    color: #2b5d4a;
                    font-weight: 500;
                    margin-left: 10px;
                '>
                    عرض {start_row:,}-{end_row:,} من {total_rows:,}
                </div>""",
                unsafe_allow_html=True
            )
        
        with c2:
            # Inline rows per page selector - add a little more space for r2
            r1, r2 = st.columns([0.7, 1.3], gap="small") 
            with r1:
                st.markdown(
                    "<div style='display:flex;align-items:center;height:40px;justify-content:flex-end;font-size:13px;color:#666;'>صف:</div>",
                    unsafe_allow_html=True
                )
            with r2:
                new_rows = st.selectbox(
                    "صفوف",
                    [10, 25, 50, 100],
                    index=[10, 25, 50, 100].index(st.session_state.get("detail_rows_per_page", 50)),
                    key="_detail_rows_compact",
                    label_visibility="collapsed",
                )
                if new_rows != st.session_state.get("detail_rows_per_page", 50):
                    st.session_state.detail_rows_per_page = new_rows
                    st.session_state.detail_page_idx = 0
                    st.rerun()
        
        with c3:
            # Navigation group with a very little gap
            n1, n2, n3 = st.columns([1, 0.6, 1], gap="small")
            with n1:
                if st.button("التالي", disabled=next_disabled, key="detail_next_compact"):
                    st.session_state.detail_page_idx += 1
                    st.rerun()
            with n2:
                st.markdown(
                    f"<div style='text-align:center;line-height:40px;font-size:13px;color:#2b5d4a;white-space:nowrap;font-weight:600;'>{current_page + 1} / {total_pages}</div>",
                    unsafe_allow_html=True
                )
            with n3:
                if st.button("السابق", disabled=prev_disabled, key="detail_prev_compact"):
                    st.session_state.detail_page_idx -= 1
                    st.rerun()

    st.stop()
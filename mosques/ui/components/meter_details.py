from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

import config
from data import find_coord_cols, load_visits_data, get_visit_status
from domain import safe_str
from ui.utils import render_plotly_chart
from .header import render_header
from i18n import t, is_english, get_quarter_name, get_month_name





def render_meter_details(
    meter_param: str,
    province_param: str,
    quarter_param: str,
    metadata: pd.DataFrame,
    all_violator_data: dict,
):
    if not meter_param:
        return False

    if quarter_param not in config.QUARTER_DATES:
        quarter_param = config.QUARTERS[0]

    meter_id_str = safe_str(meter_param)
    meta_row = metadata[metadata["METER_ID_STR"] == meter_id_str]
    mosque_name = ""
    if not meta_row.empty:
        mosque_name = meta_row.iloc[0].get("Name", meta_row.iloc[0].get("name_ar", ""))

    # Find the first available location link (if any) across all quarters
    location_link = ""
    for df in all_violator_data.values():
        if "رقم العداد" not in df.columns:
            continue
        row = df[df["رقم العداد"].astype(str) == meter_id_str]
        if not row.empty:
            link_val = row.iloc[0].get("الموقع")
            if isinstance(link_val, str) and link_val.strip():
                location_link = link_val.strip()
                break

    # Render header with ministry logo
    render_header()

    # Subtitle with meter details
    # display_title logic: if mosque_name exists, use it. else "Meter: ID"
    display_title = mosque_name if mosque_name else t("meter_label", id=meter_id_str)
    
    # Dynamic styling based on language (Center aligned, but Direction respects language)
    # title_align = "left"  <-- User requested Center
    title_align = "center"
    title_dir = "ltr" if is_english() else "rtl"
    
    st.markdown(
        f'<h2 style="text-align:{title_align}; direction:{title_dir}; color: #1a2f29;">{t("meter_details_of", item=display_title)}</h2>',
        unsafe_allow_html=True,
    )

    # Navigation buttons - consistent with province details page
    _, back_col, _ = st.columns([0.2, 0.8, 5.0])
    with back_col:
        if st.button(f" {t('back')}", key="btn_back_meter", use_container_width=True):
            params = {}
            # Capture view mode if present
            view_mode = st.query_params.get("view")
            # Preserve language
            lang_param = "en" if is_english() else "ar"

            if province_param:
                params = {"province": province_param, "quarter": quarter_param, "lang": lang_param}
                if view_mode == "map":
                    params["view"] = "map"
            elif quarter_param:
                params = {"quarter": quarter_param, "lang": lang_param}
            else:
                params = {"lang": lang_param}
            st.query_params.clear()
            if params:
                st.query_params.update(**params)
            st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # --- METRICS CALCULATION ---
    total_bill = 0.0
    bill_count = 0
    violation_count = 0
    province_name = t("unknown")

    # Iterate over all quarters to aggregate data
    for q_name, df in all_violator_data.items():
        if "رقم العداد" not in df.columns:
            continue
        
        row = df[df["رقم العداد"].astype(str) == meter_id_str]
        if not row.empty:
            # Count violation if present in this quarter's data
            violation_count += 1
            
            # Bill Value
            if "قيمة الفاتورة الإجمالي" in row.columns:
                val = row.iloc[0]["قيمة الفاتورة الإجمالي"]
                try:
                    val_float = float(val)
                    total_bill += val_float
                    bill_count += 1
                except (ValueError, TypeError):
                    pass
            
            # Province (Grab from the first available quarter that has it)
            if province_name == t("unknown") and "المحافظة" in row.columns:
                prov = row.iloc[0]["المحافظة"]
                if isinstance(prov, str) and prov.strip():
                    province_name = prov.strip()

    # Fallback: Check master metadata for Arabic governorate name (GOVERNORATE_NAME_AR)
    if province_name == t("unknown") and not meta_row.empty:
        # First try GOVERNORATE_NAME_AR which has Arabic names (same as map popup)
        if "GOVERNORATE_NAME_AR" in meta_row.columns:
            prov = meta_row.iloc[0].get("GOVERNORATE_NAME_AR")
            if isinstance(prov, str) and prov.strip():
                province_name = prov.strip()
        # Fall back to Province column (English) if still unknown
        if province_name == t("unknown") and "Province" in meta_row.columns:
            prov = meta_row.iloc[0].get("Province")
            if isinstance(prov, str) and prov.strip():
                province_name = prov.strip()

    # Translate governorate if English (and clean suffixes for matching)
    if is_english() and province_name != t("unknown"):
        province_name = t(province_name.split('(')[0].strip())



    # Get overall date range (First Quarter Start -> Last Quarter End)
    first_q = config.QUARTERS[0]
    last_q = config.QUARTERS[-1]
    
    overall_start = config.QUARTER_DATES[first_q][0].strftime("%Y-%m-%d")
    overall_end = config.QUARTER_DATES[last_q][1].strftime("%Y-%m-%d")

    lon_col, lat_col = find_coord_cols(metadata)

    # Load visit info early to include in meter info card
    visits_df = load_visits_data()
    visit_info = get_visit_status(meter_id_str, visits_df)
    
    # Determine visit status display
    # Determine visit status display
    if visit_info['visited']:
        action_status = visit_info.get('action_status', '')
        if action_status and 'تمت المعالجة' in str(action_status):
            visit_status_html = f"<span style='color: #0B9444;'>{t('visited')} </span>"
        else:
            visit_status_html = f"<span style='color: #ff8c00;'>{t('in_progress')}</span>"
        visit_date = visit_info.get('visit_date', '') or t("unspecified")
        causes = visit_info.get('causes', '') or t("no_info")
        violation_type = visit_info.get('violation_type', '') or t("unspecified")
    else:
        visit_status_html = f"<span style='color: #c53030;'>{t('not_visited')}</span>"
        visit_date = "-"
        causes = "-"
        violation_type = "-"

    # Layout: info card, GAP, map with margins
    # Adjust the middle value (0.1) to control space between card and map
    _, info_col, _, map_col, _ = st.columns([0.2, 0.7, 0.1, 1.0, 0.2])
    
    with info_col:
        if not meta_row.empty:
            # Grid with nowrap to prevent wrapping on zoom
            card_html = f"""
            <div class='meter-info-card' style='padding: 16px; direction: {"rtl" if not is_english() else "ltr"}; overflow-x: auto;'>
                <div style='display: grid; grid-template-columns: auto auto auto; gap: 40px; justify-content: start; width: 100%; white-space: nowrap;'>
                    <div>
                        <div class='meter-label'>{t("meter_number")}</div>
                        <div class='meter-value'>{meter_id_str}</div>
                    </div>
                    <div>
                        <div class='meter-label'>{t("governorate")}</div>
                        <div class='meter-value'>{province_name}</div>
                    </div>
                    <div>
                        <div class='meter-label'>{t("total_consumption")}</div>
                        <div class='meter-value highlight'>{int(total_bill):,} {t("riyal")}</div>
                        <div style='font-size: 11px; color: #8a7a63; margin-top: 2px;'>{t("consumption_period_note", start_quarter=get_quarter_name(config.QUARTERS[0]), end_quarter=get_quarter_name(config.QUARTERS[-1]))}</div>
                    </div>
                    <div>
                        <div class='meter-label'>{t("visit_status")}</div>
                        <div class='meter-value'>{visit_status_html}</div>
                    </div>
                    <div>
                        <div class='meter-label'>{t("visit_date")}</div>
                        <div class='meter-value'>{visit_date}</div>
                    </div>
                </div>
                {'<div style="margin-top: 10px; border-top: 1px solid #e1d9c6; padding-top: 8px;"><div class="meter-label">' + t("causes") + '</div><div class="meter-value" style="font-size: 13px; line-height: 1.4;">' + causes + '</div></div>' if visit_info['visited'] else ''}
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
        else:
            st.info(t("no_meter_data"))
    
    with map_col:
        if (
            not meta_row.empty
            and lon_col
            and lat_col
            and pd.notna(meta_row.iloc[0][lon_col])
            and pd.notna(meta_row.iloc[0][lat_col])
        ):
            lon, lat = float(meta_row.iloc[0][lon_col]), float(meta_row.iloc[0][lat_col])
            
            m = folium.Map(
                location=[lat, lon], 
                zoom_start=15, 
                tiles="CartoDB positron",
                dragging=False,
                zoom_control=False,
                scrollWheelZoom=False,
                doubleClickZoom=False,
                touchZoom=False,
                boxZoom=False,
                keyboard=False
            )
            
            folium.Marker(
                [lat, lon],
                icon=folium.Icon(icon="mosque", prefix="fa", color="red")
            ).add_to(m)
            
            st_folium(m, height=220, width="100%", key="meter_map", returned_objects=[])
            
            if location_link:
                st.markdown(
                    f"""<div style='text-align:center; margin-top:8px;'>
                        <a href='{location_link}' target='_blank' 
                           style='
                               background:#f4efe2; 
                               color:#1a2f29; 
                               border:1px solid #e1d9c6; 
                               border-radius:8px; 
                               padding:8px 20px; 
                               text-decoration:none; 
                               font-size:16px;
                               box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
                               display: inline-block;
                               transition: all 0.2s ease;
                           '
                           onmouseover="this.style.backgroundColor='#eaddc5'; this.style.borderColor='#d4c8b0'; this.style.boxShadow='0 4px 10px rgba(0, 0, 0, 0.12)';"
                           onmouseout="this.style.backgroundColor='#f4efe2'; this.style.borderColor='#e1d9c6'; this.style.boxShadow='0 2px 6px rgba(0, 0, 0, 0.08)';"
                        >{t("open_google_maps")}</a>
                    </div>""",
                    unsafe_allow_html=True
                )
        else:
            st.info(t("no_coordinates"))

    st.markdown(f"### {t('quarter_summary')}")
    merged_rows = []
    for quarter in config.QUARTERS:
        df_q = all_violator_data.get(quarter, pd.DataFrame())
        
        viol = t("no")
        if not df_q.empty and "رقم العداد" in df_q.columns:
            # Check if meter exists in this quarter
            if not df_q[df_q["رقم العداد"].astype(str) == meter_id_str].empty:
                viol = t("yes")

        bill_value = ""
        period_value = ""
        bill_numeric = 0.0
        morning_pct = ""
        evening_pct = ""

        if not df_q.empty and "رقم العداد" in df_q.columns:
            row = df_q[df_q["رقم العداد"].astype(str) == meter_id_str]
            if not row.empty:
                if "قيمة الفاتورة الإجمالي" in row.columns:
                    val = row.iloc[0]["قيمة الفاتورة الإجمالي"]
                    if pd.notna(val):
                        try:
                            val_float = float(val)
                            bill_value = f"{int(val_float):,} {t('riyal')}"
                            bill_numeric = val_float
                        except (ValueError, TypeError):
                            bill_value = f"{val} {t('riyal')}"
                
                # Extract period data if available
                if "الفترة صباحا/مساء" in row.columns:
                    period_val = row.iloc[0]["الفترة صباحا/مساء"]
                    period_value = safe_str(period_val) if pd.notna(period_val) and str(period_val).lower() != 'nan' else ""
                
                col_morning = "نسبة التجاوز في الفترة الصباحية"
                if col_morning in row.columns:
                     val = row.iloc[0][col_morning]
                     if pd.notna(val) and str(val).lower() != 'nan':
                         try:
                             # Format as percentage if numeric (0.85 -> 85%)
                             morning_pct = f"{float(val) * 100:.0f}%"
                         except (ValueError, TypeError):
                             morning_pct = str(val)

                col_evening = "نسبة التجاوز في الفترة المسائية"
                if col_evening in row.columns:
                     val = row.iloc[0][col_evening]
                     if pd.notna(val) and str(val).lower() != 'nan':
                         try:
                             evening_pct = f"{float(val) * 100:.0f}%"
                         except (ValueError, TypeError):
                             evening_pct = str(val)

        # Visit status logic
        visit_status_display = ""
        if visit_info['visited']:
            v_date_str = visit_info.get('visit_date', '')
            # Parse date if needed (it might be string)
            v_date_obj = None
            if v_date_str:
                 try:
                     v_date_obj = pd.to_datetime(v_date_str, dayfirst=True).to_pydatetime()
                 except:
                     pass
            
            # Check if date falls in this quarter
            if v_date_obj and quarter in config.QUARTER_DATES:
                q_start, q_end = config.QUARTER_DATES[quarter]
                if q_start <= v_date_obj <= q_end:
                    visit_status_display = t("visited_on_date", date=v_date_str)
            elif not v_date_obj:
                 # Fallback if no date object (shouldn't happen with new loader)
                 visit_status_display = t("visited")

        merged_rows.append(
            {
                t("quarter"): get_quarter_name(quarter),
                t("is_violating"): viol,
                t("morning_evening_period"): period_value, # Using shared key
                t("morning_violation_pct"): morning_pct,
                t("evening_violation_pct"): evening_pct,
                t("total_consumption_value"): bill_value, # Using shared key
                t("visit_status"): visit_status_display,
                "bill_numeric": bill_numeric,
                "quarter_key": quarter # keep key for sorting
            }
        )

    merged_df = pd.DataFrame(merged_rows)
    # Drop the numeric column used for charting so it doesn't show in the table
    # Also drop quarter_key
    display_df = merged_df.drop(columns=["bill_numeric", "quarter_key"], errors="ignore")
    # Build table HTML with proper thead/tbody for sticky headers
    header_html = "".join(f"<th>{col}</th>" for col in display_df.columns)
    rows_html = ""
    for _, row in display_df.iterrows():
        cells = "".join(f"<td>{val}</td>" for val in row)
        rows_html += f"<tr>{cells}</tr>"
    table_html = f'<table class="nice-table"><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>'
    st.markdown(f"<div class='table-wrapper'>{table_html}</div>", unsafe_allow_html=True)

    st.markdown(f"### {t('total_consumption_per_quarter')}")
    if not merged_df.empty:
        # Sort chronologically by config.QUARTERS to ensure correct chart order
        # Use quarter_key which preserves original data value
        merged_rows_sorted = sorted(merged_rows, key=lambda x: config.QUARTERS.index(x["quarter_key"]))
        chart_df = pd.DataFrame(merged_rows_sorted)

        # Add formatted labels with date ranges logic (Arabic/English)
        def _format_quarter_label(q_name):
            if q_name in config.QUARTER_DATES:
                start, end = config.QUARTER_DATES[q_name]
                
                start_str = get_month_name(start.month)
                end_str = get_month_name(end.month)
                
                # Format: 'Q3 2024<br>(from Jan to Mar)'
                display_q = get_quarter_name(q_name)
                return f"{display_q}<br><span style='font-size:11px'>{t('from_month_to_month', start=start_str, end=end_str)}</span>"
            return get_quarter_name(q_name)

        chart_df["x_label"] = chart_df["quarter_key"].apply(_format_quarter_label)
        
        fig_line = px.line(
            chart_df,
            x="x_label",
            y="bill_numeric",
            title="",
            text="bill_numeric",
            markers=True,
        )
        fig_line.update_traces(
            texttemplate="%{text:,}",
            textposition="top center",
            line_color="#456E58",
            marker=dict(size=10, color="#456E58"),
            cliponaxis=False
        )
        fig_line.update_layout(
            margin=dict(t=40, b=20, l=80, r=60),
            height=380,
            xaxis_title=f"<b>{t('quarter')}</b>",
            yaxis_title=f"<b>{t('consumption_value')}</b>",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Tajawal, sans-serif", size=14, color="#1a2f29"),
        )
        fig_line.update_yaxes(
            showgrid=True, 
            gridcolor="#e0e0e0",
            title_standoff=49
        )
        render_plotly_chart(
            fig_line,
            width_mode="stretch",
            config={"displayModeBar": False, "scrollZoom": False},
        )
        
        # Consistent explanation text below the chart
        st.markdown(
            f"<p style='text-align: center; color: #666; font-size: 13px; margin-top: -10px; font-family: Tajawal, sans-serif;'>"
            f"{t('chart_note_zero')}"
            "</p>",
            unsafe_allow_html=True
        )

    st.stop()

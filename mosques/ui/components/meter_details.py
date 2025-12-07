from __future__ import annotations

from urllib.parse import quote_plus

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import folium
from streamlit_folium import st_folium

import config
from data import find_coord_cols
from domain import safe_str
from ui.utils import render_plotly_chart
from .header import render_header


def _find_consumption_column(columns: list[str]) -> str | None:
    """Return the first column that looks like a consumption field."""
    preferred = [
        "الاستهلاك",
        "كمية الاستهلاك",
        "كمية الإستهلاك",
        "الاستهلاك الكلي",
        "استهلاك",
        "consumption",
        "total_consumption",
        "kwh",
    ]
    for col in columns:
        if not isinstance(col, str):
            continue
        col_lower = col.lower()
        if any(key in col_lower for key in preferred):
            return col
        if any(ar in col for ar in ["الاستهلاك", "استهلاك"]):
            return col
    return None


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
    display_title = mosque_name if mosque_name else f"العداد: {meter_id_str}"
    st.markdown(
        f'<h2 style="text-align:center; color: #1a2f29;">تفاصيل {display_title}</h2>',
        unsafe_allow_html=True,
    )

    # Navigation buttons - consistent with province details page
    _, back_col, _ = st.columns([0.2, 0.8, 5.0])
    with back_col:
        if st.button(" رجوع", key="btn_back_meter", use_container_width=True):
            params = {}
            # Capture view mode if present
            view_mode = st.query_params.get("view")

            if province_param:
                params = {"province": province_param, "quarter": quarter_param}
                if view_mode == "map":
                    params["view"] = "map"
            elif quarter_param:
                params = {"quarter": quarter_param}
            st.query_params.clear()
            if params:
                st.query_params.update(**params)
            st.rerun()

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # --- METRICS CALCULATION ---
    total_bill = 0.0
    bill_count = 0
    violation_count = 0
    province_name = "غير معروف"

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
            if province_name == "غير معروف" and "المحافظة" in row.columns:
                prov = row.iloc[0]["المحافظة"]
                if isinstance(prov, str) and prov.strip():
                    province_name = prov.strip()



    # Get overall date range (First Quarter Start -> Last Quarter End)
    first_q = config.QUARTERS[0]
    last_q = config.QUARTERS[-1]
    
    overall_start = config.QUARTER_DATES[first_q][0].strftime("%Y-%m-%d")
    overall_end = config.QUARTER_DATES[last_q][1].strftime("%Y-%m-%d")

    lon_col, lat_col = find_coord_cols(metadata)

    _, cinfo1, _, cinfo2, _ = st.columns([0.5, 1, 0.2, 1.5, 0.5])
    with cinfo1:
        if not meta_row.empty:
            st.markdown(
                (
                    "<div class='meter-info-card'>"
                    "<div class='meter-label'>رقم العداد</div>"
                    f"<div class='meter-value'>{meter_id_str}</div>"
                    "<div class='meter-label'>المحافظة</div>"
                    f"<div class='meter-value'>{province_name}</div>"
                    "<div class='meter-label'>إجمالي الفواتير</div>"
                    f"<div class='meter-value highlight'>{int(total_bill):,} ريال</div>"
                    f"<div style='font-size: 13px; color: #666; margin-top: -8px; margin-bottom: 12px;'>(من {first_q} إلى {last_q})</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )
        else:
            st.info("لا توجد بيانات تعريفية لهذا العداد في ملف Industry Code.")
    with cinfo2:
        if (
            not meta_row.empty
            and lon_col
            and lat_col
            and pd.notna(meta_row.iloc[0][lon_col])
            and pd.notna(meta_row.iloc[0][lat_col])
        ):
            lon, lat = float(meta_row.iloc[0][lon_col]), float(meta_row.iloc[0][lat_col])
            
            # Create Folium Map (Static)
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
            
            # Add marker with mosque icon (same as province map)
            folium.Marker(
                [lat, lon],
                icon=folium.Icon(icon="mosque", prefix="fa", color="red")
            ).add_to(m)
            
            # Display the map
            st_folium(m, height=250, width="100%", key="meter_map", returned_objects=[])
            
            # Add location link (Styled like the "Back" button)
            if location_link:
                st.markdown(
                    f"""
                    <style>
                    .btn-google-maps {{
                        display: inline-block;
                        background-color: #f4efe2;
                        color: #1a2f29 !important;
                        border: 1px solid #e1d9c6;
                        border-radius: 8px;
                        padding: 6px 24px;
                        text-decoration: none !important;
                        font-family: 'Tajawal', sans-serif;
                        font-size: 15px;
                        font-weight: 400;
                        transition: all 0.2s ease;
                        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
                    }}
                    .btn-google-maps:hover {{
                        background-color: #eaddc5 !important;
                        border-color: #d4c8b0 !important;
                        color: #1a2f29 !important;
                        box-shadow: 0 3px 10px rgba(0, 0, 0, 0.12);
                    }}
                    </style>
                    <div style="text-align:center; margin-top:16px;">
                        <a href="{location_link}" target="_blank" class="btn-google-maps">
                            فتح الموقع في خرائط قوقل
                        </a>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        else:
            st.info("لا تتوفر إحداثيات X,Y لهذا العداد.")
    st.markdown("### ملخص الأرباع")
    merged_rows = []
    for quarter in config.QUARTERS:
        df_q = all_violator_data.get(quarter, pd.DataFrame())
        
        viol = "لا"
        if not df_q.empty and "رقم العداد" in df_q.columns:
            # Check if meter exists in this quarter
            if not df_q[df_q["رقم العداد"].astype(str) == meter_id_str].empty:
                viol = "نعم"

        bill_value = ""

        bill_numeric = 0.0
        consumption_value = ""
        consumption_numeric = 0.0
        if not df_q.empty and "رقم العداد" in df_q.columns:
            row = df_q[df_q["رقم العداد"].astype(str) == meter_id_str]
            if not row.empty:
                if "قيمة الفاتورة الإجمالي" in row.columns:
                    val = row.iloc[0]["قيمة الفاتورة الإجمالي"]
                    try:
                        val_float = float(val)
                        bill_value = f"{int(val_float)}"
                        bill_numeric = val_float
                    except (ValueError, TypeError):
                        bill_value = str(val)

                consumption_col = _find_consumption_column(list(df_q.columns))
                if consumption_col and consumption_col in row.columns:
                    cons_val = row.iloc[0][consumption_col]
                    consumption_value = safe_str(cons_val)
                    try:
                        consumption_numeric = float(cons_val)
                    except (ValueError, TypeError):
                        consumption_numeric = 0.0

        merged_rows.append(
            {
                "الربع": quarter,
                "قيمة الفاتورة الإجمالي": bill_value,
                "مجموع الاستهلاك (ميجاوات ساعة)": consumption_value,
                "مُتجاوز؟": viol,
                "bill_numeric": bill_numeric,
                "consumption_numeric": consumption_numeric,
            }
        )

    merged_df = pd.DataFrame(merged_rows)
    # Drop the numeric column used for charting so it doesn't show in the table
    display_df = merged_df.drop(columns=["bill_numeric", "consumption_numeric"], errors="ignore")
    # Build table HTML with proper thead/tbody for sticky headers
    header_html = "".join(f"<th>{col}</th>" for col in display_df.columns)
    rows_html = ""
    for _, row in display_df.iterrows():
        cells = "".join(f"<td>{val}</td>" for val in row)
        rows_html += f"<tr>{cells}</tr>"
    table_html = f'<table class="nice-table"><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>'
    st.markdown(f"<div class='table-wrapper'>{table_html}</div>", unsafe_allow_html=True)

    st.markdown("### إجمالي  الفواتير لكل ربع")
    if not merged_df.empty:
        fig_line = px.line(
            merged_df,
            x="الربع",
            y="bill_numeric",
            title="",
            text="bill_numeric",
            markers=True,
        )
        fig_line.update_traces(
            texttemplate="%{text:.2s}",
            textposition="top center",
            line_color="#456E58",
            marker=dict(size=10, color="#456E58"),
        )
        fig_line.update_layout(
            margin=dict(t=20, b=20, l=80, r=20),
            height=380,
            xaxis_title="<b>الربع</b>",
            yaxis_title="<b>قيمة الفاتورة</b>",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Tajawal, sans-serif", size=14, color="#1a2f29"),
        )
        fig_line.update_yaxes(
            showgrid=True, 
            gridcolor="#e0e0e0",
            title_standoff=49
        )
        render_plotly_chart(fig_line, width_mode="stretch")

    st.stop()


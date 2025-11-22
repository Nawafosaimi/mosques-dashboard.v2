from __future__ import annotations

from urllib.parse import quote_plus

import folium
from folium.features import DivIcon
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

import config
from data import find_coord_cols
from domain import safe_str
from ui.utils import render_plotly_chart


def render_meter_details(
    meter_param: str,
    province_param: str,
    quarter_param: str,
    metadata: pd.DataFrame,
    ts: pd.DataFrame,
    all_violator_data: dict,
    violator_sets: dict,
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



    q_start, q_end = config.QUARTER_DATES[quarter_param]

    lon_col, lat_col = find_coord_cols(metadata)
    # Adjust columns for RTL: [Spacer, Card (Right), Spacer, Map (Left), Spacer]
    # Centering the content as requested
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
            fmap = folium.Map(
                location=[lat, lon],
                zoom_start=12,
                tiles="CartoDB Positron",
                zoom_control=True,
                dragging=False,
                scrollWheelZoom=False,
                doubleClickZoom=False,
                touchZoom=False,
            )

            popup_html = (
                f"<div style='min-width:160px;font-family:Tajawal;'>"
                f"<strong>{mosque_name or meter_id_str}</strong><br>"
            )
            if location_link:
                popup_html += f"<a href='{location_link}' target='_blank'>فتح الموقع</a>"
            else:
                popup_html += meter_id_str
            popup_html += "</div>"

            folium.Marker(
                [lat, lon],
                tooltip=f"{meter_id_str}",
                popup=folium.Popup(popup_html, max_width=250),
            ).add_to(fmap)
            st_folium(fmap, width=None, height=250)
        else:
            st.info("لا تتوفر إحداثيات X,Y لهذا العداد.")
    st.markdown("### ملخص الأرباع")
    merged_rows = []
    for quarter in config.QUARTERS:
        viol = "نعم" if meter_id_str in violator_sets.get(quarter, set()) else "لا"
        df_q = all_violator_data.get(quarter, pd.DataFrame())

        bill_value = "N/A"

        bill_numeric = 0.0
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

        merged_rows.append(
            {
                "الربع": quarter,
                "قيمة الفاتورة الإجمالي": bill_value,
                "مُتجاوز؟": viol,
                "bill_numeric": bill_numeric,
            }
        )

    merged_df = pd.DataFrame(merged_rows)
    # Drop the numeric column used for charting so it doesn't show in the table
    display_df = merged_df.drop(columns=["bill_numeric"], errors="ignore")
    # Build table HTML with proper thead/tbody for sticky headers
    header_html = "".join(f"<th>{col}</th>" for col in display_df.columns)
    rows_html = ""
    for _, row in display_df.iterrows():
        cells = "".join(f"<td>{val}</td>" for val in row)
        rows_html += f"<tr>{cells}</tr>"
    table_html = f'<table class="nice-table"><thead><tr>{header_html}</tr></thead><tbody>{rows_html}</tbody></table>'
    st.markdown(f"<div class='table-wrapper'>{table_html}</div>", unsafe_allow_html=True)

    st.markdown("### الفواتير لكل ربع")
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


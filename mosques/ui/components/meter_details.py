from __future__ import annotations

from urllib.parse import quote_plus

import folium
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

    hdr_left, hdr_center, hdr_right = st.columns([1, 3, 1])
    with hdr_left:
        if st.button("⬅️ رجوع", key="btn_back_meter"):
            params = {}
            if province_param:
                params = {"province": province_param, "quarter": quarter_param}
            elif quarter_param:
                params = {"quarter": quarter_param}
            st.query_params.clear()
            if params:
                st.query_params.update(**params)
            st.rerun()

    with hdr_center:
        display_title = mosque_name if mosque_name else f"العداد: {meter_id_str}"
        st.markdown(
            f'<div style="text-align:center;"><span style="font-size:38px;font-weight:700;">تفاصيل {display_title}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    q_start, q_end = config.QUARTER_DATES[quarter_param]

    lon_col, lat_col = find_coord_cols(metadata)
    cinfo1, cinfo2 = st.columns([2, 1])
    with cinfo1:
        if not meta_row.empty:
            st.markdown(
                f"<div class='card'><b>رقم العداد:</b> {meter_id_str}<br><b>اسم المسجد:</b> {mosque_name}</div>",
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
            fmap = folium.Map(location=[lat, lon], zoom_start=12, tiles="CartoDB Positron")
            folium.Marker([lat, lon], tooltip=f"{meter_id_str}").add_to(fmap)
            st_folium(fmap, width=None, height=220)
        else:
            st.info("لا تتوفر إحداثيات X,Y لهذا العداد.")
    """
    st.markdown("### استهلاك الطاقة اليومي")
    meter_ts_q = ts[
        (ts["METER_ID_STR"] == meter_id_str) & (ts["date"].between(q_start, q_end))
    ].sort_values("date")
    if meter_ts_q.empty:
        st.warning("لا توجد قراءات في هذا الربع.")
    else:
        fig_line = px.line(meter_ts_q, x="date", y="avg_power", markers=True, title="")
        fig_line.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            height=380,
            xaxis_title="التاريخ",
            yaxis_title="متوسط الاستهلاك ",
            
        )
        render_plotly_chart(fig_line, width_mode="stretch")
    """
    st.markdown("### ملخص الأرباع")
    merged_rows = []
    for quarter in config.QUARTERS:
        viol = "نعم" if meter_id_str in violator_sets.get(quarter, set()) else "لا"
        df_q = all_violator_data.get(quarter, pd.DataFrame())

        link = ""
        bill_value = "N/A"

        if not df_q.empty and "رقم العداد" in df_q.columns:
            row = df_q[df_q["رقم العداد"].astype(str) == meter_id_str]
            if not row.empty:
                if "الموقع" in row.columns and isinstance(row.iloc[0]["الموقع"], str):
                    link = row.iloc[0]["الموقع"]

                if "قيمة الفاتورة الإجمالي" in row.columns:
                    val = row.iloc[0]["قيمة الفاتورة الإجمالي"]
                    try:
                        bill_value = f"{int(float(val))}"
                    except (ValueError, TypeError):
                        bill_value = str(val)

        merged_rows.append(
            {
                "الربع": quarter,
                "قيمة الفاتورة الإجمالي": bill_value,
                "مُتجاوز؟": viol,
                "الموقع": f'<a href="{link}" target="_blank">عرض</a>' if link else "",
            }
        )

    merged_df = pd.DataFrame(merged_rows)
    st.markdown(merged_df.to_html(escape=False, index=False, classes="nice-table"), unsafe_allow_html=True)
    st.stop()


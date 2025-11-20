from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from shapely.geometry import Point
from streamlit_folium import st_folium

import config
from ui.utils import render_plotly_chart


@st.cache_data
def get_combined_violator_data(all_violator_data: dict) -> pd.DataFrame:
    """Cache the concatenation of all quarter data."""
    return pd.concat(all_violator_data.values(), ignore_index=True).dropna(how="all")


@st.cache_data
def calculate_province_counts(
    _violator_mosques: pd.DataFrame, _metadata: pd.DataFrame
) -> pd.DataFrame:
    """Cache the calculation of province counts."""
    if not _violator_mosques.empty and "Province" in _metadata.columns:
        return _violator_mosques.groupby("Province").size().reset_index(name="count")
    return pd.DataFrame(columns=["Province", "count"])


@st.cache_data
def prepare_map_data(_regions, province_counts: pd.DataFrame):
    """Cache the merging of regions with counts."""
    regions_map = _regions.merge(
        province_counts, left_on="province_en", right_on="Province", how="left"
    )
    regions_map["count"] = regions_map["count"].fillna(0).astype(int)
    regions_map["count_label"] = regions_map["count"].map(lambda x: f"{x:,}")
    return regions_map


def render_overview(
    quarter_param: str,
    regions,
    metadata: pd.DataFrame,
    all_violator_data: dict,
):
    def _quarter_count(label: str | None) -> int:
        if not label:
            return 0
        df = all_violator_data.get(label)
        if df is None or not isinstance(df, pd.DataFrame):
            return 0
        return len(df.dropna(how="all"))

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

    # Title at the top
    st.markdown("<h1 style='text-align: center;'>لوحة متابعة المساجد</h1>", unsafe_allow_html=True)

    all_quarters_label = "كل الأرباع"
    quarter_options = [all_quarters_label] + config.QUARTERS

    # Row with KPIs on left and Filter on right
    # Using more flexible proportions to allow dynamic KPI width
    _, kpi_col, _, filter_col = st.columns([0.08, 1.8, 0.15, 2.2], gap="medium")
    
    # First, we need to get the selected quarter for calculations
    with filter_col:
        spacer, filter_inner_col, _ = st.columns([0.5, 0.9, 0.6])
        with filter_inner_col:
            st.markdown("<p  class='filter-label'>اختر الربع</p>", unsafe_allow_html=True)
            selected_quarter_overview = st.selectbox(
                "اختر الربع",
                quarter_options,
                index=quarter_options.index(quarter_param) if quarter_param in quarter_options else 0,
                key="overview_quarter",
                label_visibility="hidden",
            )

    if selected_quarter_overview == all_quarters_label:
        overview_df = get_combined_violator_data(all_violator_data)
    else:
        overview_df = all_violator_data.get(selected_quarter_overview, pd.DataFrame()).dropna(how="all")

    total_mosques_overview = len(metadata)
    violations_count_overview = len(overview_df)

    mosques_delta_label = (
        f"محدّث حتى {selected_quarter_overview}"
        if selected_quarter_overview != all_quarters_label
        else f"مجموع {len(config.QUARTERS)} أرباع"
    )
    mosques_delta_html = f"<div class='delta neutral'>{mosques_delta_label}</div>"

    if selected_quarter_overview == all_quarters_label:
        violations_delta_html = f"<div class='delta neutral'>إجمالي {len(config.QUARTERS)} أرباع</div>"
    else:
        current_idx = config.QUARTERS.index(selected_quarter_overview)
        previous_label = config.QUARTERS[current_idx - 1] if current_idx > 0 else None
        previous_count = _quarter_count(previous_label) if previous_label else None
        current_count = _quarter_count(selected_quarter_overview)
        violations_delta_html = _build_delta_html(
            current_count, previous_count, previous_label, prefer_lower=True
        )

    # Now render KPIs in the middle column (dynamic width based on content)
    with kpi_col:
        kpi_left, kpi_right = st.columns([1, 1.2], gap="medium")
        
        with kpi_left:
            st.markdown(
            (
                "<div class='kpi'>"
                "<div class='t'><b>عدد المساجد في المملكة</b></div> "
                f"<div class='v'>{total_mosques_overview:,}</div>"
                f"{mosques_delta_html}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        
        with kpi_right:
            st.markdown(
                (
                    "<div class='kpi'>"
                    "<div class='t'><b>عدد المساجد المتجاوزة في منطقة الرياض</b></div>"
                    f"<div class='v red'>{violations_count_overview:,}</div>"
                    f"{violations_delta_html}"
                    "</div>"
                ),
            unsafe_allow_html=True,
        )

    col_map, col_bar = st.columns([1, 1], gap="medium")

    with col_map:
        st.markdown("### خريطة المناطق الإدارية ")

        violator_ids = (
            overview_df["رقم العداد"].astype(str).unique() if "رقم العداد" in overview_df.columns else []
        )
        violator_mosques = (
            metadata[metadata["METER_ID_STR"].isin(violator_ids)]
            if len(violator_ids) > 0
            else pd.DataFrame()
        )

        province_counts = calculate_province_counts(violator_mosques, metadata)
        regions_map = prepare_map_data(regions, province_counts)

        m = build_overview_map(regions_map)
        map_state = st_folium(m, height=435, width="stretch")

        province_clicked = None
        if map_state and map_state.get("last_object_clicked"):
            pt = Point(map_state["last_object_clicked"]["lng"], map_state["last_object_clicked"]["lat"])
            clicked_region = regions[regions.geometry.contains(pt)]
            if not clicked_region.empty:
                province_clicked = clicked_region.iloc[0]["province_en"]

        if province_clicked:
            if province_clicked == "RIYADH PROVINCE":
                if st.session_state.get("last_redirect") != (province_clicked, selected_quarter_overview):
                    st.session_state["last_redirect"] = (province_clicked, selected_quarter_overview)
                    st.query_params.update(province=province_clicked, quarter=selected_quarter_overview)
                    st.rerun()
            else:
                st.toast("البيانات متاحة حاليا لمنطقة الرياض فقط.", icon="ℹ️")

    with col_bar:
        st.markdown("### توزيع المساجد حسب المنطقة")
        if "Province" in metadata.columns:
            counts = (
                metadata.dropna(subset=["Province"])
                .groupby("Province")
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
                .head(8)
            )
            reverse_region_map = {v: k for k, v in config.REGION_NAME_MAP.items()}
            counts["Province_AR"] = counts["Province"].map(reverse_region_map).fillna(counts["Province"])

            fig_prov_bar = px.bar(
                counts.sort_values("count", ascending=True),
                x="count",
                y="Province_AR",
                orientation="h",
                text="count",
            )
            fig_prov_bar.update_traces(
                texttemplate="%{text:,}",
                textposition="outside",
                marker_color="#2E8B57",
                marker_line_color="rgba(0,0,0,0.2)",
                marker_line_width=0,
            )
            max_val = counts["count"].max()

            fig_prov_bar.update_layout(
                height=467,
                margin=dict(t=0, b=20, l=220, r=0),
                showlegend=False,
                xaxis_title="<b>عدد المساجد</b>",
                yaxis_title="",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(
                    showgrid=True,
                    gridwidth=1,
                    gridcolor="#cfc8af",
                    zeroline=False,
                    range=[0, max_val * 1.15],
                    tickfont=dict(color="#114736", size=16),
                ),
                yaxis=dict(showgrid=False, automargin=True, tickfont=dict(color="#114736", size=18)),
                font=dict(family="Tajawal, sans-serif", size=14, color="#114736"),
            )
            fig_prov_bar.update_layout(dragmode=False)
            fig_prov_bar.update_xaxes(fixedrange=True)
            fig_prov_bar.update_yaxes(fixedrange=True)
            render_plotly_chart(
                fig_prov_bar,
                width_mode="stretch",
                config={"displayModeBar": False, "scrollZoom": False},
            )
        else:
            st.info("ملف Industry Code لا يحتوي على عمود 'Province'.")

    st.markdown(" ###  المتجاوزين عبر الأرباع  في منطقة الرياض ")
    quarter_labels = config.QUARTERS
    quarter_values = [len(all_violator_data.get(q, pd.DataFrame())) for q in config.QUARTERS]

    fig_line = go.Figure(
        data=[
            go.Scatter(
                x=quarter_labels,
                y=quarter_values,
                mode="lines+markers+text",
                line=dict(color="#0B9444", width=3),
                marker=dict(size=12, color="#0B9444", line=dict(color="#ffffff", width=2)),
                text=[f"{val:,}" for val in quarter_values],
                textposition="top center",
                textfont=dict(size=16, color="#114736", family="Tajawal, sans-serif", weight="bold"),
                hovertemplate="<b>%{x}</b><br>المتجاوزين: %{y:,}<extra></extra>",
            )
        ]
    )
    fig_line.update_layout(
        height=450,
        margin=dict(t=40, b=40, l=218, r=40),
        showlegend=False,
        xaxis=dict(
            title=dict(text="<b>الربع</b>", font=dict(color="#2b5d4a", size=16, family="Tajawal, sans-serif")),
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#114736", size=15, family="Tajawal, sans-serif"),
        ),
        yaxis=dict(
            title=dict(
                text="<b>عدد المساجد المتجاوزة</b>",
                font=dict(color="#2b5d4a", size=16, family="Tajawal, sans-serif"),
                standoff=55
            ),
            showgrid=True,
            gridwidth=1,
            gridcolor="#e5eddc",
            zeroline=False,
            tickfont=dict(color="#114736", size=14),
        ),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Tajawal, sans-serif", size=14, color="#114736"),
    )
    fig_line.update_xaxes(fixedrange=True)
    fig_line.update_yaxes(fixedrange=True)
    render_plotly_chart(
        fig_line,
        width_mode="stretch",
        config={"displayModeBar": False, "scrollZoom": False},
    )


def build_overview_map(regions_map):
    import folium

    m = folium.Map(
        location=[23.8859, 45.0792],
        zoom_start=4.7,
        tiles="CartoDB positron",
        zoom_control=False,
        dragging=False,
        scrollWheelZoom=False,
        doubleClickZoom=False,
        touchZoom=False,
        boxZoom=False,
        keyboard=False,
    )
    m.get_root().html.add_child(
        folium.Element("<style>.leaflet-control-attribution{display:none !important;}</style>")
    )
    folium.GeoJson(
        data=regions_map.__geo_interface__,
        style_function=lambda _: {"fillColor": "#0B9444", "color": "#0B9444", "weight": 1, "fillOpacity": 0.3},
        highlight_function=lambda _: {"weight": 3, "fillOpacity": 0.5},
        tooltip=folium.GeoJsonTooltip(fields=["name_ar", "count_label"], aliases=["المنطقة", "عدد المتجاوزين"]),
    ).add_to(m)
    return m


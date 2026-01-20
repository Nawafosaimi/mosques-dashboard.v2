from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from urllib.parse import quote_plus
from shapely.geometry import Point
from streamlit_folium import st_folium

import config
from ui.utils import render_plotly_chart
from i18n import t, get_quarter_name, get_month_name, is_english

from .kpi_card import render_kpi_card
from .header import render_header





@st.cache_data
def get_combined_violator_data(all_violator_data: dict) -> pd.DataFrame:
    """Cache the concatenation of all quarter data, deduplicated by meter ID."""
    combined = pd.concat(all_violator_data.values(), ignore_index=True).dropna(how="all")
    # Deduplicate by meter ID to count unique mosques, not total violations across quarters
    if "رقم العداد" in combined.columns:
        combined = combined.drop_duplicates(subset=["رقم العداد"], keep="first")
    return combined


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


def render_regional_distribution_chart(metadata: pd.DataFrame, all_violator_data: dict):
    """Renders the regional distribution stacked bar chart with sorting and view options using Plotly."""
    if "Province" not in metadata.columns:
        st.info(t("no_data") if is_english() else "ملف Industry Code لا يحتوي على عمود 'Province'.")
        return

    # Header
    st.markdown(f"### {t('regional_distribution')}")

    # Data Preparation: Static (Sum of all quarters)
    total_counts = (
        metadata.dropna(subset=["Province"])
        .groupby("Province")
        .size()
        .reset_index(name="total")
    )
    
    # Always load violators from ALL quarters
    all_v_df = get_combined_violator_data(all_violator_data)
    violator_ids = all_v_df["رقم العداد"].astype(str).unique() if "رقم العداد" in all_v_df.columns else []
    
    # Filter metadata for violators
    v_mosques = metadata[metadata["METER_ID_STR"].isin(violator_ids)] if len(violator_ids) > 0 else pd.DataFrame()
    
    if not v_mosques.empty and "Province" in v_mosques.columns:
        violator_counts = (
            v_mosques.dropna(subset=["Province"])
            .groupby("Province")
            .size()
            .reset_index(name="violators")
        )
    else:
        violator_counts = pd.DataFrame(columns=["Province", "violators"])
        
    region_data = total_counts.merge(violator_counts, on="Province", how="left")
    region_data["violators"] = region_data["violators"].fillna(0).astype(int)
    region_data["total"] = region_data["total"].fillna(0).astype(int)
    region_data["non_violators"] = (region_data["total"] - region_data["violators"]).clip(lower=0).astype(int)
    
    # Percentages
    region_data["violator_pct"] = (region_data["violators"] / region_data["total"] * 100).fillna(0).round(1)
    region_data["non_violator_pct"] = (100 - region_data["violator_pct"]).round(1)

    # Sort by total count ascending (to show highest total at the top of the Plotly horizontal chart)
    region_data = region_data.sort_values("total", ascending=True)
    
    # Arabic names
    reverse_region_map = {v: k for k, v in config.REGION_NAME_MAP.items()}
    region_data["Province_AR"] = region_data["Province"].map(reverse_region_map).fillna(region_data["Province"])
    
    # Select display column based on language
    display_col = "Province" if is_english() else "Province_AR"
    
    is_pct = False
    
    fig = go.Figure()
    
    # Colors matching the user's request
    color_non_violator = "#2E8B57" # Green (Safe)
    color_violator = "#f1b622"     # Dark Gold (Violators)
    
    # Hover template - translated
    non_viol_label = t("non_violators")
    viol_label = t("violators")
    pct_label = "Percentage" if is_english() else "النسبة"
    count_label = "Count" if is_english() else "العدد"
    
    if is_pct:
        hovertemplate_non = f"<b>{non_viol_label}</b><br>{pct_label}: %{{x:.1f}}%<br>{count_label}: %{{customdata:,}}<extra></extra>"
        hovertemplate_vio = f"<b>{viol_label}</b><br>{pct_label}: %{{x:.1f}}%<br>{count_label}: %{{customdata:,}}<extra></extra>"
        x_non = region_data["non_violator_pct"]
        x_vio = region_data["violator_pct"]
        cd_non = region_data["non_violators"]
        cd_vio = region_data["violators"]
    else:
        hovertemplate_non = f"<b>{non_viol_label}</b><br>{count_label}: %{{x:,}}<br>{pct_label}: %{{customdata:.1f}}%<extra></extra>"
        hovertemplate_vio = f"<b>{viol_label}</b><br>{count_label}: %{{x:,}}<br>{pct_label}: %{{customdata:.1f}}%<extra></extra>"
        x_non = region_data["non_violators"]
        x_vio = region_data["violators"]
        cd_non = region_data["non_violator_pct"]
        cd_vio = region_data["violator_pct"]

    # Add Non-Violators (Green) - First in legend
    fig.add_trace(go.Bar(
        name=t("non_violators"),
        y=region_data[display_col],
        x=x_non,
        orientation="h",
        marker_color=color_non_violator,
        hovertemplate=hovertemplate_non,
        customdata=cd_non,
        marker=dict(line=dict(width=0))
    ))

    # Add Violators (Gold)
    fig.add_trace(go.Bar(
        name=t("violators"),
        y=region_data[display_col],
        x=x_vio,
        orientation="h",
        marker_color=color_violator,
        hovertemplate=hovertemplate_vio,
        customdata=cd_vio,
        marker=dict(line=dict(width=0))
    ))

    # Annotations for total counts
    annotations = []
    if not is_pct:
        max_val = region_data["total"].max()
        for _, row in region_data.iterrows():
            annotations.append(dict(
                x=row["total"] + max_val * 0.02,
                y=row[display_col],
                text=f"{row['total']:,}",
                showarrow=False,
                font=dict(size=13, color="#000000", family="Tajawal"),
                xanchor="left",
                yanchor="middle",
            ))

    # Layout styling
    chart_height = max(540, len(region_data) * 48)
    fig.update_layout(
        barmode="stack",
        height=chart_height,
        margin=dict(t=50, b=10, l=180, r=60),
        showlegend=True,
        annotations=annotations,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=14, color="#000000", family="Tajawal"),
            itemclick=False,
            itemdoubleclick=False
        ),
        xaxis_title=f"<b>{t('percentage') if is_pct else t('num_mosques')}</b>",
        yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor="#ececec",
            zeroline=False,
            range=[0, 105 if is_pct else region_data["total"].max() * 1.15],
            tickfont=dict(color="#000000", size=13),
            ticksuffix="%" if is_pct else "",
        ),
        yaxis=dict(
            showgrid=False,
            automargin=True,
            tickfont=dict(color="#000000", size=14, family="Tajawal"),
        ),
        font=dict(family="Tajawal, sans-serif", size=14, color="#000000"),
        hoverlabel=dict(bgcolor="white", font_size=14, font_family="Tajawal", font_color="#000000"),
        clickmode="none"
    )

    # Disable zoom/pan
    fig.update_layout(dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)

    # Render
    render_plotly_chart(
        fig,
        width_mode="stretch",
        config={"displayModeBar": False, "scrollZoom": False},
    )


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
            return f"<div class='delta neutral'>{t('first_period')}</div>"
        if previous_count == 0:
            return f"<div class='delta neutral'>{t('no_comparison_data')}</div>"
        diff = current_count - previous_count
        if diff == 0:
            q_display = get_quarter_name(previous_label)
            return f"<div class='delta flat'>{t('no_change', quarter=q_display)}</div>"
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
        text_html = f"<span>{diff_text} {t('compared_to_prev')}</span>"
        return f"<div class='delta {direction}'>{text_html}{badge_html}</div>"

    # Render header with ministry logo
    render_header()

    # Title at the top
    st.markdown(f"<h1 style='text-align: center;'>{t('dashboard_title')}</h1>", unsafe_allow_html=True)

    all_quarters_label = t("all_quarters")
    
    # Build display options with translated quarter names
    # Map: display_name -> arabic_key (for data lookup)
    quarter_display_to_key = {all_quarters_label: all_quarters_label}
    for q in config.QUARTERS:
        display_name = get_quarter_name(q)  # Translates to "Q4 2024" etc in English
        quarter_display_to_key[display_name] = q
    
    # Display options (translated names)
    quarter_display_options = [all_quarters_label] + [get_quarter_name(q) for q in config.QUARTERS]

    # Date legend helper
    def _get_quarter_legend(q_name):
        if q_name in config.QUARTER_DATES:
            start, end = config.QUARTER_DATES[q_name]
            # Format: 1 Jan - 31 Mar
            return f"{start.strftime('%d %b')} - {end.strftime('%d %b')}"
        return ""

    # Row with KPIs on left and Filter on right
    # Using more flexible proportions to allow dynamic KPI width
    _, kpi_col, _, filter_col = st.columns([0.05, 2.0, 0.1, 2.0], gap="medium")
    
    # First, we need to get the selected quarter for calculations
    with filter_col:
        spacer, filter_inner_col, _ = st.columns([0.5, 0.9, 0.6])
        with filter_inner_col:
            st.markdown(f"<p  class='filter-label'>{t('select_quarter')}</p>", unsafe_allow_html=True)
            
            # Determine index based on the quarter_param (which is in Arabic)
            if quarter_param in config.QUARTERS:
                # Find the display name for this Arabic key
                display_name = get_quarter_name(quarter_param)
                q_idx = quarter_display_options.index(display_name) if display_name in quarter_display_options else 0
            elif quarter_param == all_quarters_label:
                q_idx = 0
            else:
                q_idx = 0

            # User selects from translated display names
            # Include language in key to force refresh when language changes
            current_lang = "en" if is_english() else "ar"
            selected_display = st.selectbox(
                t("select_quarter"),
                quarter_display_options,
                index=q_idx,
                key=f"overview_quarter_{current_lang}",
                label_visibility="hidden",
            )
            
            # Map selected display name back to Arabic key for data lookup
            selected_quarter_overview = quarter_display_to_key.get(selected_display, selected_display)


    if selected_quarter_overview == all_quarters_label:
        overview_df = get_combined_violator_data(all_violator_data)
    else:
        overview_df = all_violator_data.get(selected_quarter_overview, pd.DataFrame()).dropna(how="all")

    total_mosques_overview = len(metadata)
    violations_count_overview = len(overview_df)

    q_display = get_quarter_name(selected_quarter_overview) if selected_quarter_overview != all_quarters_label else ""
    mosques_delta_label = (
        t("updated_until", quarter=q_display)
        if selected_quarter_overview != all_quarters_label
        else t("quarter_total", count=len(config.QUARTERS))
    )
    mosques_delta_html = f"<div class='delta neutral'>{mosques_delta_label}</div>"

    if selected_quarter_overview == all_quarters_label:
        violations_delta_html = f"<div class='delta neutral'>{t('quarter_total', count=len(config.QUARTERS))}</div>"
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
        # Increased ratio to [1, 1.6] to give more space to the second card (Violators)
        kpi_left, kpi_right = st.columns([1, 1.2], gap="medium")
        
        with kpi_left:
            render_kpi_card(
                title=t("total_mosques"),
                value=f"{total_mosques_overview:,}",
                delta_html=mosques_delta_html,
                tooltip="Total mosques in the Kingdom" if is_english() else "إجمالي عدد المساجد على مستوى المملكة"
            )
        
        with kpi_right:
            kpi_title = t("violating_mosques_riyadh")
            if selected_quarter_overview != all_quarters_label:
                kpi_title = t("violating_mosques_quarter", quarter=q_display)
                
            render_kpi_card(
                title=kpi_title,
                value=f"{violations_count_overview:,}",
                delta_html=violations_delta_html,
                value_color_class="red",
                tooltip="Violating mosques in Riyadh" if is_english() else "المساجد المتجاوزة في الرياض حاليا"
            )

    col_map, col_bar = st.columns([1, 1], gap="medium")

    with col_map:
        st.markdown(f"### {t('admin_regions_map')}")

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

        # Reset map state if returning from a redirect
        if "last_redirect" in st.session_state:
            del st.session_state["last_redirect"]
            st.session_state.overview_map_nonce = st.session_state.get("overview_map_nonce", 0) + 1

        if "overview_map_nonce" not in st.session_state:
            st.session_state.overview_map_nonce = 0

        # Calculate chart height to match the bar chart
        num_regions = len(regions_map) if hasattr(regions_map, '__len__') else 13
        map_height = max(520, num_regions * 45)
        
        m = build_overview_map(regions_map)
        map_key = f"overview_map_{st.session_state.overview_map_nonce}"
        map_state = st_folium(m, height=540, width="stretch", key=map_key)

        province_clicked = None
        if map_state and map_state.get("last_object_clicked"):
            pt = Point(map_state["last_object_clicked"]["lng"], map_state["last_object_clicked"]["lat"])
            clicked_region = regions[regions.geometry.contains(pt)]
            if not clicked_region.empty:
                province_clicked = clicked_region.iloc[0]["province_en"]

        if province_clicked:
            if st.session_state.get("last_redirect") != (province_clicked, selected_quarter_overview):
                st.session_state["last_redirect"] = (province_clicked, selected_quarter_overview)
                st.query_params.update(province=province_clicked, quarter=selected_quarter_overview)
                st.rerun()

    with col_bar:
        render_regional_distribution_chart(metadata, all_violator_data)

    st.markdown(f" ###  {t('violators_by_quarter')} ")
    
    quarter_labels = config.QUARTERS
    quarter_values = [len(all_violator_data.get(q, pd.DataFrame())) for q in config.QUARTERS]

    # line chart for number of violators per quarter
    # Helper to format X-axis labels with date ranges
    def _format_quarter_label(q_name):
        if q_name in config.QUARTER_DATES:
            start, end = config.QUARTER_DATES[q_name]
            
            start_str = get_month_name(start.month)
            end_str = get_month_name(end.month)
            
            q_display_name = get_quarter_name(q_name)
            from_to = t("from_to", start=start_str, end=end_str)
            return f"{q_display_name}<br><span style='font-size:11px'>({from_to})</span>"
        return get_quarter_name(q_name)

    formatted_labels = [_format_quarter_label(q) for q in quarter_labels]

    chart_df = pd.DataFrame({
        "x_label": formatted_labels,
        "count": quarter_values
    })
    
    fig_line = px.line(
        chart_df,
        x="x_label",
        y="count",
        title="",
        text="count",
        markers=True,
    )
    fig_line.update_traces(
        texttemplate="%{text:,}",
        textposition="top center",
        line_color="#456E58",
        marker=dict(size=10, color="#456E58"),
    )
    fig_line.update_layout(
        height=450,
        margin=dict(t=40, b=40, l=40, r=40),
        showlegend=False,
        xaxis_title=f"<b>{t('the_quarter')}</b>",
        yaxis_title=f"<b>{t('violating_mosques_count')}</b>",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Tajawal, sans-serif", size=14, color="#1a2f29"),
    )
    fig_line.update_xaxes(
        showgrid=False,
        zeroline=False,
        tickfont=dict(color="#1a2f29", size=15, family="Tajawal, sans-serif"),
        fixedrange=True
    )
    fig_line.update_yaxes(
        showgrid=True,
        gridcolor="#e0e0e0",
        zeroline=False,
        tickfont=dict(color="#1a2f29", size=14),
        fixedrange=True,
        title_standoff=49
    )
    render_plotly_chart(
        fig_line,
        width_mode="stretch",
        config={"displayModeBar": False, "scrollZoom": False},
    )


def build_overview_map(regions_map):
    import folium

    m = folium.Map(
        location=[23.8859, 45.0792],
        zoom_start=5.2,
        tiles="CartoDB positron",
        zoom_control=False,
        dragging=False,
        scrollWheelZoom=False,
        doubleClickZoom=False,
        touchZoom=False,
        boxZoom=False,
        keyboard=False,
    )
    
    # Dynamic CSS based on language
    # User requested left alignment for map tooltips regardless of language
    direction = "ltr" if is_english() else "rtl"
    text_align = "left" 
    label_align = "left"
    value_align = "left" 
    padding_side = "padding-right" if is_english() else "padding-left"
    
    # Custom CSS for tooltip styling to match province map popup design
    tooltip_css = f"""
    <link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        .leaflet-control-attribution{{display:none !important;}}
        
        /* Custom tooltip styling to match province map popups */
        .leaflet-tooltip {{
            background: #faf8f3 !important;
            border: none !important;
            border-radius: 12px !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12) !important;
            padding: 12px 16px !important;
            font-family: 'Tajawal', sans-serif !important;
            direction: {direction} !important;
            text-align: {text_align} !important;
            min-width: 200px !important;
        }}
        
        .leaflet-tooltip::before {{
            display: none !important;
        }}
        
        /* Target all text inside tooltip */
        .leaflet-tooltip,
        .leaflet-tooltip * {{
            font-family: 'Tajawal', sans-serif !important;
        }}
        
        .leaflet-tooltip table {{
            border-collapse: collapse !important;
            width: 100% !important;
        }}
        
        .leaflet-tooltip table tr {{
            border-bottom: 1px solid #f0f0f0 !important;
        }}
        
        .leaflet-tooltip table tr:last-child {{
            border-bottom: none !important;
        }}
        
        .leaflet-tooltip table td,
        .leaflet-tooltip table th {{
            padding: 8px 6px !important;
            vertical-align: middle !important;
            font-size: 14px !important;
        }}
        
        /* Labels column (th or first td) */
        .leaflet-tooltip table th,
        .leaflet-tooltip table td:first-child {{
            color: #8a7a63 !important;
            font-size: 13px !important;
            font-weight: 500 !important;
            text-align: {label_align} !important;
            {padding_side}: 20px !important;
            white-space: nowrap !important;
        }}
        
        /* Values column (last td) */
        .leaflet-tooltip table td:last-child {{
            color: #1a2f29 !important;
            font-size: 14px !important;
            font-weight: 700 !important;
            text-align: {value_align} !important;
            white-space: nowrap !important;
        }}
        
        /* Override any strong/bold tags inside */
        .leaflet-tooltip strong,
        .leaflet-tooltip b {{
            color: #8a7a63 !important;
            font-weight: 500 !important;
        }}
    </style>
    """
    m.get_root().html.add_child(folium.Element(tooltip_css))
    
    # Select name field based on language
    name_field = "province_en" if is_english() else "name_ar"
    
    folium.GeoJson(
        data=regions_map.__geo_interface__,
        style_function=lambda _: {"fillColor": "#0B9444", "color": "#0B9444", "weight": 1, "fillOpacity": 0.5},
        highlight_function=lambda _: {"weight": 3, "fillOpacity": 0.7},
        tooltip=folium.GeoJsonTooltip(
            fields=[name_field, "count_label"], 
            aliases=[t("region"), t("violators_count")],
            sticky=False
        ),

    ).add_to(m)
    return m
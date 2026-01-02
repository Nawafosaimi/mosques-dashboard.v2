import streamlit as st

def render_kpi_card(
    title: str, 
    value: str | int, 
    delta_html: str = "", 
    value_color_class: str = "",
    tooltip: str = ""
):
    """
    Renders a consistent KPI card with a title, value, and optional delta/subtitle.
    
    Args:
        title: The title of the KPI (e.g., "Total Mosques")
        value: The main value to display (e.g., "1,234")
        delta_html: HTML string for the delta/subtitle (e.g., "<div class='delta...'>...</div>")
        value_color_class: Optional CSS class for the value text (e.g., "red")
        tooltip: Optional tooltip text shown on hover (explains the KPI meaning)
    """
    # Build tooltip attribute if provided
    tooltip_attr = f'title="{tooltip}"' if tooltip else ''
    tooltip_class = 'has-tooltip' if tooltip else ''
    
    st.markdown(
        (
            f"<div class='kpi {tooltip_class}' {tooltip_attr}>"
            f"<div class='t'><b>{title}</b></div>"
            f"<div class='v {value_color_class}'>{value}</div>"
            f"{delta_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

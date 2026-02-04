from __future__ import annotations

import streamlit as st


LIGHT_BG = "#faf8f3"
LIGHT_FONT = "#1a2f29"
ACCENT_FONT = "#184c3b"


def apply_light_theme(fig):
    fig.update_layout(
        paper_bgcolor=LIGHT_BG,
        plot_bgcolor=LIGHT_BG,
        font=dict(color=ACCENT_FONT, family="Tajawal, sans-serif", size=15),
        legend=dict(
            bgcolor="rgba(250,248,243,0.9)",
            bordercolor="#d9cfae",
            borderwidth=1,
            font=dict(color=ACCENT_FONT),
        ),
    )
    axis_style = dict(
        tickfont=dict(color=ACCENT_FONT, size=16),
        gridcolor="#e3dcc5",
        zerolinecolor="#d9d2bb",
        linecolor="#c6bea5",
    )
    fig.update_xaxes(**axis_style, title=dict(font=dict(color=ACCENT_FONT, size=18)))
    fig.update_yaxes(**axis_style, title=dict(font=dict(color=ACCENT_FONT, size=18)))
    return fig


def render_plotly_chart(fig, *, width_mode: str = "stretch", **kwargs):
    """Render Plotly chart with forward/backward compatibility for width settings."""
    apply_light_theme(fig)
    width_arg = {"width": width_mode} if width_mode else {}
    try:
        st.plotly_chart(fig, **width_arg, **kwargs)
    except TypeError:
        # Fallback for Streamlit versions that still expect use_container_width.
        use_container_width = width_mode == "stretch"
        st.plotly_chart(fig, use_container_width=use_container_width, **kwargs)


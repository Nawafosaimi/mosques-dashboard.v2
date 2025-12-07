
"""Header component with ministry logo for all pages."""
from __future__ import annotations

from pathlib import Path
import streamlit as st

# Path to assets directory
ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


import base64

@st.cache_data
def get_base64_image(image_path: Path) -> str:
    """Read image file and return base64 string. Cached to prevent reloading."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""

def render_header() -> None:
    """Render the ministry logo using a reliable Base64 HTML overlay."""
    logo_path = ASSETS_DIR / "ministry_logo.png"
    if not logo_path.exists():
        logo_path = ASSETS_DIR / "favicon.png"
    
    # Get base64 string
    img_base64 = get_base64_image(logo_path)
    if not img_base64:
        return

    # 2. Render fixed overlay using CSS background-image
    # This prevents the "image reload" flicker by letting the browser cache the style
    st.markdown(
        f"""
        <a href="/" target="_self" class="ministry-logo-link">
            <div class="ministry-logo-overlay"></div>
        </a>
        <style>
            /* Hide Streamlit toolbar actions (Deploy, etc) - Reinforced */
            [data-testid="stToolbar"], 
            [data-testid="stToolbarActions"], 
            [data-testid="stHeader"] button {{
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
            }}
            
            header[data-testid="stHeader"] {{
                z-index: 1 !important;
            }}
            
            .ministry-logo-link {{
                position: fixed;
                top: 3px; /* User preference */
                right: 70%; /* Shifted right */
                transform: translateX(-50%);
                z-index: 999999;
                display: block;
                width: 200px; /* Fixed width for click area */
                height: 55px;
                pointer-events: auto;
                cursor: pointer;
                text-decoration: none !important;
                border: none !important;
            }}
            
            .ministry-logo-link:hover {{
                transform: translateX(-50%) !important; /* Prevent shifting on hover */
                text-decoration: none !important;
                border: none !important;
            }}
            
            .ministry-logo-overlay {{
                width: 100%;
                height: 100%;
                background-image: url('data:image/png;base64,{img_base64}');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: center;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
                transition: filter 0.2s ease !important;
            }}
            
            /* Apply brightness glow on hover - no movement */
            .ministry-logo-link:hover .ministry-logo-overlay {{
                filter: drop-shadow(0 2px 8px rgba(11, 148, 68, 0.4)) brightness(1.1) !important;
            }}
            
            /* Responsive: iPad/Large Tablet - adjust logo */
            @media (max-width: 1024px) {{
                .ministry-logo-link {{
                    right: 65% !important;
                    width: 170px !important;
                    height: 48px !important;
                }}
            }}
            
            /* Responsive: Tablet - center the logo */
            @media (max-width: 768px) {{
                .ministry-logo-link {{
                    right: auto !important;
                    left: 50% !important;
                    transform: translateX(-50%) !important;
                    width: 200px !important;
                    height: 55px !important;
                }}
            }}
            
            /* Responsive: Mobile - larger logo */
            @media (max-width: 480px) {{
                .ministry-logo-link {{
                    top: 5px !important;
                    width: 180px !important;
                    height: 50px !important;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

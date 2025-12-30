
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
        
        
        <!-- Contact Us Button with CSS checkbox trick for click toggle -->
        <input type="checkbox" id="contactToggle" class="contact-toggle-checkbox">
        <label for="contactToggle" class="contact-header-btn">تواصل معنا</label>
        <label for="contactToggle" class="contact-backdrop"></label>
        <div class="contact-popup">
            <label for="contactToggle" class="close-btn">✕</label>
            <h4>تواصل معنا</h4>
            <div class="contact-row" style="margin-bottom: 5px;">
                <span class="contact-label">الإدارة:</span>
                <span class="contact-value">الإدارة العامة للذكاء الاصطناعي وتطوير الاعمال</span>
            </div>
            <div class="contact-row">
                <span class="contact-label">البريد الإلكتروني:</span>
                <a href="mailto:AI@moenergy.gov.sa" class="contact-link">AI@moenergy.gov.sa</a>
            </div>
            <div class="contact-divider"></div>
            <div class="contact-row">
                <span class="contact-label">الاسم:</span>
                <span class="contact-value">نواف العصيمي</span>
            </div>
            <div class="contact-row">
                <span class="contact-label">البريد الإلكتروني:</span>
                <a href="mailto:Nawaf.Alosaimi@moenergy.gov.sa" class="contact-link">Nawaf.Alosaimi@moenergy.gov.sa</a>
            </div>
            <div class="contact-divider"></div>
            <div class="contact-row">
                <span class="contact-label">الاسم:</span>
                <span class="contact-value">عبد الرحمن السلوم</span>
            </div>
            <div class="contact-row">
                <span class="contact-label">البريد الإلكتروني:</span>
                <a href="mailto:Abdulrahman.Sallum@moenergy.gov.sa" class="contact-link">Abdulrahman.Sallum@moenergy.gov.sa</a>
            </div>
        </div>
        
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
                top: 8px;
                left: 20px; /* Moved to far left */
                z-index: 999999;
                display: block;
                width: 140px; /* Reduced from 200px */
                height: 40px; /* Reduced from 55px */
                pointer-events: auto;
                cursor: pointer;
                text-decoration: none !important;
                border: none !important;
            }}
            
            .ministry-logo-link:hover {{
                text-decoration: none !important;
                border: none !important;
            }}
            
            .ministry-logo-overlay {{
                width: 100%;
                height: 100%;
                background-image: url('data:image/png;base64,{img_base64}');
                background-size: contain;
                background-repeat: no-repeat;
                background-position: left center;
                filter: drop-shadow(0 2px 4px rgba(0,0,0,0.05));
                transition: filter 0.2s ease !important;
            }}
            
            /* Apply brightness glow on hover - no movement */
            .ministry-logo-link:hover .ministry-logo-overlay {{
                filter: drop-shadow(0 2px 8px rgba(11, 148, 68, 0.3)) brightness(1.1) !important;
            }}
            
            /* Contact Button Styles */
            .contact-toggle-checkbox {{
                display: none;
            }}
            
            
            
            /* Invisible backdrop that covers screen when popup is open */
            .contact-backdrop {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 999998;
                background: transparent;
                cursor: default;
            }}
            
            /* Show backdrop when checkbox is checked */
            .contact-toggle-checkbox:checked ~ .contact-backdrop {{
                display: block;
            }}
            
            .contact-header-btn {{
                position: fixed;
                top: 12px;
                right: 20px;
                z-index: 999999;
                background: #F4EFE2;
                color: #1a2f29;
                border: 1px solid #e1d9c6;
                border-radius: 8px;
                padding: 8px 16px;
                font-family: 'Tajawal', sans-serif;
                font-size: 14px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.2s ease;
            }}
            
            .contact-header-btn:hover {{
                background: #ebe4d1;
                border-color: #d4cbb3;
            }}
            
            .contact-popup {{
                display: none;
                position: fixed;
                top: 55px;
                right: 20px;
                z-index: 999999;
                background: #faf8f3;
                border-radius: 12px;
                padding: 16px;
                min-width: 300px;
                box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
                font-family: 'Tajawal', sans-serif;
                direction: rtl;
                text-align: right;
            }}
            
            /* Show popup when checkbox is checked */
            .contact-toggle-checkbox:checked ~ .contact-popup {{
                display: block;
            }}
            
            .contact-popup .close-btn {{
                position: absolute;
                top: 8px;
                left: 8px;
                background: none;
                border: none;
                font-size: 18px;
                cursor: pointer;
                color: #8a7a63;
                padding: 5px;
                line-height: 1;
            }}
            
            .contact-popup .close-btn:hover {{
                color: #1a2f29;
            }}
            
            .contact-popup h4 {{
                color: #0B9444;
                margin: 0 0 12px 0;
                padding-bottom: 10px;
                border-bottom: 1px solid #f0f0f0;
                font-size: 16px;
                font-weight: 700;
            }}
            
            .contact-popup .contact-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
                padding: 4px 0;
            }}
            
            .contact-popup .contact-label {{
                color: #8a7a63;
                font-size: 13px;
            }}
            
            .contact-popup .contact-value {{
                color: #1a2f29;
                font-size: 14px;
                font-weight: 600;
            }}
            
            .contact-popup .contact-link {{
                color: #0B9444;
                font-size: 13px;
                font-weight: 600;
                text-decoration: none;
                direction: ltr;
            }}
            
            .contact-popup .contact-link:hover {{
                text-decoration: underline;
            }}
            
            .contact-popup .contact-divider {{
                height: 1px;
                background: #e0d8c8;
                margin: 12px 0;
            }}
            
            /* Responsive: Mobile - adjust logo */
            @media (max-width: 768px) {{
                .ministry-logo-link {{
                    left: 10px !important;
                    width: 120px !important;
                    height: 35px !important;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True
    )

from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
STYLE_FILE = ASSETS_DIR / "style.css"


def apply_base_styles() -> None:
    """Inject the shared CSS stylesheet if it exists."""
    if STYLE_FILE.exists():
        css = STYLE_FILE.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    else:
        st.warning("تعذر تحميل ملف الأنماط. تأكد من وجود assets/style.css.")


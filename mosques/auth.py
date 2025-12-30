"""Authentication module for Mosques Dashboard."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
import streamlit_authenticator as stauth
import base64
import yaml

# Path to auth config and assets
AUTH_CONFIG_PATH = Path(__file__).parent / "auth_config.yaml"
ASSETS_DIR = Path(__file__).parent / "assets"

def get_base64_image(image_path: Path) -> str:
    """Read image file and return base64 string."""
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except Exception:
        return ""


def load_auth_config() -> dict:
    """Load authentication configuration from YAML file."""
    if not AUTH_CONFIG_PATH.exists():
        st.error("ملف إعدادات المصادقة غير موجود: auth_config.yaml")
        st.stop()
    
    with open(AUTH_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_authenticator() -> stauth.Authenticate:
    """Create and return the authenticator instance."""
    config = load_auth_config()
    
    return stauth.Authenticate(
        credentials=config["credentials"],
        cookie_name=config["cookie"]["name"],
        cookie_key=config["cookie"]["key"],
        cookie_expiry_days=config["cookie"]["expiry_days"],
    )


def get_current_user() -> Optional[dict]:
    """Get current logged-in user info from session state.
    
    Returns:
        dict with keys: username, name, role, email
        None if not authenticated
    """
    if not st.session_state.get("authentication_status"):
        return None
    
    username = st.session_state.get("username")
    if not username:
        return None
    
    config = load_auth_config()
    user_data = config["credentials"]["usernames"].get(username, {})
    
    return {
        "username": username,
        "name": st.session_state.get("name", user_data.get("name", "")),
        "role": user_data.get("role", "user"),
        "email": user_data.get("email", ""),
    }


def is_admin() -> bool:
    """Check if current user has admin role."""
    user = get_current_user()
    return user is not None and user.get("role") == "admin"


def get_login_styles() -> str:
    """Read the login-specific CSS file."""
    css_path = ASSETS_DIR / "login.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def render_login_page(authenticator: stauth.Authenticate) -> bool:
    """Render the login page and return authentication status.
    
    Returns:
        True if authenticated, False otherwise
    """
    # Only render the login UI if not authenticated
    if not st.session_state.get("authentication_status"):
        # Get logo base64
        logo_path = ASSETS_DIR / "ministry_logo.png"
        if not logo_path.exists():
            logo_path = ASSETS_DIR / "favicon.png"
        img_base64 = get_base64_image(logo_path)
        
        # Get login specific styles
        login_css = get_login_styles()
        
        # Render the login UI
        st.markdown(
            f"""<style>
{login_css}
</style>
<div class="login-logo-container">
    <img src="data:image/png;base64,{img_base64}" class="login-logo">
</div>""",
            unsafe_allow_html=True
        )
    
    # Render login form
    authenticator.login(location="main", fields={
        "Form name": "تسجيل الدخول",
        "Username": "اسم المستخدم",
        "Password": "كلمة المرور",
        "Login": "دخول",
    })
    
    if st.session_state.get("authentication_status") is False:
        st.error("اسم المستخدم أو كلمة المرور غير صحيحة")
    elif st.session_state.get("authentication_status") is None:
        st.info("الرجاء إدخال اسم المستخدم وكلمة المرور")
    
    return st.session_state.get("authentication_status", False)

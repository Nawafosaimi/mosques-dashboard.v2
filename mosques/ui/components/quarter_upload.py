from __future__ import annotations

import re
import streamlit as st
from data.loaders import process_uploaded_quarter


def render_quarter_upload():
    """Render the quarter upload UI component (intended for modal/dialog)."""
    # Removed st.sidebar references to allow rendering in main area/modal
    st.header("📤 إضافة ربع جديد")
    st.write("قم بتحميل ملف Excel يحتوي على بيانات الربع الجديد لإضافته إلى النظام.")

    # File uploader
    uploaded_file = st.file_uploader(
        "تحميل ملف Excel للربع",
        type=["xlsx"],
        help="اختر ملف Excel يحتوي على بيانات الربع الجديد",
    )

    if uploaded_file is not None:
        # Extract quarter name from filename
        filename = uploaded_file.name
        quarter_name = _extract_quarter_name(filename)
        
        # Create a unique key for this specific file upload instance
        # We use size and name to track if we've already processed this exact file
        file_key = f"processed_{filename}_{uploaded_file.size}"
        
        # Initialize processed files tracker if needed
        if "processed_uploads" not in st.session_state:
            st.session_state.processed_uploads = set()

        # If this file hasn't been processed yet, process it immediately
        if file_key not in st.session_state.processed_uploads:
            st.info(f"⏳ جاري معالجة الملف: **{quarter_name}**...")
            
            # Show a spinner while processing
            with st.spinner("جاري معالجة البيانات..."):
                try:
                    success, message = process_uploaded_quarter(uploaded_file, quarter_name)
                    
                    if success:
                        # Mark as processed BEFORE rerun to avoid loops
                        st.session_state.processed_uploads.add(file_key)
                        
                        # Show success message briefly
                        st.success(f"✅ {message}")
                        
                        # Clear data caches
                        st.cache_data.clear()
                        st.cache_resource.clear()
                        
                        # Small delay to ensure user sees the success state
                        import time
                        time.sleep(1.0)
                        
                        # Rerun app to update data
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
                        
                except Exception as e:
                    st.error(f"❌ حدث خطأ: {str(e)}")
        else:
            # File already processed
            st.success(f"✅ تم تحميل الربع: **{quarter_name}** بنجاح.")
            st.write("يمكنك إغلاق هذه النافذة أو تحميل ملف آخر.")


def _extract_quarter_name(filename: str) -> str:
    """Extract standardized quarter name from filename using regex.

    Attempts to find patterns like "الربع الثالث" and a year "2025"
    to construct a standard name "الربع الثالث 2025".
    """
    # Normalize filename: remove extension and underscores
    name = filename.replace(".xlsx", "").replace(".XLSX", "").replace("_", " ")
    
    # Regex to find the quarter part (e.g., الربع الأول, الربع الثاني...)
    # Matches "الربع" followed optionally by " " then one of the ordinals
    quarter_pattern = r"(الربع\s+(?:الأول|الثاني|الثالث|الرابع))"
    
    # Regex to find a 4-digit year (19xx or 20xx)
    year_pattern = r"((?:19|20)\d{2})"
    
    q_match = re.search(quarter_pattern, name)
    y_match = re.search(year_pattern, name)
    
    if q_match and y_match:
        # Found both parts, construct standardized name
        return f"{q_match.group(1)} {y_match.group(1)}"
    
    # Fallback: return the cleaned up filename if pattern not found
    return name.strip()


def _inject_sidebar_css():
    """Inject custom CSS to style the sidebar and its components."""
    st.markdown(
        """
        <style>
        /* Sidebar Background - Beige like buttons */
        /* Sidebar Container - Default (Collapsed) is transparent */
        section[data-testid="stSidebar"] {
            background-color: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }

        /* Sidebar Container - Expanded is Beige */
        section[data-testid="stSidebar"][aria-expanded="true"] {
            background-color: #faf4e4 !important;
            box-shadow: 1px 0 5px rgba(0,0,0,0.02);
        }
        
        /* Sidebar Content Headers */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            font-family: 'Tajawal', sans-serif;
            color: #0B9444;
        }

        /* Expand/Collapse Button Container */
        [data-testid="stSidebarCollapsedControl"] {
            background-color: transparent !important;
            color: #0B9444 !important;
            border: none !important;
            box-shadow: none !important;
            left: auto !important;
            right: 1rem !important;
            display: block !important; /* Ensure it's visible */
            z-index: 1000000 !important;
        }

        /* The actual button/icon inside */
        [data-testid="stSidebarCollapsedControl"] > svg,
        [data-testid="stSidebarCollapsedControl"] > img {
            background-color: #ffffff !important;
            border-radius: 50%;
            padding: 4px;
            border: 1px solid #e1d9c6;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            fill: #0B9444 !important;
            color: #0B9444 !important;
            width: 2rem !important;
            height: 2rem !important;
        }
        
        /* Hover effect */
        [data-testid="stSidebarCollapsedControl"]:hover > svg,
        [data-testid="stSidebarCollapsedControl"]:hover > img {
            background-color: #f0ebe0 !important;
            color: #007a37 !important;
            fill: #007a37 !important;
        }
        
        /* Ensure no other background leaks in collapsed state */
        div[data-testid="stSidebarNav"],
        div[data-testid="stSidebarUserContent"] {
            background-color: transparent !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

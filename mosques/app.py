from __future__ import annotations

import streamlit as st

import config
from config import validate_data_configuration, get_quarters, QUARTER_FILES, QUARTER_DATES
from data import (
    DataFileError,
    load_all_violator_data,
    load_industry_meta,
    load_regions,
    load_single_quarter_data,
    load_timeseries,
    precompute_helpers,
)
from ui import apply_base_styles
from ui.components import (
    render_meter_details,
    render_overview,
    render_province_details,
    render_province_map,
    render_quarter_upload,
)





def main():
    # 1. Page config + styles (must be first)
    st.set_page_config(
        page_title="لوحة متابعة المساجد",
        page_icon="assets/favicon.png",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_base_styles()

    # 2. Initialize session state
    if "refresh_quarters" not in st.session_state:
        st.session_state.refresh_quarters = False

    # 3. Load quarters configuration
    QUARTER_FILES, QUARTER_DATES, QUARTERS = get_quarters()
    st.session_state.refresh_quarters = False
    config.QUARTER_FILES = QUARTER_FILES
    config.QUARTER_DATES = QUARTER_DATES
    config.QUARTERS = QUARTERS

    # 4. Validate data configuration (no UI rendering yet)
    missing_critical, missing_optional = validate_data_configuration(quarter_files=QUARTER_FILES)
    if missing_critical:
        details = "\n".join(f"- {label}: {path}" for label, path in missing_critical.items())
        st.error(
            "تعذر بدء التطبيق بسبب نقص ملفات بيانات أساسية:\n"
            f"{details}\n"
            "يمكنك ضبط المتغير MOSQUES_DATA_DIR أو التأكد من وجود الملفات في المجلد الحالي."
        )
        st.stop()
    if missing_optional:
        details = "\n".join(f"- {label}: {path}" for label, path in missing_optional.items())
        st.markdown(
            f"""
            <div style="background-color: #ffe9b5; padding: 10px; border-radius: 5px; color: black; border: 1px solid #e0c486; direction: rtl; text-align: right; margin-bottom: 1rem;">
                <strong>تنبيه:</strong> بعض ملفات الربع غير متوفرة. سيتم عرض البيانات المتاحة فقط:<br>
                <pre style="background: transparent; border: none; color: black; font-family: inherit; white-space: pre-wrap; margin: 0;">{details}</pre>
            </div>
            """,
            unsafe_allow_html=True
        )

    # 5. Determine route based on query params
    query = st.query_params
    province_param = query.get("province", "")
    quarter_param = query.get("quarter", QUARTERS[0])
    meter_param = query.get("meter", "")
    view_param = query.get("view", "")

    if quarter_param not in QUARTERS + ["كل الأرباع"]:
        quarter_param = QUARTERS[0]

    # 6. LOAD DATA WITH SPINNER (no other UI visible during this phase)
    try:
        # Lazy load data based on route
        if meter_param:
            # Meter Details Route - minimal loading
            with st.spinner("⏳ جاري تحميل بيانات العداد..."):
                metadata = load_industry_meta()
                ts = load_timeseries()
                # Only load the specific quarter needed
                all_violator_data = load_all_violator_data(quarter_files=QUARTER_FILES)
                violator_sets, meter_to_province = precompute_helpers(all_violator_data, metadata)
            
            # 7. NOW render UI (after data is ready)
            render_meter_details(
                meter_param=meter_param,
                province_param=province_param,
                quarter_param=quarter_param,
                metadata=metadata,
                ts=ts,
                all_violator_data=all_violator_data,
                violator_sets=violator_sets,
            )
            return

        elif province_param and view_param == "map":
            # Province Map Route - skip timeseries
            with st.spinner("⏳ جاري تحميل خريطة المنطقة..."):
                regions = load_regions()
                metadata = load_industry_meta()
                # Load all quarters for map (users can switch between quarters)
                all_violator_data = load_all_violator_data(quarter_files=QUARTER_FILES)
            
            # Render UI after data is ready
            render_province_map(
                province_param=province_param,
                regions=regions,
                metadata=metadata,
                all_violator_data=all_violator_data,
            )
            return

        elif province_param:
            # Province Details Route - skip timeseries
            with st.spinner("⏳ جاري تحميل تفاصيل المنطقة..."):
                regions = load_regions()
                metadata = load_industry_meta()
                all_violator_data = load_all_violator_data(quarter_files=QUARTER_FILES)
            
            # Render UI after data is ready
            render_province_details(
                province_param=province_param,
                quarter_param=quarter_param,
                regions=regions,
                metadata=metadata,
                all_violator_data=all_violator_data,
            )
            return

        else:
            # Overview Route - load everything
            with st.spinner("⏳ جاري تحميل البيانات..."):
                regions = load_regions()
                metadata = load_industry_meta()
                all_violator_data = load_all_violator_data(quarter_files=QUARTER_FILES)
            
            # 8. RENDER ALL UI AFTER DATA IS LOADED (including the button)
            
            render_overview(
                quarter_param=quarter_param,
                regions=regions,
                metadata=metadata,
                all_violator_data=all_violator_data,
            )

    except DataFileError as exc:
        st.error(f"تعذر تحميل البيانات: {exc}")
        st.stop()


if __name__ == "__main__":
    main()

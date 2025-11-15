from __future__ import annotations

import streamlit as st

from config import QUARTERS, validate_data_configuration
from data import (
    DataFileError,
    load_all_violator_data,
    load_industry_meta,
    load_regions,
    load_timeseries,
    precompute_helpers,
)
from ui import apply_base_styles
from ui.components import (
    render_meter_details,
    render_overview,
    render_province_details,
    render_province_map,
)


def main():
    st.set_page_config(
        page_title="لوحة متابعة المساجد",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_base_styles()

    missing_critical, missing_optional = validate_data_configuration()
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
        st.warning(
            "بعض ملفات الربع غير متوفرة. سيتم عرض البيانات المتاحة فقط:\n"
            f"{details}"
        )

    try:
        regions = load_regions()
        ts = load_timeseries()
        metadata = load_industry_meta()
        all_violator_data = load_all_violator_data()
    except DataFileError as exc:
        st.error(f"تعذر تحميل البيانات: {exc}")
        st.stop()

    violator_sets, meter_to_province = precompute_helpers(all_violator_data, metadata)

    query = st.query_params
    province_param = query.get("province", "")
    quarter_param = query.get("quarter", QUARTERS[0])
    meter_param = query.get("meter", "")

    if quarter_param not in QUARTERS + ["كل الأرباع"]:
        quarter_param = QUARTERS[0]

    if meter_param:
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

    if province_param and query.get("view", "") == "map":
        render_province_map(
            province_param=province_param,
            regions=regions,
            metadata=metadata,
            all_violator_data=all_violator_data,
        )
        return

    if province_param:
        render_province_details(
            province_param=province_param,
            quarter_param=quarter_param,
            regions=regions,
            metadata=metadata,
            all_violator_data=all_violator_data,
        )
        return

    render_overview(
        quarter_param=quarter_param,
        regions=regions,
        metadata=metadata,
        all_violator_data=all_violator_data,
    )


if __name__ == "__main__":
    main()


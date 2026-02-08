"""Internationalization (i18n) module for the Mosques Dashboard.

This module provides language switching capabilities between Arabic and English.
"""
from __future__ import annotations

import streamlit as st

# Supported languages
LANGUAGES = {
    "ar": "العربية",
    "en": "English"
}

DEFAULT_LANGUAGE = "ar"

# Translation dictionaries
TRANSLATIONS = {
    "ar": {
        # Dashboard titles
        "dashboard_title": "لوحة متابعة المساجد",
        "province_details_title": "تفاصيل المنطقة",
        "meter_details_title": "تفاصيل العداد",
        
        # Province Details
        "back": "رجوع",
        "open_interactive_map": "فتح الخريطة التفاعلية",
        "details_of": "تفاصيل {province}",
        "search": "بحث",
        "search_placeholder": "ابحث...",
        "sort_by": "ترتيب حسب",
        "order": "الترتيب",
        "ascending": "تصاعدي",
        "descending": "تنازلي",
        "province_direction": "اتجاة المحافظات",
        "all": "الكل",
        "none": "لا يوجد",
        "governorate": "المحافظة",
        "period": "الفترة",
        "visit_status": "حالة الزيارة",
        "visited": "تمت الزيارة",
        "not_visited": "لم تتم الزيارة",
        "export": "تصدير",
        "active_filters": "فلاتر نشطة",
        "clear_all": "مسح الكل",
        "violating_mosques_list": "قائمة المساجد المتجاوزة",
        "no_violation_data": "لا توجد بيانات مخالفات متاحة لـ {quarter}",
        
        # Meter Details
        "meter_details_of": "تفاصيل {item}",
        "meter_label": "العداد: {id}",
        "total_consumption": "إجمالي الاستهلاك",
        "consumption_period_note": "(من {start_quarter} إلى {end_quarter})",
        "visit_date": "تاريخ الزيارة",
        "causes": "المسببات",
        "no_meter_data": "لا توجد بيانات تعريفية لهذا العداد.",
        "in_progress": "تحت الإجراء ⏳",
        "unspecified": "غير محدد",
        "no_info": "لا توجد معلومات",
        "processed": "تمت المعالجة",
        "both_periods": "كلا الفترتين",
        "open_google_maps": "فتح في خرائط قوقل",
        "no_coordinates": "لا تتوفر إحداثيات.",
        "quarter_summary": "ملخص الأرباع",
        "is_violating": "مُتجاوز؟",
        "morning_violation_pct": "نسبة التجاوز في الفترة الصباحية",
        "evening_violation_pct": "نسبة التجاوز في الفترة المسائية",
        "total_consumption_per_quarter": "إجمالي الاستهلاك لكل ربع",
        "chart_note_zero": "* إذا كانت القيمة 0، فهذا يعني أنه لم يتم رصد أي تجاوزات في ذلك الربع.",
        "consumption_value": "قيمة الاستهلاك",
        "quarter": "الربع",
        "from_month_to_month": "(من {start} إلى {end})",
        
        # Table Columns
        "mosque_name": "اسم المسجد",
        "meter_number": "رقم العداد",
        "morning_evening_period": "الفترة صباحا/مساء",
        "total_consumption_value": "قيمة الاستهلاك الإجمالي",
        "previously_violating": "مخالف سابقا",
        "location": "الموقع",
        "location_link": "رابط الموقع",
        "view_location": "عرض الموقع",
        "yes": "نعم",
        "no": "لا",
        "visited_date_unspecified": "تمت الزيارة (تاريخ غير محدد)",
        "visited_on_date": "تمت الزيارة ({date})",
        
        # Comparison / Delta
        "no_data_comparison": "لا توجد بيانات للمقارنة",
        "first_available_period": "أول فترة متاحة",
        "no_change_previous": "بدون تغيير مقارنة بالربع السابق",
        "compared_to_previous": "مقارنة بالربع السابق",
        "total_quarters": "إجمالي {count} أرباع",
        "sum_quarters": "مجموع {count} أرباع",
        "updated_until": "محدّث حتى {quarter}",
        "out_of_mosques": "من {count} مسجد",
        "unknown": "غير معروف",
        
        # Province Map
        "display_range": "نطاق العرض",
        "show_mosques": "عرض المساجد",
        "violators_only": "المتجاوزين فقط",
        "all_mosques": "جميع المساجد",
        "select_quarter": "اختر الربع",
        "all_quarters": "كل الأرباع",
        "non_violator": "غير متجاوز",
        "violator_visited": "متجاوز وتمت زيارته",
        "violator_not_visited": "متجاوز ولم تتم زيارته",
        "in_progress_status": "تحت الإجراء",
        "more_details": "تفاصيل اكثر",
        "google_maps": "موقع قوقل ماب",
        "map_layer_mosques": "المساجد",
        "no_violator_data": "لا توجد بيانات للمتجاوزين",
        "status": "الحالة",
        
        # Domain / Services
        "meter": "العداد",
        "name": "الاسم",
        
        # Other
        "riyal": "ريال",
        
        # KPI labels
        "total_mosques": "عدد المساجد في المملكة",
        "total_mosques_province": "عدد المساجد في {province}",
        "violating_mosques": "عدد المساجد المتجاوزة",
        "violating_mosques_quarter": "عدد المساجد المتجاوزة في {quarter}",
        "violating_mosques_riyadh": "عدد المساجد المتجاوزة في منطقة الرياض",
        
        # Quarter-related
        "select_quarter": "اختر الربع",
        "all_quarters": "كل الأرباع",
        "quarter_total": "مجموع {count} أرباع",
        "updated_until": "محدّث حتى {quarter}",
        "first_period": "أول فترة متاحة",
        "no_comparison_data": "لا توجد بيانات للمقارنة",
        "no_change": "بدون تغيير مقارنة بـ {quarter}",
        "compared_to_prev": "مقارنة بالربع السابق",
        
        # Chart titles
        "regional_distribution": "توزيع المساجد حسب المنطقة",
        "admin_regions_map": "خريطة المناطق الإدارية",
        "violators_by_quarter": "المتجاوزين عبر الأرباع في منطقة الرياض",
        "num_mosques": "عدد المساجد",
        "violating_mosques_count": "عدد المساجد المتجاوزة",
        "the_quarter": "الربع",
        "percentage": "النسبة %",
        
        # Status labels
        "violators": "متجاوزين",
        "non_violators": "غير متجاوزين",
        "region": "المنطقة",
        "violators_count": "عدد المتجاوزين",
        "mosques_visited": "المساجد التي تمت زيارتها",
        
        # Pagination
        "showing_rows": "عرض {start}-{end} من {total}",
        "rows_label": "صف:",
        "next": "التالي",
        "previous": "السابق",
        
        # Directions / Periods
        "morning": "صباحي",
        "evening": "مسائي",
        "north": "شمال",
        "south": "جنوب",
        "east": "شرق",
        "west": "غرب",
        "middle": "وسط",
        
        # Months
        "month_jan": "يناير",
        "month_feb": "فبراير",
        "month_mar": "مارس",
        "month_apr": "أبريل",
        "month_may": "مايو",
        "month_jun": "يونيو",
        "month_jul": "يوليو",
        "month_aug": "أغسطس",
        "month_sep": "سبتمبر",
        "month_oct": "أكتوبر",
        "month_nov": "نوفمبر",
        "month_dec": "ديسمبر",
        "from_to": "من {start} إلى {end}",
        
        # Directions specific
        "gov_north_riyadh": "محافظات شمال الرياض",
        "gov_south_riyadh": "محافظات جنوب الرياض",
        "gov_east_riyadh": "محافظات شرق الرياض",
        "gov_west_riyadh": "محافظات غرب الرياض",
        "city_riyadh": "مدينة الرياض",
        
        # Header
        "contact_us": "تواصل معنا",
        "department": "الإدارة",
        "dept_name": "الإدارة العامة للذكاء الاصطناعي وتطوير الاعمال",
        "email": "البريد الإلكتروني",
        "name": "الاسم",
        
        # Province details
        "select_province": "اختر المنطقة",
        "all_provinces": "جميع المناطق",
        "select_governorate": "اختر المحافظة",
        "all_governorates": "جميع المحافظات",
        "rows_per_page": "عدد الصفوف",
        "page_number": "رقم الصفحة",
        "clear_filters": "مسح الفلاتر",
        "export": "تصدير",
        
        # Table headers
        "mosque_name": "اسم المسجد",
        "meter_id": "رقم العداد",
        "governorate": "المحافظة",
        "visit_status": "حالة الزيارة",
        "consumption": "الاستهلاك",
        "bill_value": "قيمة الفاتورة",
        
        # Meter details
        "total_bills": "إجمالي الفواتير",
        "bills_per_quarter": "إجمالي الفواتير حسب الربع",
        "meter_location": "موقع العداد",
        "back_to_list": "العودة للقائمة",
        
        # Map popups
        "province_label": "المحافظة",
        "no_data": "لا توجد بيانات",
        
        # Misc
        "loading": "جاري التحميل...",
        "error": "خطأ",
        "no_results": "لا توجد نتائج",
    },
    "en": {
        # Dashboard titles
        "dashboard_title": "Mosques Monitoring Dashboard",
        "province_details_title": "Province Details",
        "meter_details_title": "Meter Details",
        
        # Province Details
        "back": "Back",
        "open_interactive_map": "Open Interactive Map",
        "details_of": "Details of {province}",
        "search": "Search",
        "search_placeholder": "Search...",
        "sort_by": "Sort By",
        "order": "Order",
        "ascending": "Ascending",
        "descending": "Descending",
        "province_direction": "Province Direction",
        "all": "All",
        "none": "None",
        "governorate": "Governorate",
        "period": "Period",
        "visit_status": "Visit Status",
        "visited": "Visited",
        "not_visited": "Not Visited",
        "export": "Export",
        "active_filters": "Active Filters",
        "clear_all": "Clear All",
        "violating_mosques_list": "Suspected Mosques List",
        "no_violation_data": "No suspected mosques data available for {quarter}",
        
        # Meter Details
        "meter_details_of": "Details of {item}",
        "meter_label": "Meter: {id}",
        "total_consumption": "Total Consumption",
        "consumption_period_note": "(From {start_quarter} to {end_quarter})", # Dynamic
        "visit_date": "Visit Date",
        "causes": "Causes",
        "no_meter_data": "No identification data found for this meter.",
        "in_progress": "In Progress ⏳",
        "unspecified": "Unspecified",
        "no_info": "No information",
        "processed": "Processed",
        "both_periods": "Both Periods",
        "open_google_maps": "Open in Google Maps",
        "no_coordinates": "No coordinates available.",
        "quarter_summary": "Quarter Summary",
        "is_violating": "Suspected?",
        "morning_violation_pct": "Morning Suspicion %",
        "evening_violation_pct": "Evening Suspicion %",
        "total_consumption_per_quarter": "Total Consumption per Quarter",
        "chart_note_zero": "* If value is 0, it means no suspected activity was detected in that quarter.",
        "consumption_value": "Consumption Value",
        "quarter": "Quarter",
        "from_month_to_month": "(from {start} to {end})",
        
        # Table Columns
        "mosque_name": "Mosque Name",
        "meter_number": "Meter Number",
        "morning_evening_period": "Morning/Evening Period",
        "total_consumption_value": "Total Consumption Value",
        "previously_violating": "Previously Suspected",
        "location": "Location",
        "location_link": "Location Link",
        "view_location": "View Location",
        "yes": "Yes",
        "no": "No",
        "visited_date_unspecified": "Visited (Date unspecified)",
        "visited_on_date": "Visited ({date})",
        
        # Comparison / Delta
        "no_data_comparison": "No data for comparison",
        "first_available_period": "First available period",
        "no_change_previous": "No change from previous quarter",
        "compared_to_previous": "compared to previous quarter",
        "total_quarters": "Total {count} quarters",
        "sum_quarters": "Sum of {count} quarters",
        "updated_until": "Updated until {quarter}",
        "out_of_mosques": "out of {count} mosques",
        "unknown": "Unknown",
        
        # Province Map
        "display_range": "Display Range",
        "show_mosques": "Show Mosques",
        "violators_only": "Suspected Only",
        "all_mosques": "All Mosques",
        "select_quarter": "Select Quarter",
        "all_quarters": "All Quarters",
        "non_violator": "Non-Suspected",
        "violator_visited": "Suspected (Visited)",
        "violator_not_visited": "Suspected (Not Visited)",
        "in_progress_status": "In Progress", # "in_progress" exists with hourglass
        "more_details": "More Details",
        "google_maps": "Google Maps",
        "map_layer_mosques": "Mosques",
        "no_violator_data": "No suspected mosques data available",
        "status": "Status",
        
        # Domain / Services
        "meter": "Meter",
        "name": "Name",
        
        # Other
        "riyal": "SAR",
        
        # KPI labels
        "total_mosques": "Total Mosques in the Kingdom of Saudi Arabia",    
        "total_mosques_province": "Mosques in {province}",
        "violating_mosques": "Suspected Mosques",
        "violating_mosques_quarter": "Suspected Mosques in {quarter}",
        "violating_mosques_riyadh": "Suspected Mosques in Riyadh Province",
        
        # Quarter-related
        "select_quarter": "Select Quarter",
        "all_quarters": "All Quarters",
        "quarter_total": "Total of {count} quarters",
        "updated_until": "Updated until {quarter}",
        "first_period": "First available period",
        "no_comparison_data": "No comparison data available",
        "no_change": "No change compared to {quarter}",
        "compared_to_prev": "compared to previous quarter",
        
        # Chart titles
        "regional_distribution": "Mosque Distribution by Region",
        "admin_regions_map": "Administrative Regions Map",
        "violators_by_quarter": "Suspected Mosques by Quarter in Riyadh Province",
        "num_mosques": "Number of Mosques",
        "violating_mosques_count": "Number of Suspected Mosques",
        "the_quarter": "Quarter",
        "percentage": "Percentage %",
        
        # Status labels
        "violators": "Suspected",
        "non_violators": "Non-Suspected",
        "region": "Region",
        "violators_count": "Suspected Count",
        "mosques_visited": "Visited Mosques",
        
        # Pagination
        "showing_rows": "Showing {start}-{end} of {total}",
        "rows_label": "Rows:",
        "next": "Next",
        "previous": "Previous",
        
        # Directions / Periods
        "morning": "Morning",
        "evening": "Evening",
        "north": "North",
        "south": "South",
        "east": "East",
        "west": "West",
        "middle": "Middle",
        
        # Months
        "month_jan": "January",
        "month_feb": "February",
        "month_mar": "March",
        "month_apr": "April",
        "month_may": "May",
        "month_jun": "June",
        "month_jul": "July",
        "month_aug": "August",
        "month_sep": "September",
        "month_oct": "October",
        "month_nov": "November",
        "month_dec": "December",
        "from_to": "from {start} to {end}",
        
        # Directions specific
        "gov_north_riyadh": "North Riyadh Governorates",
        "gov_south_riyadh": "South Riyadh Governorates",
        "gov_east_riyadh": "East Riyadh Governorates",
        "gov_west_riyadh": "West Riyadh Governorates",
        "city_riyadh": "Riyadh City",
        
        # Header
        "contact_us": "Contact Us",
        "department": "Department",
        "dept_name": "General Department of AI and Business Development",
        "email": "Email",
        "name": "Name",
        
        # Province details
        "select_province": "Select Province",
        "all_provinces": "All Provinces",
        "select_governorate": "Select Governorate",
        "all_governorates": "All Governorates",
        "rows_per_page": "Rows per page",
        "page_number": "Page number",
        "clear_filters": "Clear Filters",
        "export": "Export",
        
        # Table headers
        "mosque_name": "Mosque Name",
        "meter_id": "Meter ID",
        "governorate": "Governorate",
        "visit_status": "Visit Status",
        "consumption": "Consumption",
        "bill_value": "Bill Value",
        
        # Meter details
        "total_bills": "Total Bills",
        "bills_per_quarter": "Total Bills per Quarter",
        "meter_location": "Meter Location",
        "back_to_list": "Back to List",
        
        # Map popups
        "province_label": "Province",
        "no_data": "No data available",
        
        # Misc
        "loading": "Loading...",
        "error": "Error",
        "no_results": "No results",
        
        # Governorates (Riyadh & Common)
        "الرياض": "Riyadh",
        "الدرعية": "Ad Diriyah",
        "الخرج": "Al Kharj",
        "الدلم": "Ad Dilam",
        "المجمعة": "Al Majma'ah",
        "القويعية": "Al Quway'iyah",
        "وادي الدواسر": "Wadi Ad Dawasir",
        "الزلفي": "Az Zulfi",
        "شقراء": "Shaqra",
        "حوطة بني تميم": "Hotat Bani Tamim",
        "عفيف": "Afif",
        "الغاط": "Al Ghat",
        "ثادق": "Thadiq",
        "حريملاء": "Huraymila",
        "رماح": "Ruma",
        "ضرما": "Dharma",
        "المزاحمية": "Al Muzahimiyah",
        "السليل": "As Sulayyil",
        "الأفلاج": "Al Aflaj",
        "الحريق": "Al Hariq",
        "مرات": "Marat",
        "الدوادمي": "Ad Dawadimi",
        "المهد": "Al Mahd",
        "الرين": "Ar Rayn",

        # Extended Governorates (All Regions)
        "أضم": "Adham",         "أبها": "Abha",         "أبو عريش": "Abu Arish", 
        "أحد المسارحة": "Ahad Al Masarihah", "أحد رفيدة": "Ahad Rafidah", "الأسياح": "Al Asyah", 
        "الأمويه": "Al Amwah", "الا مواة": "Al Amwah", "الأحساء": "Al Ahsa", "الاحساء": "Al Ahsa",
        "الأفلاج": "Al Aflaj", "الباحة": "Al Baha", 
        "البدائع": "Al Badai", "البدع": "Al Bida", "البرك": "Al Birk", "البكيرية": "Al Bukayriyah",
        "الجبيل": "Al Jubail", "الجموم": "Al Jumum", "الحائط": "Al Hait", "الحجرة": "Al Hajarah",
        "الحرث": "Al Harath", "الحرجة": "Al Harajah", "الحناكية": "Al Henakiyah", "الخبر": "Al Khobar",
        "الخرمة": "Al Khurmah", "الخفجي": "Al Khafji", "الدائر": "Ad Dair", "الدرب": "Ad Darb",
        "الدمام": "Dammam", "الرس": "Ar Rass", "الريث": "Ar Reeth", "السليمي": "As Sulaimi",
        "الشماسية": "Ash Shimasiyah", "الشملي": "Ash Shamli", "الشنان": "Ash Shinan", "الطائف": "Taif",
        "الطوال": "At Tuwal", "العارضة": "Al Aridhah", "العديد": "Al Udayd", "العرضيات": "Al Ardiyat",
        "العقيق": "Al Aqiq", "العلا": "Al Ula", "العويقيلة": "Al Uwayqilah", "العيدابي": "Al Edabi",
        "العيص": "Al Ais", "الغزالة": "Al Ghazalah", "القرى": "Al Qura", "القريات": "Al Qurayyat",
        "القطيف": "Al Qatif", "القنفذة": "Al Qunfudhah", "الكامل": "Al Kamil", "الليث": "Al Lith",
        "المجاردة": "Al Majardah", "المخواة": "Al Makhwah", "المدينة المنورة": "Madinah",
        "المذنب": "Al Mithnab", "المندق": "Al Mandaq", "المويه": "Al Muwayh", "الموية": "Al Muwayh",
        "النبهانية": "An Nabhaniyah", "النعيرية": "An Nuayriyah", "النماص": "An Namas",
        "الوجه": "Al Wajh", "الوجة": "Al Wajh", "أملج": "Umluj", "املج": "Umluj",
        "بارق": "Bariq", "بالقرن": "Balqarn", "بحرة": "Bahrah", "بدر": "Badr", "بدر الجنوب": "Badr Al Janub",
        "بريدة": "Buraydah", "بقعاء": "Baqaa", "بقيق": "Abqaiq", "بلجرشي": "Baljurashi",
        "بني حسن": "Bani Hassan", "بيش": "Baish", "بيشة": "Bisha", "تبوك": "Tabuk",
        "تثليث": "Tathlith", "تربة": "Turabah", "تنومة": "Tanumah", "تيماء": "Tayma",
        "ثار": "Thar", "جازان": "Jazan", "جدة": "Jeddah", "حائل": "Hail", "حبونا": "Hubuna",
        "حفر الباطن": "Hafar Al Batin", "حقل": "Haql", "حوطة بني تميم": "Hotat Bani Tamim",
        "حوطة بنى تميم": "Hotat Bani Tamim", "خباش": "Khabash", "خليص": "Khulais",
        "خميس مشيط": "Khamis Mushait", "خيبر": "Khaybar", "دومة الجندل": "Dumat Al Jandal",
        "رأس تنورة": "Ras Tanura", "رابغ": "Rabigh", "رجال ألمع": "Rijal Alma", "رجال المع": "Rijal Alma",
        "رفحاء": "Rafha", "رنية": "Ranyah", "رياض الخبراء": "Riyadh Al Khabra", "سراة عبيدة": "Sarat Abidah",
        "سكاكا": "Sakaka", "سميراء": "Samira", "شرورة": "Sharurah", "صامطة": "Samtah",
        "صبياء": "Sabya", "ضباء": "Duba", "ضرية": "Daria", "ضمد": "Damad", "طبرجل": "Tabarjal",
        "طريب": "Tathleeth", "طريف": "Turaif", "ظهران الجنوب": "Dhahran Al Janub", "عرعر": "Arar",
        "عقلة الصقور": "Uqlat As Suqoor", "عنيزة": "Unaizah", "عيون الجواء": "Uyun Al Jiwa",
        "فرسان": "Farasan", "فرعة غامد الزناد": "Ghamid Az Zinad", "فيفا": "Fifa",
        "قرية العليا": "Qaryat Al Ulya", "قلوة": "Qilwah", "محايل": "Mahayil", "مكة المكرمة": "Makkah",
        "موقق": "Mawqaq", "ميسان": "Maysan", "نجران": "Najran", "هروب": "Harub",
        "وادي الفرع": "Wadi Al Fara", "يدمة": "Yadamah", "ينبع": "Yanbu",
    }
}

# Quarter name translations
QUARTER_NAMES = {
    "ar": {
        "الربع الرابع 2024": "الربع الرابع 2024",
        "الربع الأول 2025": "الربع الأول 2025",
        "الربع الثاني 2025": "الربع الثاني 2025",
        "الربع الثالث 2025": "الربع الثالث 2025",
    },
    "en": {
        "الربع الرابع 2024": "Q4 2024",
        "الربع الأول 2025": "Q1 2025",
        "الربع الثاني 2025": "Q2 2025",
        "الربع الثالث 2025": "Q3 2025",
    }
}

# Month mapping for formatting
MONTHS = {
    "ar": {
        1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل",
        5: "مايو", 6: "يونيو", 7: "يوليو", 8: "أغسطس",
        9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
    },
    "en": {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
}


def get_language() -> str:
    """Get the current language from session state."""
    if "language" not in st.session_state:
        st.session_state.language = DEFAULT_LANGUAGE
    return st.session_state.language


def set_language(lang: str) -> None:
    """Set the current language in session state."""
    if lang in LANGUAGES:
        st.session_state.language = lang


def toggle_language() -> None:
    """Toggle between Arabic and English."""
    current = get_language()
    new_lang = "en" if current == "ar" else "ar"
    set_language(new_lang)


def t(key: str, **kwargs) -> str:
    """Translate a key to the current language.
    
    Args:
        key: The translation key
        **kwargs: Format arguments for string interpolation
        
    Returns:
        The translated string, or the key if not found
    """
    lang = get_language()
    translations = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE])
    text = translations.get(key, key)
    
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    
    return text


def get_quarter_name(arabic_name: str) -> str:
    """Get the translated quarter name."""
    lang = get_language()
    return QUARTER_NAMES.get(lang, QUARTER_NAMES["ar"]).get(arabic_name, arabic_name)


def get_month_name(month_num: int) -> str:
    """Get the translated month name (1-12)."""
    lang = get_language()
    return MONTHS.get(lang, MONTHS["ar"]).get(month_num, str(month_num))


def is_english() -> bool:
    """Check if current language is English."""
    return get_language() == "en"


def is_arabic() -> bool:
    """Check if current language is Arabic."""
    return get_language() == "ar"

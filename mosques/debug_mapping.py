import pandas as pd
import sys
import os

# Adjust path to import from mosques folder
sys.path.append('mosques')

try:
    from data import load_all_violator_data, load_industry_meta, find_coord_cols
    
    def debug_counts():
        print("Loading metadata...")
        metadata = load_industry_meta()
        
        metadata['METER_ID_STR_CLEAN'] = metadata['METER_ID_STR'].astype(str).str.strip()
        
        provinces = metadata['Province'].unique()
        print(f"\nProvinces in Metadata: {provinces}")

        print("\nLoading violator data...")
        all_violator_data = load_all_violator_data()

        for q_name, df in all_violator_data.items():
            print(f"\nQuarter: {q_name}")
            print(f"  Total rows in file: {len(df)}")
            
            if df.empty or "رقم العداد" not in df.columns:
                print("  No data or 'رقم العداد' column missing.")
                continue

            temp = df.copy()
            temp["رقم العداد"] = temp["رقم العداد"].astype(str).str.strip()
            
            # Check if any province-like column exists in the file
            possible_prov_cols = [c for c in df.columns if any(x in c for x in ["منطقة", "المنطقة", "Province", "Region"])]
            if possible_prov_cols:
                for col in possible_prov_cols:
                    print(f"  - Values in column '{col}': {df[col].unique()[:5]}")

            matched_any = False
            for province in provinces:
                p_meta = metadata[metadata["Province"] == province]
                allowed_meters = set(p_meta["METER_ID_STR_CLEAN"].unique())
                
                violator_meters = set(temp[temp["رقم العداد"].isin(allowed_meters)]["رقم العداد"].unique())
                
                if len(violator_meters) > 0:
                    print(f"  - {province:25}: {len(violator_meters)} violators matched")
                    matched_any = True
            
            if not matched_any:
                print("  - WARNING: NO matches for ANY province!")
                print(f"  - First 5 meter IDs in file: {temp['رقم العداد'].head().tolist()}")
                print(f"  - First 5 meter IDs in RIYADH metadata: {metadata[metadata['Province']=='RIYADH PROVINCE']['METER_ID_STR_CLEAN'].head().tolist()}")

    debug_counts()

except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()

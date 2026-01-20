import pandas as pd
import sys

# Hardcoded path to file
file_path = r"c:\Users\AlosaiNK\OneDrive - Ministry of Energy\Documents\Mosques\mosques-dashboard-v2\mosques\Industry Code with Population 1.parquet"

try:
    print(f"Loading {file_path}...")
    df = pd.read_parquet(file_path)
    
    # Analyze "GOVERNORATE_NAME_AR"
    col = "GOVERNORATE_NAME_AR"
    if col in df.columns:
        print(f"\n--- {col} (Unique) ---")
        uniques = sorted(df[col].astype(str).unique())
        count = 0
        for u in uniques:
            if u and u.lower() != "nan" and u.strip() != "":
                # Print clean list for copying
                print(u)
                count += 1
        print(f"\nTotal unique governorates: {count}")
    else:
        print(f"\nColumn '{col}' not found.")
    
except Exception as e:
    print(f"Error: {e}")

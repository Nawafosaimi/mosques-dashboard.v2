import pandas as pd
from pathlib import Path

def debug_riyadh():
    master_path = Path('mosques/Industry Code with Population 1.parquet')
    if not master_path.exists():
        print(f"File not found: {master_path}")
        return

    df = pd.read_parquet(master_path)
    riyadh = df[df['Province'].str.strip() == 'RIYADH PROVINCE'].copy()
    
    print(f"Total rows in Riyadh (Master): {len(riyadh)}")
    print(f"Unique Meter Numbers: {riyadh['Meter Number'].nunique()}")
    
    # Check for NaNs in coordinates
    nan_coords = riyadh[riyadh['X Coordinates'].isna() | riyadh['Y Coordinates'].isna()]
    print(f"Rows with NaN coordinates: {len(nan_coords)}")
    
    # Check for duplicates
    dupes = riyadh[riyadh.duplicated(subset=['Meter Number'], keep=False)]
    if not dupes.empty:
        print(f"Found {len(dupes)} rows with duplicated Meter Numbers")
        print("Sample of duplicates:")
        print(dupes[['Meter Number', 'X Coordinates', 'Y Coordinates', 'Name']].head(10))
    else:
        print("No duplicate Meter Numbers found.")

    # Filtered count (the count we expect on the map)
    filtered = riyadh.dropna(subset=['X Coordinates', 'Y Coordinates'])
    print(f"Total markers expected on map (Riyadh): {len(filtered)}")

if __name__ == "__main__":
    debug_riyadh()

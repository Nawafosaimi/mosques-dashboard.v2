# Setup Guide - Mosque Dashboard

## Prerequisites
- Python 3.9 or higher
- pip (Python package installer)

## Installation Steps

### 1. Clone or Download the Project
```bash
# If using Git:
git clone <your-repo-url>
cd energy

# Or simply copy the folder to your device
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

Or install directly:
```bash
pip install streamlit pandas geopandas folium streamlit-folium plotly openpyxl python-dotenv shapely
```

### 3. Configure Environment (Optional but Recommended)

**Important:** The `.env` file is NOT included in the repository for security reasons.

Copy `mosques/env.example` to `mosques/.env` and adjust paths for your device:

**On Windows:**
```bash
cd mosques
copy env.example .env
```

**On Mac/Linux:**
```bash
cd mosques
cp env.example .env
```

Then edit `.env` with your local paths:
```env
# Example for Windows:
MOSQUES_DATA_DIR=D:/your-path/energy/mosques
MOSQUES_CACHE_DIR=D:/your-path/energy/mosques/cache

# Example for Mac/Linux:
MOSQUES_DATA_DIR=/Users/yourname/projects/energy/mosques
MOSQUES_CACHE_DIR=/Users/yourname/projects/energy/mosques/cache
```

**Note:** If you don't create a `.env` file, the app will use relative paths from the `mosques` directory by default.

### 4. Run the Application
```bash
cd mosques
streamlit run app.py
```

Or from the root directory:
```bash
streamlit run mosques/app.py
```

The app will open in your browser at `http://localhost:8501`

## Project Structure
```
energy/
├── mosques/
│   ├── app.py                 # Main entry point
│   ├── config.py              # Configuration
│   ├── assets/
│   │   └── style.css          # Styling
│   ├── data/
│   │   └── loaders.py         # Data loading functions
│   ├── ui/
│   │   ├── layout.py          # UI layout utilities
│   │   ├── utils.py           # Chart utilities
│   │   └── components/        # UI components
│   ├── regions.geojson        # GeoJSON data
│   └── *.xlsx                 # Data files
└── requirements.txt
```

## 🔒 Security & Environment Files

### What Gets Pushed to GitHub:
✅ `env.example` - Template file with example values  
✅ All code files (`.py`, `.css`, etc.)  
✅ `requirements.txt`  
✅ Documentation (`.md` files)  

### What Does NOT Get Pushed:
❌ `.env` - Your personal configuration (in `.gitignore`)  
❌ `__pycache__/` - Python cache files  
❌ `*.parquet` - Cache files  
❌ `.vscode/`, `.idea/` - IDE settings  

### On Each New Device:
1. Clone the repository
2. Create your own `.env` file from `env.example`
3. Update paths to match your local setup
4. Run the app

## Troubleshooting

### Cache Issues
If you see old styling or data, clear Streamlit cache:
```bash
streamlit cache clear
```

Or force refresh in browser: **Ctrl + Shift + F5**

### Module Not Found
Make sure you're in the correct directory and all dependencies are installed:
```bash
pip install -r requirements.txt --upgrade
```

### Port Already in Use
If port 8501 is busy:
```bash
streamlit run app.py --server.port 8502
```


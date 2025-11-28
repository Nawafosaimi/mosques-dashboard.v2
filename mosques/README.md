# Mosques Dashboard

A Streamlit application for monitoring and visualizing mosque violations across different provinces.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd mosques
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the app

```bash
streamlit run app.py
```

## Configuration

Environment variables in `.env` (or your shell) control where the raw data lives. Copy `env.example` to `.env` and set:

- `MOSQUES_DATA_DIR`: Path to the directory containing parquet/Excel files (defaults to current directory if not set).
- `MOSQUES_CACHE_DIR`: Path for auto-generated parquet caches (defaults to `<data_dir>/cache`).
- `MOSQUES_REGIONS_CACHE_FILE` / `REGIONS_SIMPLIFY_TOLERANCE`: Control the cached, simplified GeoJSON that powers the overview map.

The app validates these paths and the required files on startup.

## Project Layout

- `app.py`: Main entry point that wires data and UI components.
- `config.py`: Shared constants, data paths, and quarter definitions.
- `data/`: Data loading, caching logic, and `quarters_config.json`.
- `domain/`: Reusable helpers (string cleanup, localization, etc.).
- `ui/`:
  - `layout.py`: Global styling and CSS injection.
  - `components/`: Streamlit views (`overview`, `province_details`, `province_map`, `meter_details`).
- `assets/`: Static assets like `style.css` and images.
- `uploaded_quarters/`: Directory where user-uploaded quarter data is stored.

## Testing

Run tests using `pytest`:

```bash
pytest
```


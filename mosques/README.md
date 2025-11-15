# Mosques Dashboard

## Running the app

```bash
cd mosques
streamlit run app.py
```

Environment variables in `.env` (or your shell) control where the raw data lives. Copy `env.example` to `.env` and set:

- `MOSQUES_DATA_DIR` when the parquet/Excel files live outside the repo.
- `MOSQUES_CACHE_DIR` if you want the auto-generated parquet caches saved somewhere else (defaults to `<data_dir>/cache`).
- `MOSQUES_REGIONS_CACHE_FILE` / `REGIONS_SIMPLIFY_TOLERANCE` to control the cached, simplified GeoJSON that powers the overview map.

The app validates these paths and the required files on startup.

```powershell
$env:MOSQUES_DATA_DIR="D:\path\to\data"
streamlit run app.py
```

## Project layout

- `config.py` – shared constants, data paths, and quarter definitions.
- `data/` – loading/caching logic for GeoJSON, parquet, and Excel files.
- `domain/` – reusable helpers (string cleanup, boolean localization, marker prep).
- `ui/layout.py` – global styling (injects `assets/style.css`).
- `ui/components/` – Streamlit views (`overview`, `province`, `map`, `meter`).
- `assets/style.css` – consolidated RTL theme.
- `app.py` – main entry point that wires data + UI components.
- `1_Landing.py` – thin wrapper to keep older launch commands working.

Add tests under `tests/` (fixtures can live in `tests/data_fixtures`). Use `python -m compileall mosques` or `pytest` before committing.


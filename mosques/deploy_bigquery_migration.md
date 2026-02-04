# Migrating to Google BigQuery on GCP

This guide explains how to refactor the application to fetch quarter data from Google BigQuery instead of local Excel/Parquet files when deployed to Google Cloud Platform (GCP).

## 1. Infrastructure Setup

Before changing code, ensure your GCP environment is ready:

1.  **BigQuery Dataset**: Ensure your data is loaded into BigQuery tables (e.g., `your-project.mosques_data.violations`).
2.  **Service Account**: The Service Account used by your Cloud Run instance must have the following IAM roles:
    *   `BigQuery Data Viewer`
    *   `BigQuery Job User`

## 2. Update Dependencies

Add the necessary Google Cloud libraries to your `requirements.txt`:

```text
google-cloud-bigquery
db-dtypes
pandas-gbq
```

## 3. Refactor Data Loading (`data/loaders.py`)

You need to replace the file-reading logic with BigQuery query logic.

### Import the Client
```python
from google.cloud import bigquery
```

### Update `load_single_quarter_data`

**Current (File-based):**
```python
def load_single_quarter_data(quarter):
    path = quarter_files[quarter]
    return pd.read_excel(path)
```

**New (BigQuery-based):**
```python
@st.cache_data(ttl=3600)  # Cache for 1 hour to save costs/time
def load_single_quarter_data(quarter):
    client = bigquery.Client()
    
    # Map the quarter string (e.g., "الربع الثالث 2025") to a query parameter
    # You might need a mapping function if your DB uses dates or IDs
    
    query = """
        SELECT 
            meter_id AS `رقم العداد`,
            mosque_name AS `اسم المسجد`,
            province AS `المحافظة`,
            -- Select other columns and map them to the expected Arabic names
            *
        FROM `your-project.mosques_data.violations`
        WHERE quarter_name = @quarter_name
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("quarter_name", "STRING", quarter)
        ]
    )
    
    # Returns a pandas DataFrame directly
    df = client.query(query, job_config=job_config).to_dataframe() 
    return df
```

## 4. Update Configuration (`config.py`)

1.  **Remove File Paths**: You no longer need `QUARTER_FILES` pointing to local paths.
2.  **Add BigQuery Config**: Add constants for your project and dataset.

```python
# config.py
BQ_PROJECT_ID = os.environ.get("BQ_PROJECT_ID", "your-default-project")
BQ_DATASET_ID = os.environ.get("BQ_DATASET_ID", "mosques_data")
```

## 5. Authentication

When running on **Cloud Run**, authentication is handled automatically via the Service Account. You do **not** need to manage JSON key files.

For **local development**, you can authenticate using the gcloud CLI:
```bash
gcloud auth application-default login
```

## 6. Caching Strategy

BigQuery queries incur costs and latency.
*   **Keep `st.cache_data`**: This is crucial. It ensures that once a quarter is loaded, it stays in the app's memory (RAM) and doesn't trigger a new query for every user interaction.
*   **TTL (Time To Live)**: Consider adding a `ttl` parameter to `st.cache_data` (e.g., `ttl=3600` for 1 hour) if the data updates frequently. If data is static per quarter, indefinite caching is fine.

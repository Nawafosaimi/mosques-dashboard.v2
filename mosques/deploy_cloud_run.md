# Deploy to Google Cloud Run

This guide explains how to deploy the Mosques Dashboard to Google Cloud Run.

## Prerequisites

1.  **Google Cloud SDK**: Ensure you have the `gcloud` CLI installed and authenticated.
2.  **Docker**: (Optional if using Cloud Build) You need Docker installed to build locally.
3.  **Google Cloud Project**: You need a project with billing enabled.

## 1. Setup Environment Variables

Set your project ID and region:

```bash
export PROJECT_ID="testing-444715"
export REGION="me-central2" # e.g., Riyadh (me-west1) or other preferred region
export SERVICE_NAME="mosques-dashboard"
```

## 2. Enable Required Services

```bash
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com
```

## 3. Build and Push the Image

You can use Google Cloud Build to build the image in the cloud without needing local Docker:

```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME
```

*Alternatively, if you want to use Artifact Registry (recommended for newer projects):*

1.  Create a repository:
    ```bash
    gcloud artifacts repositories create my-repo --repository-format=docker \
        --location=$REGION --description="Docker repository"
    ```
2.  Build and push:
    ```bash
    gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/my-repo/$SERVICE_NAME
    ```

## 4. Deploy to Cloud Run

Deploy the image you just built:

```bash
gcloud run deploy $SERVICE_NAME \
    --image $REGION-docker.pkg.dev/$PROJECT_ID/mosques-dashbaord/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --project $PROJECT_ID \
    --memory 4Gi
```

*Note: Adjust `--memory` if your data requires more RAM.*

## 5. Verify Deployment

After deployment, the command will output a Service URL (e.g., `https://mosques-dashboard-xyz-uc.a.run.app`). Open this URL in your browser.

## Troubleshooting

-   **Memory Errors**: If the app crashes on startup, try increasing memory: `--memory 4Gi`.
-   **Port Issues**: Ensure the `Dockerfile` exposes port 8080 (default) or that you pass the correct port to Cloud Run.
-   **Forbidden Error (403)**: If you see "Forbidden", run this command to allow public access:
    ```bash
    gcloud run services add-iam-policy-binding $SERVICE_NAME \
        --member="allUsers" \
        --role="roles/run.invoker" \
        --region=$REGION \
        --project=$PROJECT_ID
    ```

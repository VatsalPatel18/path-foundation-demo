# Path Foundation Demo

This repository contains the **PathoLens** API service built with FastAPI and the Google Agent Development Kit.

## Environment Variables
Create a `.env` file based on `.env.example` and provide values for your Google Cloud project and Vertex AI resources. The variables are:

| Variable | Description |
| --- | --- |
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCP_REGION` | Region for Google Cloud services |
| `MEDGEMMA_ENDPOINT_ID` | Vertex AI MedGemma endpoint ID |
| `GCS_ARTIFACT_BUCKET` | GCS bucket for generated artifacts |
| `WSI_BUCKET` | GCS bucket containing WSIs |
| `ROOT_AGENT_MODEL` | LLM used by the root agent |
| `SNAPSHOT_AGENT_MODEL` | LLM used by the snapshot manager |
| `ROI_AGENT_MODEL` | LLM used by the ROI manager |
| `SLIDE_AGENT_MODEL` | LLM used by the slide manager |

Example contents of `.env`:

```bash
# --- GCP Configuration ---
GCP_PROJECT_ID="your-gcp-project-id"
GCP_REGION="us-central1"

# --- Vertex AI MedGemma Configuration ---
MEDGEMMA_ENDPOINT_ID="your-medgemma-endpoint-id"

# --- Cloud Storage Configuration ---
GCS_ARTIFACT_BUCKET="your-patholens-artifacts-bucket"
WSI_BUCKET="your-patholens-wsi-bucket"

# --- Agent Model Configuration ---
ROOT_AGENT_MODEL="gemini-1.5-flash-001"
SNAPSHOT_AGENT_MODEL="gemini-1.5-flash-001"
ROI_AGENT_MODEL="gemini-1.5-flash-001"
SLIDE_AGENT_MODEL="gemini-1.5-flash-001"
```

## Setup Instructions

1. **Install system dependencies** (Ubuntu/Debian):
   ```bash
   sudo apt-get update && sudo apt-get install -y \
       python3-venv build-essential openslide-tools libvips-dev git
   ```

2. **Create and activate a Python virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r patholens/app/requirements.txt
   ```

3. **Run the API locally**:
   ```bash
   cd patholens/app
   uvicorn services.main:app --host 0.0.0.0 --port 8080 --reload
   ```

4. **Build and run with Docker** (optional):
   ```bash
   docker build -t patholens -f patholens/deployment/Dockerfile .
   docker run --env-file .env -p 8080:8080 patholens
   ```

For Google Cloud authentication, refer to [Application Default Credentials](https://cloud.google.com/docs/authentication/getting-started) if running outside of Docker.

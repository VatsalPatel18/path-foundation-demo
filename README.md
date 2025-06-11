# Minimal Pathology Viewer

This project provides a lightweight demo that serves a DICOM whole slide image viewer and a simple prediction API. The inference model is downloaded from Hugging Face at start up. Set the `HF_MODEL_NAME` environment variable to choose a different model; otherwise `google/path-foundation` is used.

The container exposes:

* `/` – static viewer UI.
* `/dicom/*` – proxy to a DICOMweb server defined by `DICOM_SERVER_URL`.
* `/predict` – forwards embedding requests to another prediction service defined by `PREDICT_ENDPOINT_URL`.

Build the Docker image:

```bash
docker build -t path-foundation-demo .
```

Run it with the required environment variables:

```bash
docker run -p 8080:8080 \
  -e DICOM_SERVER_URL=https://example.com/dicom \
  -e PREDICT_ENDPOINT_URL=https://predict.example.com \
  -e HF_MODEL_NAME=my/model \
  -e SERVICE_ACC_KEY='{...}' \
  path-foundation-demo
```

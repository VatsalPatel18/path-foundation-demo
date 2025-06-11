import os
import sys
import tempfile
from google.cloud import storage, firestore

# Import the main function from Trident's script, as recommended in their docs
from run_single_slide import main as run_trident_on_slide


def _update_firestore_status(slide_id: str, status: str, details: str = ""):
    """Updates the slide's processing status in Firestore."""
    try:
        db = firestore.Client()
        doc_ref = db.collection("slide_metadata").document(slide_id)
        doc_ref.set({"processing_status": status, "status_details": details, "last_updated": firestore.SERVER_TIMESTAMP}, merge=True)
        print(f"Updated Firestore status for {slide_id} to {status}")
    except Exception as e:
        print(f"Error updating Firestore for {slide_id}: {e}")


def process_wsi_with_trident(slide_id: str, input_gcs_uri: str, output_gcs_base_path: str):
    """
    Downloads a WSI, processes it with Trident using its Python API, and uploads the results.
    """
    _update_firestore_status(slide_id, "processing_started", "Downloading WSI from GCS.")

    with tempfile.TemporaryDirectory() as tmpdir:
        local_wsi_dir = os.path.join(tmpdir, "wsi_input")
        local_output_dir = os.path.join(tmpdir, "trident_output")
        os.makedirs(local_wsi_dir, exist_ok=True)
        os.makedirs(local_output_dir, exist_ok=True)

        try:
            # 1. Download WSI from GCS
            storage_client = storage.Client()
            bucket_name, blob_name = input_gcs_uri.replace("gs://", "").split("/", 1)
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            local_slide_path = os.path.join(local_wsi_dir, os.path.basename(blob_name))
            blob.download_to_filename(local_slide_path)
            print(f"Successfully downloaded {input_gcs_uri} to {local_slide_path}")

            # 2. Run Trident for segmentation and coordinate generation via its Python API
            _update_firestore_status(slide_id, "running_trident", "Segmentation and coordinate generation in progress.")
            job_dir = os.path.join(local_output_dir, slide_id)

            # Construct the arguments for Trident's main function as if they were command-line args
            sys.argv = [
                "run_single_slide.py",
                "--slide_path", local_slide_path,
                "--job_dir", job_dir,
                "--task", "seg", "coords",
                "--segmenter", "hest",
                "--mag", "20",
                "--patch_size", "256",
            ]
            run_trident_on_slide()  # Call the imported main function
            print(f"Trident processing complete for {slide_id}")

            # 3. Upload results back to GCS
            _update_firestore_status(slide_id, "uploading_results", "Uploading Trident outputs to GCS.")
            output_bucket_name = output_gcs_base_path.replace("gs://", "").split("/")[0]
            output_bucket = storage_client.bucket(output_bucket_name)
            trident_results_path = f"{output_gcs_base_path.split('/', 3)[-1]}/{slide_id}"

            for root, _, files in os.walk(job_dir):
                for file in files:
                    local_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(local_file_path, job_dir)
                    output_blob_name = os.path.join(trident_results_path, relative_path)
                    output_blob = output_bucket.blob(output_blob_name)
                    output_blob.upload_from_filename(local_file_path)
            print(f"Successfully uploaded results for {slide_id} to gs://{output_bucket_name}/{trident_results_path}")

            # 4. Update final status in Firestore, including the path to the results
            db = firestore.Client()
            doc_ref = db.collection("slide_metadata").document(slide_id)
            doc_ref.set({
                "trident_output_path": f"gs://{output_bucket_name}/{trident_results_path}",
                "processing_status": "complete",
                "status_details": "Trident processing finished successfully.",
                "last_updated": firestore.SERVER_TIMESTAMP,
            }, merge=True)

        except Exception as e:
            print(f"An error occurred during processing for {slide_id}: {e}")
            _update_firestore_status(slide_id, "failed", str(e))

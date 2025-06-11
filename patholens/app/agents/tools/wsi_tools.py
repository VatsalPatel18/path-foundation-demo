import io
import openslide
from PIL import Image
from google.cloud import storage
from google.adk.tools import FunctionTool, ToolContext
from google.adk import types

# This is a placeholder. In a real app, the GCS client would be initialized
# once and passed via context or a dependency injection system.
storage_client = None

def _initialize_client():
    """Lazy initializer for the GCS client."""
    global storage_client
    if storage_client is None:
        try:
            storage_client = storage.Client()
        except Exception as e:
            print(f"Could not initialize GCS client: {e}")
            storage_client = "Dummy"
    return storage_client

def load_wsi_tile(slide_gcs_uri: str, x: int, y: int, width: int, height: int, level: int) -> Image.Image:
    """
    Fetches a specific tile/region from a WSI stored in GCS.
    """
    client = _initialize_client()
    if not isinstance(client, storage.Client):
        raise ConnectionError("GCS client is not available.")

    bucket_name, blob_name = slide_gcs_uri.replace("gs://", "").split("/", 1)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    with io.BytesIO(blob.download_as_bytes()) as slide_bytes:
        slide = openslide.OpenSlide(slide_bytes)
        tile = slide.read_region((x, y), level, (width, height))
        # Return as RGBA and then convert to RGB for consistency, as some formats have alpha channels
        return tile.convert("RGB")

def capture_snapshot(slide_id: str, x: int, y: int, width: int, height: int, level: int, tool_context: ToolContext) -> str:
    """
    Captures the current viewport or a specified ROI as an image,
    saves it to the GCS Artifact Service, and returns its GCS URI.
    """
    # Assume slide_id can be resolved to a full GCS path.
    # This logic will be improved later (e.g., fetching from a Firestore database).
    slide_gcs_uri = f"gs://{tool_context.app_config.get('WSI_BUCKET')}/originals_for_viewer/{slide_id}"

    try:
        image = load_wsi_tile(slide_gcs_uri, x, y, width, height, level)
        
        # Convert PIL Image to bytes to save as an artifact
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        # Use the ADK's artifact service to save the file
        filename = f"snapshot_{slide_id}_L{level}_{x}_{y}.png"
        part = types.Part.from_blob(image_bytes, "image/png")
        
        tool_context.save_artifact(filename, part)
        
        # Construct and return the GCS URI of the saved artifact
        # The exact path is managed by the GcsArtifactService
        artifact_uri = f"gs://{tool_context.artifact_service.bucket_name}/{tool_context.artifact_service.get_artifact_path(tool_context, filename)}"
        return f"Successfully saved snapshot to {artifact_uri}"

    except Exception as e:
        return f"Error capturing snapshot: {e}"

capture_snapshot_tool = FunctionTool.from_function(capture_snapshot)

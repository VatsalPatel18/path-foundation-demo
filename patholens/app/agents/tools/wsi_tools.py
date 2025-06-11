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


def generate_global_wsi_summary(slide_id: str, tool_context: ToolContext) -> str:
    """
    Orchestrates generating a global summary for a WSI. It does this by
    creating a composite image of several representative tiles and sending
    that to the MedGemma invocation tool.
    """
    slide_gcs_uri = f"gs://{tool_context.app_config.get('WSI_BUCKET')}/originals_for_viewer/{slide_id}"

    try:
        # For this example, we'll create a 2x2 grid of tiles from a low-power level.
        # A real implementation could use more sophisticated sampling.
        client = _initialize_client()
        if not isinstance(client, storage.Client):
            raise ConnectionError("GCS client is not available.")

        bucket_name, blob_name = slide_gcs_uri.replace("gs://", "").split("/", 1)
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        with io.BytesIO(blob.download_as_bytes()) as slide_bytes:
            slide = openslide.OpenSlide(slide_bytes)

            # Use a lower power level for the overview, e.g., level 2
            level = 2
            if level >= slide.level_count:
                level = slide.level_count - 1

            level_dims = slide.level_dimensions[level]

            # Create a 2x2 grid of tiles from the four quadrants of the slide at this level
            tile_w, tile_h = 256, 256
            coords = [
                (0, 0), (level_dims[0] // 2, 0),
                (0, level_dims[1] // 2), (level_dims[0] // 2, level_dims[1] // 2)
            ]

            tiles = [slide.read_region(coord, level, (tile_w, tile_h)).convert("RGB") for coord in coords]

        # Stitch tiles into a single composite image
        composite_image = Image.new('RGB', (tile_w * 2, tile_h * 2))
        composite_image.paste(tiles[0], (0, 0))
        composite_image.paste(tiles[1], (tile_w, 0))
        composite_image.paste(tiles[2], (0, tile_h))
        composite_image.paste(tiles[3], (tile_w, tile_h))

        # Save the composite image as a new artifact
        img_byte_arr = io.BytesIO()
        composite_image.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()

        filename = f"global_summary_composite_{slide_id}.png"
        part = types.Part.from_blob(image_bytes, "image/png")
        tool_context.save_artifact(filename, part)

        # Get the GCS URI of the newly created composite image
        composite_artifact_uri = f"gs://{tool_context.artifact_service.bucket_name}/{tool_context.artifact_service.get_artifact_path(tool_context, filename)}"

        # Call the MedGemma tool with this composite image
        from .medgemma_tools import invoke_medgemma
        return invoke_medgemma(composite_artifact_uri, "global_summary", tool_context)

    except Exception as e:
        return f"Error generating global summary for slide {slide_id}: {e}"

generate_global_wsi_summary_tool = FunctionTool.from_function(generate_global_wsi_summary)

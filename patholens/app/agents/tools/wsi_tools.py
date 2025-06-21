import io
import openslide
from PIL import Image
from google.cloud import storage
from google.adk.tools import FunctionTool, ToolContext
from google.adk import types
from .storage_tools import get_slide_metadata

storage_client = None


def _initialize_gcs_client():
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
    """ Fetches a specific tile/region from a WSI stored in GCS. """
    client = _initialize_gcs_client()
    if not isinstance(client, storage.Client):
        raise ConnectionError("GCS client is not available.")

    bucket_name, blob_name = slide_gcs_uri.replace("gs://", "").split("/", 1)
    blob = client.bucket(bucket_name).blob(blob_name)

    with io.BytesIO(blob.download_as_bytes()) as slide_bytes:
        slide = openslide.OpenSlide(slide_bytes)
        tile = slide.read_region((x, y), level, (width, height))
        return tile.convert("RGB")


def capture_snapshot(slide_id: str, x: int, y: int, width: int, height: int, level: int, tool_context: ToolContext) -> str:
    """
    Captures a viewport/ROI, saves it to GCS Artifact Service, and returns the URI.
    """
    metadata = get_slide_metadata(slide_id)
    slide_gcs_uri = metadata.get("gcs_original_path")
    if not slide_gcs_uri:
        return f"Error: Could not find GCS path in metadata for slide {slide_id}"

    try:
        image = load_wsi_tile(slide_gcs_uri, x, y, width, height, level)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        filename = f"snapshot_{slide_id}_L{level}_{x}_{y}.png"
        part = types.Part.from_blob(img_byte_arr.getvalue(), "image/png")
        tool_context.save_artifact(filename, part)
        artifact_uri = f"gs://{tool_context.artifact_service.bucket_name}/{tool_context.artifact_service.get_artifact_path(tool_context, filename)}"
        return f"Successfully saved snapshot to {artifact_uri}"
    except Exception as e:
        return f"Error capturing snapshot: {e}"


def generate_global_wsi_summary(slide_id: str, tool_context: ToolContext) -> str:
    """
    Orchestrates generating a global summary for a WSI by creating a composite image.
    """
    metadata = get_slide_metadata(slide_id)
    slide_gcs_uri = metadata.get("gcs_original_path")
    if not slide_gcs_uri:
        return f"Error: Could not find GCS path in metadata for slide {slide_id}"

    try:
        client = _initialize_gcs_client()
        if not isinstance(client, storage.Client):
            raise ConnectionError("GCS client is not available.")

        bucket_name, blob_name = slide_gcs_uri.replace("gs://", "").split("/", 1)
        blob = client.bucket(bucket_name).blob(blob_name)

        with io.BytesIO(blob.download_as_bytes()) as slide_bytes:
            slide = openslide.OpenSlide(slide_bytes)
            level = 2
            if level >= slide.level_count:
                level = slide.level_count - 1
            level_dims = slide.level_dimensions[level]
            tile_w, tile_h = 256, 256
            coords = [
                (0, 0), (level_dims[0] // 2, 0),
                (0, level_dims[1] // 2), (level_dims[0] // 2, level_dims[1] // 2)
            ]
            tiles = [slide.read_region(coord, level, (tile_w, tile_h)).convert("RGB") for coord in coords]

        composite_image = Image.new('RGB', (tile_w * 2, tile_h * 2))
        composite_image.paste(tiles[0], (0, 0)); composite_image.paste(tiles[1], (tile_w, 0))
        composite_image.paste(tiles[2], (0, tile_h)); composite_image.paste(tiles[3], (tile_w, tile_h))
        
        img_byte_arr = io.BytesIO()
        composite_image.save(img_byte_arr, format='PNG')
        
        filename = f"global_summary_composite_{slide_id}.png"
        part = types.Part.from_blob(img_byte_arr.getvalue(), "image/png")
        tool_context.save_artifact(filename, part)
        
        composite_artifact_uri = f"gs://{tool_context.artifact_service.bucket_name}/{tool_context.artifact_service.get_artifact_path(tool_context, filename)}"

        from .medgemma_tools import invoke_medgemma
        return invoke_medgemma(composite_artifact_uri, "global_summary", tool_context)
    except Exception as e:
        return f"Error generating global summary for slide {slide_id}: {e}"


capture_snapshot_tool = FunctionTool.from_function(capture_snapshot)
generate_global_wsi_summary_tool = FunctionTool.from_function(generate_global_wsi_summary)

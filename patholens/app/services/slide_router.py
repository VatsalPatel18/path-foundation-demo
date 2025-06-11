import io
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response
from app.agents.tools.wsi_tools import load_wsi_tile
from app.common.models import SlideProcessingRequest
from app.trident_processing.processor import process_wsi_with_trident

router = APIRouter()

# This is a placeholder for getting app-level configuration.
# In a real app, you might use FastAPI's dependency injection for settings.
def get_wsi_bucket():
    import os
    return os.getenv("WSI_BUCKET", "your-wsi-bucket-name")


@router.get("/tiles/{slide_id}/{level}/{x}_{y}.png", tags=["WSI Tiling"])
async def get_wsi_tile(
    slide_id: str,
    level: int,
    x: int,
    y: int,
):
    """
    Serves a single tile from a Whole-Slide Image stored in GCS.
    This endpoint is designed to be used by a tile viewer like OpenSeadragon.
    """
    try:
        from app.agents.tools.storage_tools import get_slide_metadata
        # Fetch metadata from Firestore to get the GCS path
        metadata = get_slide_metadata(slide_id)
        slide_gcs_uri = metadata.get('gcs_original_path')
        if not slide_gcs_uri:
            raise HTTPException(status_code=404, detail=f"GCS path for slide {slide_id} not found in metadata.")

        tile_size = 256  # Assumed tile size

        image = load_wsi_tile(slide_gcs_uri, x, y, tile_size, tile_size, level)

        with io.BytesIO() as output:
            image.save(output, format="PNG")
            return Response(content=output.getvalue(), media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve WSI tile: {e}")


@router.post("/process", status_code=202, tags=["WSI Processing"])
async def trigger_slide_processing(
    request: SlideProcessingRequest,
    background_tasks: BackgroundTasks
):
    """
    Accepts a WSI for processing and triggers the Trident pipeline
    as a background task.
    """
    output_gcs_base_path = f"gs://{os.getenv('WSI_BUCKET')}/processed/trident_output"

    background_tasks.add_task(
        process_wsi_with_trident,
        request.slide_id,
        request.gcs_uri,
        output_gcs_base_path
    )

    return {"message": "Slide processing initiated.", "slide_id": request.slide_id}

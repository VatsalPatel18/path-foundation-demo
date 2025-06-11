import io
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from app.agents.tools.wsi_tools import load_wsi_tile

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
    wsi_bucket: str = Depends(get_wsi_bucket)
):
    """
    Serves a single tile from a Whole-Slide Image stored in GCS.
    This endpoint is designed to be used by a tile viewer like OpenSeadragon.
    """
    try:
        # Assumes tile size is known, e.g., 256x256. This could be a query param.
        tile_size = 256

        # The tile coordinate (x,y) from viewers is typically the top-left pixel of the tile.
        # We need to map this to the level 0 coordinates that openslide expects.
        # This is a simplified mapping; a real implementation would need slide-specific properties.
        # For now, we assume x and y are already the level 0 coordinates.

        slide_gcs_uri = f"gs://{wsi_bucket}/originals_for_viewer/{slide_id}"

        # We use the existing tool's utility function
        image = load_wsi_tile(slide_gcs_uri, x, y, tile_size, tile_size, level)

        with io.BytesIO() as output:
            image.save(output, format="PNG")
            return Response(content=output.getvalue(), media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve WSI tile: {e}")

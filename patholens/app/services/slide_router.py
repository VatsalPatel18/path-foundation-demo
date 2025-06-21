import io
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import Response
from app.agents.tools.wsi_tools import load_wsi_tile
from app.common.models import SlideProcessingRequest
from app.trident_processing.processor import process_wsi_with_trident
from app.agents.tools.storage_tools import get_slide_metadata
from google.cloud import firestore, storage
import openslide

router = APIRouter()

@router.get("/slides", tags=["WSI Listing"])
async def list_available_slides():
    """Lists all slides with 'complete' processing status from Firestore."""
    try:
        db = firestore.Client()
        slides_ref = db.collection("slide_metadata").where(filter=firestore.FieldFilter("processing_status", "==", "complete")).stream()
        slides = []
        for doc in slides_ref:
            slide_data = doc.to_dict()
            slides.append({
                "slide_id": doc.id,
                "filename": slide_data.get("original_filename", "N/A")
            })
        return slides
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not list slides: {e}")


@router.get("/slides/{slide_id}/metadata", tags=["WSI Listing"])
async def get_slide_properties(slide_id: str):
    """Retrieves detailed WSI properties required by a viewer."""
    try:
        metadata = get_slide_metadata(slide_id)
        gcs_uri = metadata.get('gcs_original_path')
        if not gcs_uri:
            raise HTTPException(status_code=404, detail=f"GCS path for slide {slide_id} not found in metadata.")

        storage_client = storage.Client()
        bucket_name, blob_name = gcs_uri.replace("gs://", "").split("/", 1)
        blob = storage_client.bucket(bucket_name).blob(blob_name)
        
        with io.BytesIO(blob.download_as_bytes()) as slide_bytes:
            slide = openslide.OpenSlide(slide_bytes)
            properties = {
                "level_count": slide.level_count,
                "level_dimensions": slide.level_dimensions,
                "mpp": (float(slide.properties.get('openslide.mpp-x', 0)), float(slide.properties.get('openslide.mpp-y', 0))),
            }
            return properties
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve slide properties: {e}")


@router.get("/tiles/{slide_id}/{level}/{x}_{y}.png", tags=["WSI Tiling"])
async def get_wsi_tile_endpoint(slide_id: str, level: int, x: int, y: int):
    """Serves a single tile from a Whole-Slide Image stored in GCS."""
    try:
        metadata = get_slide_metadata(slide_id)
        slide_gcs_uri = metadata.get('gcs_original_path')
        if not slide_gcs_uri:
            raise HTTPException(status_code=404, detail=f"GCS path for slide {slide_id} not found in metadata.")
        
        image = load_wsi_tile(slide_gcs_uri, x, y, 256, 256, level) # Assume 256x256 tiles
        
        with io.BytesIO() as output:
            image.save(output, format="PNG")
            return Response(content=output.getvalue(), media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not retrieve WSI tile: {e}")


@router.post("/process", status_code=202, tags=["WSI Processing"])
async def trigger_slide_processing(request: SlideProcessingRequest, background_tasks: BackgroundTasks):
    """Accepts a WSI for processing and triggers the Trident pipeline as a background task."""
    output_gcs_base_path = f"gs://{os.getenv('WSI_BUCKET')}/processed/trident_output"
    background_tasks.add_task(
        process_wsi_with_trident,
        request.slide_id,
        request.gcs_uri,
        output_gcs_base_path
    )
    return {"message": "Slide processing initiated.", "slide_id": request.slide_id}

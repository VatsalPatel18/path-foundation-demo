from google.adk.tools import FunctionTool, ToolContext
from google.cloud import firestore
from datetime import datetime, timezone
from typing import Optional

# Placeholder for Firestore client
db_client = None


def _initialize_client():
    """Lazy initializer for the Firestore client."""
    global db_client
    if db_client is None:
        try:
            db_client = firestore.Client()
        except Exception as e:
            print(f"Could not initialize Firestore client: {e}")
            db_client = "Dummy"
    return db_client


def archive_note_to_firestore(
    slide_id: str,
    roi_snapshot_gcs_uri: str,
    note_summary: str,
    user_annotations: Optional[dict],
    tool_context: ToolContext
) -> str:
    """
    Saves a detailed note for a Region of Interest (ROI) to the 'pathology_notes' collection in Firestore.
    """
    client = _initialize_client()
    if not isinstance(client, firestore.Client):
        return "Error: Firestore client is not available."

    try:
        doc_ref = client.collection("pathology_notes").document()
        doc_ref.set({
            "slide_id": slide_id,
            "roi_image_uri": roi_snapshot_gcs_uri,
            "summary_text": note_summary,
            "user_annotations": user_annotations or {},
            "user_id": tool_context.session.user_id,
            "timestamp": datetime.now(timezone.utc),
        })
        return f"Successfully archived note with ID: {doc_ref.id}"
    except Exception as e:
        return f"Error archiving note to Firestore: {e}"


def update_recent_snapshots(snapshot_gcs_uri: str, summary: str, tool_context: ToolContext) -> str:
    """
    Adds the latest snapshot URI and its summary to a rolling list in the session state. Keeps the last 5.
    """
    if "recent_snapshots" not in tool_context.state:
        tool_context.state["recent_snapshots"] = []

    # Prepend the new snapshot to the list
    tool_context.state["recent_snapshots"].insert(0, {
        "image_uri": snapshot_gcs_uri,
        "summary": summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Keep only the most recent 5 snapshots
    tool_context.state["recent_snapshots"] = tool_context.state["recent_snapshots"][:5]

    return "Successfully updated the list of recent snapshots in the session."


archive_note_tool = FunctionTool.from_function(archive_note_to_firestore)
update_recent_snapshots_tool = FunctionTool.from_function(update_recent_snapshots)

def get_slide_metadata(slide_id: str) -> dict:
    """
    Retrieves metadata for a given slide_id from the 'slide_metadata' collection in Firestore.
    This tool does not require ToolContext.
    """
    client = _initialize_client()
    if not isinstance(client, firestore.Client):
        return {"error": "Firestore client is not available."}
    
    try:
        doc_ref = client.collection("slide_metadata").document(slide_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        else:
            return {"error": f"No metadata found for slide_id: {slide_id}"}
    except Exception as e:
        return {"error": f"Error fetching slide metadata: {e}"}

get_slide_metadata_tool = FunctionTool.from_function(get_slide_metadata)

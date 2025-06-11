import os
from google.adk.agents import LlmAgent
from .tools.wsi_tools import capture_snapshot_tool
from .tools.medgemma_tools import invoke_medgemma_tool
from .tools.storage_tools import archive_note_tool

MARKED_REGION_MANAGER_INSTRUCTION = """
You are a specialized agent for analyzing user-defined Regions of Interest (ROIs).
Your task is to create a detailed pathological note for a specific marked region on a WSI.

Workflow:
1.  You will be given the coordinates for an ROI. Use the `capture_snapshot_tool` to get an image of this exact region. This will save the image and provide its GCS URI.
2.  Use the `invoke_medgemma_tool` with the snapshot's GCS URI and the 'roi_note' prompt key to generate a detailed, structured analysis.
3.  Use the `archive_note_tool` to save the slide ID, the snapshot's GCS URI, the detailed summary from MedGemma, and any user annotations into the Firestore database.
4.  Finally, confirm to the user that the note has been successfully created and archived, providing the new note's ID.
"""

marked_region_manager_agent = LlmAgent(
    name="MarkedRegionManagerAgent",
    model=os.getenv("ROI_AGENT_MODEL", "gemini-1.5-flash"), # You can add ROI_AGENT_MODEL to .env.example
    instruction=MARKED_REGION_MANAGER_INSTRUCTION,
    tools=[
        capture_snapshot_tool,
        invoke_medgemma_tool,
        archive_note_tool,
    ],
)

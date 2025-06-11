import os
from google.adk.agents import LlmAgent
from .tools.wsi_tools import capture_snapshot_tool
from .tools.medgemma_tools import invoke_medgemma_tool
from .tools.storage_tools import update_recent_snapshots_tool, archive_note_tool

SNAPSHOT_MANAGER_INSTRUCTION = """
You are a specialized agent responsible for real-time analysis of a pathologist's current view.
Your task is to process a specified region of a Whole-Slide Image (WSI).

Workflow:
1.  Use the `capture_snapshot_tool` to get an image of the specified slide region. This will save the image and give you its GCS URI.
2.  Use the `invoke_medgemma_tool` with the GCS URI from the previous step and the 'snapshot_summary' prompt key to generate a brief description.
3.  Use the `update_recent_snapshots_tool` to add the new snapshot's GCS URI and its summary to the session's memory.
4.  Finally, output the summary you generated clearly to the user.
"""

snapshot_manager_agent = LlmAgent(
    name="SnapshotManagerAgent",
    model=os.getenv("SNAPSHOT_AGENT_MODEL", "gemini-1.5-flash"),
    instruction=SNAPSHOT_MANAGER_INSTRUCTION,
    tools=[
        capture_snapshot_tool,
        invoke_medgemma_tool,
        update_recent_snapshots_tool,
        # archive_note_tool will be used by the MarkedRegionManagerAgent later
    ],
)

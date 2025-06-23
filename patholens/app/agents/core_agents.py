import os
from google.adk.agents import LlmAgent
from .snapshot_manager import snapshot_manager_agent
from .marked_region_manager import marked_region_manager_agent
from .slide_manager import slide_manager_agent
from .ui_telemetry_coordinator import ui_telemetry_coordinator_agent

ROOT_AGENT_INSTRUCTION = """
You are PathoLens, the master AI assistant for pathologists. Your primary role is to understand user requests and delegate tasks to your specialized sub-agents. You do not perform tasks yourself; you coordinate the workflow.
- For requests about a specific marked region (ROI), delegate to `MarkedRegionManagerAgent`.
- For requests to analyze the current view (a snapshot), delegate to `SnapshotManagerAgent`.
- For requests to get a summary of a whole slide, delegate to `SlideManagerAgent`.
- For structured JSON events from the UI, delegate to `UITelemetryCoordinatorAgent`.
Based on the user's message, determine which agent is best suited and transfer control.
"""

root_agent = LlmAgent(
    name="PathoLensRootAgent",
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-2.5-flash"),
    instruction=ROOT_AGENT_INSTRUCTION,
    sub_agents=[
        slide_manager_agent,
        snapshot_manager_agent,
        marked_region_manager_agent,
        ui_telemetry_coordinator_agent,
    ],
)

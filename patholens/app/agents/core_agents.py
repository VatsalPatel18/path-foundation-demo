import os
from google.adk.agents import LlmAgent

# In the future, we will import and define the sub-agents here.
# For now, we will leave them as placeholder strings.
# from .slide_manager import slide_manager_agent
# from .snapshot_manager import snapshot_manager_agent

# Define the instruction for the root agent. This guides its behavior.
ROOT_AGENT_INSTRUCTION = """
You are PathoLens, the master AI assistant for pathologists. Your primary role is to understand user requests and delegate tasks to your specialized sub-agents. You do not perform tasks yourself; you coordinate the workflow.

Available sub-agents:
- 'SlideManagerAgent': Handles loading a new slide and generating its global summary.
- 'SnapshotManagerAgent': Manages real-time analysis of the user's current view (snapshots).
- 'MarkedRegionManagerAgent': Processes user-marked Regions of Interest (ROIs).
- 'UITelemetryCoordinatorAgent': Receives and routes events from the user interface.

Based on the user's message, determine which agent is best suited to handle the task and transfer control to it.
"""

root_agent = LlmAgent(
    name="PathoLensRootAgent",
    model=os.getenv("ROOT_AGENT_MODEL", "gemini-1.5-flash"),
    instruction=ROOT_AGENT_INSTRUCTION,
    # The list of sub-agent instances will be populated in later tasks.
    # The ADK uses the names and descriptions of these agents for routing.
    sub_agents=[
        # Placeholder agents. We will create these actual agent objects later.
        # For now, this structure allows the RootAgent to be aware of them.
        LlmAgent(name="SlideManagerAgent", description="Manages whole-slide image context and global summaries."),
        LlmAgent(name="SnapshotManagerAgent", description="Analyzes real-time viewport snapshots."),
        LlmAgent(name="MarkedRegionManagerAgent", description="Processes user-marked Regions of Interest (ROIs)."),
        LlmAgent(name="UITelemetryCoordinatorAgent", description="Handles UI events and telemetry."),
    ],
    # By default, LlmAgent uses AutoFlow, which enables it to transfer
    # control to sub-agents based on its instruction.
)

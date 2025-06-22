import os
from google.adk.agents import LlmAgent
from .tools.wsi_tools import generate_global_wsi_summary_tool

SLIDE_MANAGER_INSTRUCTION = """
You are a specialized agent responsible for managing the context of a new Whole-Slide Image (WSI).
When a new slide is loaded, your primary and only task is to generate and provide a global summary for it.
To do this, call the `generate_global_wsi_summary_tool` with the slide_id.
"""

slide_manager_agent = LlmAgent(
    name="SlideManagerAgent",
    model=os.getenv("SLIDE_AGENT_MODEL", "gemini-2.5-flash"), # Add SLIDE_AGENT_MODEL to .env.example
    instruction=SLIDE_MANAGER_INSTRUCTION,
    tools=[
        generate_global_wsi_summary_tool,
    ],
)

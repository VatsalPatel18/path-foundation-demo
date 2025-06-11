import json
from google.adk.agents import BaseAgent, InvocationContext
from google.adk import types

class UITelemetryCoordinatorAgent(BaseAgent):
    """
    A non-LLM agent that receives structured UI events (from a WebSocket)
    and triggers the appropriate agent by creating a new message for the runner.
    """
    async def run_async(self, context: InvocationContext):
        # This agent expects the user message to be a JSON string with UI event data
        if not context.user_content or not context.user_content.parts:
            yield self.construct_event("No UI event data received.", is_error=True)
            return

        try:
            event_data = json.loads(context.user_content.parts[0].text)
            event_type = event_data.get("type")
            payload = event_data.get("payload", {})
        except (json.JSONDecodeError, AttributeError):
            yield self.construct_event("Invalid UI event format. Expecting JSON.", is_error=True)
            return

        # Based on the event type, construct a natural language message
        # for the RootAgent to delegate to the correct sub-agent.
        message_for_root_agent = ""
        if event_type == "roi_marked":
            # This message is crafted to trigger the MarkedRegionManagerAgent
            message_for_root_agent = (
                f"A new Region of Interest has been marked on slide '{payload.get('slide_id')}'. "
                f"Please analyze it. The ROI coordinates are x={payload.get('x')}, y={payload.get('y')}, "
                f"width={payload.get('width')}, height={payload.get('height')} at level {payload.get('level')}. "
                f"User annotations: {payload.get('annotations')}"
            )
        elif event_type == "viewport_update":
            # This message is crafted to trigger the SnapshotManagerAgent
            message_for_root_agent = (
                f"The user is viewing a new region on slide '{payload.get('slide_id')}'. "
                f"Please generate a snapshot summary for the area at x={payload.get('x')}, y={payload.get('y')}, "
                f"width={payload.get('width')}, height={payload.get('height')} at level {payload.get('level')}."
            )
        elif event_type == "slide_loaded":
             # This message is crafted to trigger the SlideManagerAgent
             message_for_root_agent = f"A new slide with ID '{payload.get('slide_id')}' has been loaded. Please generate a global summary."
        else:
            yield self.construct_event(f"Unknown UI event type: '{event_type}'", is_error=True)
            return

        # Yield a new message content. The ADK runner will pick this up
        # and re-run the RootAgent with this new instruction.
        yield self.construct_event(message_for_root_agent, is_message=True)

ui_telemetry_coordinator_agent = UITelemetryCoordinatorAgent(
    name="UITelemetryCoordinatorAgent",
    description="Receives and routes events from the user interface."
)

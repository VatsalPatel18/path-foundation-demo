import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import GcsArtifactService, InMemoryArtifactService
from google.adk.memory import InMemoryMemoryService

# Import the root agent we defined
from app.agents.core_agents import root_agent

# Load environment variables from a .env file
load_dotenv()

# --- ADK Runner and Services Configuration ---

# For development, we use in-memory services.
# For production, you would switch to persistent services like FirestoreSessionService.
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# Artifacts (e.g., generated images, files) can be stored in GCS.
# Check for a GCS_BUCKET environment variable. If not set, use an in-memory service for local dev.
gcs_bucket = os.getenv("GCS_ARTIFACT_BUCKET")
if gcs_bucket:
    artifact_service = GcsArtifactService(bucket_name=gcs_bucket)
else:
    print("WARNING: GCS_ARTIFACT_BUCKET not set. Using InMemoryArtifactService.")
    artifact_service = InMemoryArtifactService()

# Initialize the main ADK Runner
runner = Runner(
    app_name="patholens",
    agent=root_agent,
    session_service=session_service,
    artifact_service=artifact_service,
    memory_service=memory_service,
)


# --- FastAPI Application Setup ---

app = FastAPI(
    title="PathoLens AI Service",
    version="0.1.0",
    description="Backend service for PathoLens, integrating ADK agents for pathology analysis."
)

# Store the runner in the app's state so it can be accessed in endpoints
app.state.runner = runner

# Configure CORS (Cross-Origin Resource Sharing)
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Health Check"])
async def root():
    """Root endpoint for health check."""
    return {"message": "Welcome to the PathoLens AI Service. The API is running."}

# The agent interaction endpoint will be added in the next task.

# --- Agent Interaction Endpoint ---

from fastapi import Request
from fastapi.responses import StreamingResponse
from google.adk import types
from google.adk.agents import RunConfig
import json

# Import the Pydantic model for the request body
from app.common.models import AgentRunRequest


async def event_stream_generator(request_data: AgentRunRequest, adk_runner: Runner):
    """
    Asynchronous generator that runs the agent and yields events as JSON strings.
    """
    run_config = RunConfig(**request_data.run_config) if request_data.run_config else RunConfig()
    
    # Create the initial message content for the ADK
    new_message = types.Content(parts=[types.Part.from_text(request_data.message)])

    try:
        # Asynchronously iterate through the events from the runner
        async for event in adk_runner.run_async(
            user_id=request_data.user_id,
            session_id=request_data.session_id,
            new_message=new_message,
            run_config=run_config
        ):
            # Yield each event as a server-sent event (SSE) formatted string
            yield f"data: {json.dumps(event.to_dict())}\n\n"
            
    except Exception as e:
        # Handle exceptions during agent execution
        error_event = {
            "author": "system_error",
            "content": {"parts": [{"text": f"An error occurred: {str(e)}"}]},
            "type": "ERROR"
        }
        yield f"data: {json.dumps(error_event)}\n\n"


@app.post("/agent/run", tags=["AI Agents"])
async def run_agent(agent_request: AgentRunRequest, request: Request):
    """
    Receives a user message and runs it through the ADK agent.
    
    This endpoint streams the agent's events back to the client.
    """
    adk_runner = request.app.state.runner
    return StreamingResponse(
        event_stream_generator(agent_request, adk_runner),
        media_type="text/event-stream"
    )

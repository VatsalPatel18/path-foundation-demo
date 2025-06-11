from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class AgentRunRequest(BaseModel):
    """
    Defines the request body for interacting with the main agent runner.
    """
    user_id: str = Field(
        ..., 
        example="user123", 
        description="A unique identifier for the user."
    )
    session_id: str = Field(
        ..., 
        example="session_abc", 
        description="A unique identifier for the conversation session."
    )
    message: str = Field(
        ..., 
        example="Hello, PathoLens!", 
        description="The user's text message to the agent."
    )
    run_config: Optional[Dict[str, Any]] = Field(
        default=None, 
        example={"streaming_mode": "SSE"}, 
        description="Optional ADK RunConfig parameters."
    )


class SlideProcessingRequest(BaseModel):
    """Defines the request to process a new WSI."""
    slide_id: str = Field(..., example="TCGA-AA-3554-01A-01-TS1")
    gcs_uri: str = Field(..., example="gs://your-wsi-bucket-name/raw/TCGA-AA-3554-01A-01-TS1.svs")

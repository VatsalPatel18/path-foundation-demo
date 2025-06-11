from google.adk.tools import FunctionTool, ToolContext
from app.common.medgemma_client import MedGemmaClient
from app.agents.prompts import medgemma_prompts
from typing import Literal

# This is a placeholder. In a real app, the client would be initialized
# once and passed via context or a dependency injection system.
# For now, we'll initialize it with placeholder values for structure.
# In a later step, we'll get these values from environment variables.
medgemma_client_instance = None # To be initialized later


def _initialize_client():
    """Lazy initializer for the client."""
    global medgemma_client_instance
    if medgemma_client_instance is None:
        try:
            from dotenv import load_dotenv
            import os
            load_dotenv()
            medgemma_client_instance = MedGemmaClient(
                project_id=os.getenv("GCP_PROJECT_ID", "placeholder"),
                region=os.getenv("GCP_REGION", "placeholder"),
                endpoint_id=os.getenv("MEDGEMMA_ENDPOINT_ID", "placeholder")
            )
        except (ValueError, ImportError) as e:
            print(f"Could not initialize MedGemmaClient: {e}")
            medgemma_client_instance = "Dummy" # Avoid re-initialization failure
    return medgemma_client_instance

PROMPT_MAPPING = {
    "global_summary": (medgemma_prompts.SYSTEM_INSTRUCTION_EXPERT_PATHOLOGIST, medgemma_prompts.PROMPT_GLOBAL_SUMMARY),
    "snapshot_summary": (medgemma_prompts.SYSTEM_INSTRUCTION_CONCISE_OBSERVER, medgemma_prompts.PROMPT_SNAPSHOT_SUMMARY),
    "roi_note": (medgemma_prompts.SYSTEM_INSTRUCTION_NOTE_TAKER, medgemma_prompts.PROMPT_ROI_NOTE),
}

PromptKey = Literal["global_summary", "snapshot_summary", "roi_note"]


def invoke_medgemma(image_gcs_uri: str, prompt_key: PromptKey, tool_context: ToolContext) -> str:
    """
    Sends an image (by GCS URI) and a selected prompt to the MedGemma Vertex AI endpoint for summarization.
    """
    client = _initialize_client()
    if not isinstance(client, MedGemmaClient):
        return "Error: MedGemma client is not available or failed to initialize."

    if prompt_key not in PROMPT_MAPPING:
        return f"Error: Invalid prompt key '{prompt_key}'. Valid keys are: {list(PROMPT_MAPPING.keys())}"

    system_instruction, prompt = PROMPT_MAPPING[prompt_key]
    
    summary = client.generate_summary(
        image_uri=image_gcs_uri,
        prompt=prompt,
        system_instruction=system_instruction
    )
    return summary


invoke_medgemma_tool = FunctionTool.from_function(invoke_medgemma)

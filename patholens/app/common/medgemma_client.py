import os
from google.cloud import aiplatform

class MedGemmaClient:
    """A wrapper for interacting with a deployed MedGemma endpoint on Vertex AI."""

    def __init__(self, project_id: str, region: str, endpoint_id: str):
        """
        Initializes the MedGemma client.

        Args:
            project_id: The Google Cloud project ID.
            region: The region where the Vertex AI endpoint is deployed.
            endpoint_id: The ID of the Vertex AI endpoint.
        """
        if not all([project_id, region, endpoint_id]):
            raise ValueError("Project ID, region, and endpoint ID must be provided.")
        
        aiplatform.init(project=project_id, location=region)
        self.endpoint = aiplatform.Endpoint(endpoint_name=endpoint_id)
        print(f"MedGemmaClient initialized for endpoint: {self.endpoint.resource_name}")

    def generate_summary(
        self,
        image_uri: str,
        prompt: str,
        system_instruction: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> str:
        """
        Generates a summary for a given image using the MedGemma model.

        Args:
            image_uri: GCS URI of the image to analyze (e.g., "gs://bucket/image.png").
            prompt: The user-facing prompt for the model.
            system_instruction: The system-level instruction to guide the model's persona.
            max_tokens: The maximum number of tokens to generate.
            temperature: The sampling temperature for the generation.

        Returns:
            The generated text summary from the model.
        """
        full_prompt = f"{system_instruction} {prompt}"
        
        instances = [{
            "prompt": full_prompt,
            "multi_modal_data": {"image": image_uri},
            "max_tokens": max_tokens,
            "temperature": temperature,
            "raw_response": True,
        }]

        try:
            response = self.endpoint.predict(instances=instances)
            prediction = response.predictions[0] if response.predictions else ""
            return prediction
        except Exception as e:
            print(f"Error calling MedGemma endpoint: {e}")
            return f"Error: Could not get a response from the model. Details: {e}"

# Example of how this might be instantiated in main.py later
# medgemma_client = MedGemmaClient(
#     project_id=os.getenv("GCP_PROJECT_ID"),
#     region=os.getenv("GCP_REGION"),
#     endpoint_id=os.getenv("MEDGEMMA_ENDPOINT_ID")
# )

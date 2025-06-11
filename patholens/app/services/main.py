import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Initialize the FastAPI application
app = FastAPI(
    title="PathoLens AI Service",
    version="0.1.0",
    description="Backend service for PathoLens, integrating ADK agents for pathology analysis."
)

# Configure CORS (Cross-Origin Resource Sharing)
# This allows the frontend UI (on a different domain/port) to communicate with the backend.
origins = [
    "http://localhost",
    "http://localhost:8080", # Default for local dev servers
    "http://localhost:5173", # Default for Vue/Vite dev server
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
    """
    Root endpoint for health check.
    """
    return {"message": "Welcome to the PathoLens AI Service. The API is running."}

# In future steps, we will add more routers and the ADK runner here.
# For example:
# from patholens.app.agents import agent_router
# app.include_router(agent_router, prefix="/agent", tags=["AI Agents"])


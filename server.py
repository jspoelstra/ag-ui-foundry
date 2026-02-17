"""
AG-UI Server for an existing Microsoft Foundry Agent (Azure AI Projects 2.x)

Prerequisites:
- pip install -r requirements.txt
- Have your Foundry project endpoint (from portal: https://<....>.services.ai.azure.com/api/projects/<project-name>)
- Logged in via Azure CLI (az login) or set AZURE_SUBSCRIPTION_ID etc. for DefaultAzureCredential
- Replace the placeholders below

This script loads an EXISTING agent by name (latest version) and serves it via AG-UI.
"""

import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from azure.identity import DefaultAzureCredential  # or AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

# ── Microsoft Agent Framework imports ───────────────────────────────────────
from agent_framework.azure import AzureAIProjectAgentProvider
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint

load_dotenv()  # Optional: loads from .env file

# ── Configuration ────────────────────────────────────────────────────────────
# Get these from the Azure AI Foundry portal (ai.azure.com → your project)
PROJECT_ENDPOINT = os.getenv(
    "AZURE_AI_PROJECT_ENDPOINT",
    "https://your-project-name.services.ai.azure.com/api/projects/your-project-name"
)  # ← Replace or set in .env

AGENT_NAME = os.getenv("AZURE_AI_PROJECT_AGENT_NAME",
                       "AgentSmith"
)  # ← Exact name from Foundry portal (case-sensitive)
# AGENT_VERSION = os.getenv("AZURE_AI_PROJECT_AGENT_VERSION", "1.0")  # Optional: uncomment if targeting specific version

# CORS: adjust for production (e.g. your frontend domain)
ALLOWED_ORIGINS = ["*"]  # For dev; tighten this in prod!

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="AG-UI Server - Foundry Agent",
    description="Exposes an existing Azure AI Foundry agent via AG-UI protocol",
    version="0.1.0"
)

# Enable CORS so frontend (e.g. CopilotKit, custom React) can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variable for the agent (loaded once at startup)
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the Foundry agent once when the server starts"""
    global agent

    credential = DefaultAzureCredential()

    async with AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential
    ) as project_client:

        async with AzureAIProjectAgentProvider(project_client=project_client) as provider:
            print(f"Loading agent '{AGENT_NAME}' from Foundry project...")

            # Load existing agent (defaults to latest published version)
            agent = await provider.get_agent(name=AGENT_NAME)

            # If you need a specific version (uncommon for published agents):
            # agent = await provider.get_agent(name=AGENT_NAME, version=AGENT_VERSION)

            if agent is None:
                raise RuntimeError(f"Agent '{AGENT_NAME}' not found in the project.")

            print(f"Agent loaded successfully: {agent.name} (version: {getattr(agent, 'version', 'latest')})")

            # Optional: wrap if your use-case needs extra behavior (usually not required for AG-UI)
            # from agent_framework import AgentFrameworkAgent
            # agent = AgentFrameworkAgent(agent)  # or ChatAgent(chat_client=..., agent=agent)

    yield  # Server runs here

    print("Shutting down AG-UI server...")


app.router.lifespan_context = lifespan


# ── Register the AG-UI endpoint ─────────────────────────────────────────────
# This single call exposes your agent at /ag-ui (or change path to "/")
add_agent_framework_fastapi_endpoint(
    app,
    agent=agent,           # Will be available after lifespan runs
    path="/ag-ui",         # Common path; some examples use "/" or "/chat"
    # state_schema=...,    # Optional: if using shared/persistent state
    # allow_origins=...,   # Already handled via middleware
)


# Optional root endpoint for health check
@app.get("/")
async def root():
    return {
        "status": "running",
        "message": f"AG-UI endpoint available at /ag-ui",
        "agent_name": AGENT_NAME,
    }


if __name__ == "__main__":
    import uvicorn

    # Run with: python this_file.py
    # Or:     uvicorn this_file:app --reload --port 8000
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,           # dev only
        log_level="info"
    )
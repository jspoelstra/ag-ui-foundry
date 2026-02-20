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
from collections.abc import AsyncGenerator
from typing import Any
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from azure.identity import DefaultAzureCredential  # or AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

# ── Microsoft Agent Framework imports ───────────────────────────────────────
from agent_framework import tool
from agent_framework.ag_ui import AgentFrameworkAgent
from agent_framework.azure import AzureAIProjectAgentProvider
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from pydantic import BaseModel, Field

load_dotenv()  # Optional: loads from .env file


class Location(BaseModel):
    """Project location details."""

    country: str = Field(..., description="Country name")
    district: str = Field(..., description="District or region")
    lat: float = Field(..., description="Latitude")
    long: float = Field(..., description="Longitude")


class Component(BaseModel):
    """A project component with environmental impact."""

    type: str = Field(..., description="Component type")
    description: str = Field(..., description="Component description")
    environment_impact: str = Field(..., description="Environmental impact")


class Project(BaseModel):
    """A complete project."""

    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    location: Location = Field(..., description="Project location")
    components: list[Component] = Field(..., description="Project components")


@tool
def update_info(project: Project) -> str:
    """Update the project object with new or modified content.

    You MUST write the complete project with ALL fields, even when changing only a few items.
    When modifying an existing project, include ALL existing components plus your changes.
    NEVER delete existing data - only add or modify.

    Args:
        project: The complete project object with all details.

    Returns:
        Confirmation that the project was updated.
    """
    return "Project information updated."


@tool
def update_title(name: str) -> str:
    """Update the project title.

    Args:
        name: The updated project name.

    Returns:
        Confirmation that the title was updated.
    """
    return "Project title updated."


@tool
def update_description(description: str) -> str:
    """Update the project description.

    Args:
        description: The updated project description.

    Returns:
        Confirmation that the description was updated.
    """
    return "Project description updated."


@tool
def update_location(location: Location) -> str:
    """Update the project location.

    Args:
        location: The updated project location details.

    Returns:
        Confirmation that the location was updated.
    """
    return "Project location updated."


@tool
def add_component(components: list[Component]) -> str:
    """Update project components after adding or editing an item.

    You MUST provide the complete components list, including all existing items,
    plus any newly added or modified component.

    Args:
        components: The complete, updated components list.

    Returns:
        Confirmation that components were updated.
    """
    return "Project components updated."

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


def _get_event_field(event: Any, field_name: str) -> Any:
    if isinstance(event, dict):
        return event.get(field_name)
    return getattr(event, field_name, None)


def _get_event_type(event: Any) -> str | None:
    event_type = _get_event_field(event, "type")

    if not isinstance(event_type, str):
        return None

    normalized_type = event_type.strip().upper().replace("-", "_")
    return normalized_type or None


def _get_tool_call_id(event: Any) -> str | None:
    direct_candidates = (
        _get_event_field(event, "toolCallId"),
        _get_event_field(event, "tool_call_id"),
        _get_event_field(event, "toolCallID"),
        _get_event_field(event, "id"),
    )

    for candidate in direct_candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    nested_tool_call = _get_event_field(event, "toolCall")
    if nested_tool_call is None:
        nested_tool_call = _get_event_field(event, "tool_call")

    if nested_tool_call is not None:
        nested_candidates = (
            _get_event_field(nested_tool_call, "toolCallId"),
            _get_event_field(nested_tool_call, "tool_call_id"),
            _get_event_field(nested_tool_call, "id"),
        )

        for candidate in nested_candidates:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

    return None


class AgentProxy:
    """Proxy that delegates run_agent calls to the loaded agent."""

    async def run_agent(self, input_data: dict[str, Any]) -> AsyncGenerator[Any, None]:
        if agent is None:
            raise RuntimeError("Agent is not initialized. Ensure startup completed.")

        active_tool_calls: set[str] = set()
        tool_start_events = {"TOOL_CALL_START", "TOOL_START"}
        tool_lifecycle_events = {
            "TOOL_CALL_ARGS",
            "TOOL_CALL_END",
            "TOOL_CALL_RESULT",
            "TOOL_ARGS",
            "TOOL_END",
            "TOOL_RESULT",
        }

        async for event in agent.run_agent(input_data):
        # Note: The event filtering logic below is a best-effort approach to handle tool call events.
        # It tracks active tool calls by their IDs and filters out lifecycle events that don't match any active tool call.
        #     event_type = _get_event_type(event)
        #     tool_call_id = _get_tool_call_id(event)

        #     if event_type in tool_start_events and tool_call_id:
        #         active_tool_calls.add(tool_call_id)
        #     elif event_type in tool_lifecycle_events:
        #         if not tool_call_id or tool_call_id not in active_tool_calls:
        #             continue
        #         if event_type in {"TOOL_CALL_END", "TOOL_CALL_RESULT", "TOOL_END", "TOOL_RESULT"}:
        #             active_tool_calls.discard(tool_call_id)

            yield event


agent_proxy = AgentProxy()

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
            raw_agent = await provider.get_agent(
                name=AGENT_NAME,
                tools=[
                    update_info,
                    update_title,
                    update_description,
                    update_location,
                    add_component,
                ],
            )

            # If you need a specific version (uncommon for published agents):
            # raw_agent = await provider.get_agent(name=AGENT_NAME, version=AGENT_VERSION)

            if raw_agent is None:
                raise RuntimeError(f"Agent '{AGENT_NAME}' not found in the project.")

            print(f"Agent loaded successfully: {raw_agent.name} (version: {getattr(raw_agent, 'version', 'latest')})")

            agent = AgentFrameworkAgent(
                agent=raw_agent,
                name="librarian",
                description="Project agent",
                state_schema={
                    "name": {"type": "string", "description": "The current project name"},
                    "description": {"type": "string", "description": "The current project description"},
                    "location": {"type": "object", "description": "The current project location"},
                    "components": {"type": "array", "description": "The current project components"},
                },
                predict_state_config={
                    "name": {"tool": "update_title", "tool_argument": "name"},
                    "description": {"tool": "update_description", "tool_argument": "description"},
                    "location": {"tool": "update_location", "tool_argument": "location"},
                    "components": {"tool": "add_component", "tool_argument": "components"},
                },
                require_confirmation=False,
            )

    yield  # Server runs here

    print("Shutting down AG-UI server...")


app.router.lifespan_context = lifespan


# ── Register the AG-UI endpoint ─────────────────────────────────────────────
# This single call exposes your agent at /ag-ui (or change path to "/")
add_agent_framework_fastapi_endpoint(
    app,
    agent=agent_proxy,
    path="/ag-ui",         # Common path; some examples use "/" or "/chat"
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
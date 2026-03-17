# Copyright (c) Microsoft. All rights reserved.

"""Foundry-backed agent loader for AG-UI."""

from __future__ import annotations

import asyncio
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient

from agent_framework.ag_ui import AgentFrameworkAgent
from agent_framework.azure import AzureAIProjectAgentProvider

from backend.state import update_title, update_description, update_location, add_component


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


async def _load_foundry_agent() -> AgentFrameworkAgent:
    endpoint = _get_required_env("AZURE_AI_PROJECT_ENDPOINT")
    agent_name = _get_required_env("AZURE_AI_PROJECT_AGENT_NAME")
    agent_version = os.getenv("AZURE_AI_PROJECT_AGENT_VERSION", "").strip() or None

    credential = DefaultAzureCredential()

    async with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
        async with AzureAIProjectAgentProvider(project_client=project_client) as provider:
            if agent_version:
                raw_agent = await provider.get_agent(
                    name=agent_name,
                    version=agent_version,
                    tools=[
                        update_title,
                        update_description,
                        update_location,
                        add_component,
                    ],
                )
            else:
                raw_agent = await provider.get_agent(
                    name=agent_name,
                    tools=[
                        update_title,
                        update_description,
                        update_location,
                        add_component,
                    ],
                )

            if raw_agent is None:
                raise RuntimeError(f"Agent '{agent_name}' not found in the project.")

            return AgentFrameworkAgent(
                agent=raw_agent,
                name="foundry_agent",
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


def foundry_agent() -> AgentFrameworkAgent:
    return asyncio.run(_load_foundry_agent())

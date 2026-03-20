# Copyright (c) Microsoft. All rights reserved.

"""Foundry-backed agent loader for AG-UI."""

from __future__ import annotations

import asyncio
import os

from agent_framework import Agent, FunctionTool
from azure.identity import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

from agent_framework.ag_ui import AgentFrameworkAgent
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework_azure_ai._shared import from_azure_ai_tools

from backend.state import update_title, update_description, update_location, add_component


_SHARED_STATE_TOOLS = [
    update_title,
    update_description,
    update_location,
    add_component,
]

_STATE_SCHEMA = {
    "name": {"type": "string", "description": "The current project name"},
    "description": {"type": "string", "description": "The current project description"},
    "location": {"type": "object", "description": "The current project location"},
    "components": {"type": "array", "description": "The current project components"},
}

_PREDICT_STATE_CONFIG = {
    "name": {"tool": "update_title", "tool_argument": "name"},
    "description": {"tool": "update_description", "tool_argument": "description"},
    "location": {"tool": "update_location", "tool_argument": "location"},
    "components": {"tool": "add_component", "tool_argument": "components"},
}


def _resolve_foundry_model_deployment(definition: PromptAgentDefinition) -> str:
    deployment_name = (
        (definition.model or "").strip()
        or os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME", "").strip()
        or os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME", "").strip()
    )
    if not deployment_name:
        raise RuntimeError(
            "Missing model deployment for Foundry mode. Configure the prompt agent model in Foundry "
            "or set AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME."
        )
    return deployment_name


def _merge_foundry_tools(definition: PromptAgentDefinition) -> list[object]:
    shared_tool_names = {
        tool.name
        for tool in _SHARED_STATE_TOOLS
        if isinstance(tool, FunctionTool)
    }
    missing_function_tools = [
        tool.name
        for tool in (definition.tools or [])
        if getattr(tool, "type", None) == "function" and getattr(tool, "name", None) not in shared_tool_names
    ]
    if missing_function_tools:
        missing_names = ", ".join(sorted(missing_function_tools))
        raise RuntimeError(
            "Foundry agent requires function tool implementations that are not available locally: "
            f"{missing_names}"
        )

    hosted_tools = []
    for hosted_tool in from_azure_ai_tools(definition.tools):
        if isinstance(hosted_tool, dict) and hosted_tool.get("type") == "function":
            continue
        hosted_tools.append(hosted_tool)

    return [*hosted_tools, *_SHARED_STATE_TOOLS]


async def _get_prompt_agent_definition(
    project_client: AIProjectClient,
    agent_name: str,
    agent_version: str | None,
) -> tuple[str, str | None, PromptAgentDefinition]:
    if agent_version:
        details = await project_client.agents.get_version(agent_name=agent_name, agent_version=agent_version)
    else:
        agent = await project_client.agents.get(agent_name=agent_name)
        latest_version = getattr(getattr(agent, "versions", None), "latest", None)
        if latest_version is None:
            raise RuntimeError(f"Agent '{agent_name}' was found, but it has no latest version.")
        details = latest_version

    definition = getattr(details, "definition", None)
    if not isinstance(definition, PromptAgentDefinition):
        raise RuntimeError(
            f"Agent '{agent_name}' must use a PromptAgentDefinition, got {type(definition).__name__}."
        )

    return details.name, details.description, definition


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
        resolved_name, resolved_description, definition = await _get_prompt_agent_definition(
            project_client=project_client,
            agent_name=agent_name,
            agent_version=agent_version,
        )

    deployment_name = _resolve_foundry_model_deployment(definition)
    client = AzureOpenAIResponsesClient(
        project_endpoint=endpoint,
        deployment_name=deployment_name,
        credential=credential,
    )
    raw_agent = Agent(
        name=resolved_name,
        description=resolved_description,
        instructions=definition.instructions,
        client=client,
        model_id=deployment_name,
        tools=_merge_foundry_tools(definition),
    )

    return AgentFrameworkAgent(
        agent=raw_agent,
        name="foundry_agent",
        description=resolved_description or "Project agent",
        state_schema=_STATE_SCHEMA,
        predict_state_config=_PREDICT_STATE_CONFIG,
        require_confirmation=False,
    )


def foundry_agent() -> AgentFrameworkAgent:
    return asyncio.run(_load_foundry_agent())

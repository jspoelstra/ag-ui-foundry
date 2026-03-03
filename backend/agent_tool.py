# Copyright (c) Microsoft. All rights reserved.

"""Foundry agent tool helpers."""

from __future__ import annotations

import asyncio
import os

from agent_framework import FunctionTool, tool
from agent_framework.azure import AzureAIProjectAgentProvider
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential


def _get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

_CACHED_TOOL: FunctionTool | None = None

def _get_optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


async def _create_foundry_qa_tool() -> FunctionTool:
    endpoint = _get_required_env("AZURE_AI_PROJECT_ENDPOINT")
    agent_name = _get_required_env("AZURE_AI_PROJECT_AGENT_NAME")
    agent_version = os.getenv("AZURE_AI_PROJECT_AGENT_VERSION", "").strip() or None
    description_override = _get_optional_env("AZURE_AI_PROJECT_AGENT_DESCRIPTION")

    credential = DefaultAzureCredential()
    project_client = AIProjectClient(endpoint=endpoint, credential=credential)
    provider = AzureAIProjectAgentProvider(project_client=project_client)

    if agent_version:
        agent = await provider.get_agent(name=agent_name, version=agent_version)
    else:
        agent = await provider.get_agent(name=agent_name)

    if agent is None:
        await credential.close()
        await project_client.close()
        raise RuntimeError(f"Agent '{agent_name}' not found in the project.")

    description = (
        description_override
        or "Ask the Foundry agent a question and return its response."
    )

    async def ask_agent(question: str) -> str:
        response = await agent.run(messages=question, stream=False)
        return response.text or ""

    return tool(description=description)(ask_agent)


def build_foundry_qa_tool() -> FunctionTool:
    """Return a cached tool that asks a Foundry agent a question."""
    global _CACHED_TOOL
    if _CACHED_TOOL is None:
        _CACHED_TOOL = asyncio.run(_create_foundry_qa_tool())
    return _CACHED_TOOL

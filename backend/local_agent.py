# Copyright (c) Microsoft. All rights reserved.

"""Local agent demonstrating shared state management."""

from __future__ import annotations

from typing import Any

from agent_framework import Agent, SupportsChatGetResponse
from agent_framework.ag_ui import AgentFrameworkAgent
from backend.agent_tool import build_foundry_qa_tool
from backend.state import update_info, update_title, update_description, update_location, add_component


_AGENT_INSTRUCTIONS = """
    You are helping users complete a project document using shared state.

    Rules:
    1. You receive current state in system context.
    2. Use the smallest matching tool:
       - update_title(name)
       - update_description(description)
       - update_location(location)
       - add_component(components)
       - update_info(project) only for full rewrites or multi-field updates.
    3. Preserve existing data. Do not remove components unless the user explicitly asks.
    4. For add_component, send the full updated components list.
    5. After tool calls, reply briefly (1-2 sentences).
    6. Use ask_foundry(question) to talk with another agent for tasks not about project state.
"""

def _build_tools(client: SupportsChatGetResponse[Any]) -> list[Any]:
    tools: list[Any] = [
        update_info,
        update_title,
        update_description,
        update_location,
        add_component,
        build_foundry_qa_tool(),
    ]

    return tools


def local_agent(client: SupportsChatGetResponse[Any]) -> AgentFrameworkAgent:
    """Create a local agent with streaming state updates.

    Args:
        client: The chat client to use for the agent

    Returns:
        A configured AgentFrameworkAgent instance with state management
    """
    agent = Agent(
        name="local_agent",
        instructions=_AGENT_INSTRUCTIONS,
        client=client,
        tools=_build_tools(client),
    )

    return AgentFrameworkAgent(
        agent=agent,
        name="local_agent",
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

#!/usr/bin/env python3
"""Update an Azure AI Foundry agent to add project state update tools.

Usage:
    python scripts/update_foundry_agent.py \
        --endpoint "https://<account>.services.ai.azure.com/api/projects/<project>" \
        --agent-name "AgentSmith"

Environment variables:
    AZURE_AI_PROJECT_ENDPOINT: Foundry project endpoint.
    AZURE_AI_PROJECT_AGENT_NAME: Agent name.

Example:
    AZURE_AI_PROJECT_ENDPOINT="https://.../api/projects/your-project" \
    AZURE_AI_PROJECT_AGENT_NAME="AgentSmith" \
    python scripts/update_foundry_agent.py
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.ai.projects import models
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

EXIT_SUCCESS = 0
EXIT_FAILURE = 1
EXIT_ERROR = 2

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        description="Add or update project state tools on a Foundry agent."
    )
    parser.add_argument(
        "--endpoint",
        default=os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
        help="Foundry project endpoint. Defaults to AZURE_AI_PROJECT_ENDPOINT.",
    )
    parser.add_argument(
        "--agent-name",
        default=os.getenv("AZURE_AI_PROJECT_AGENT_NAME"),
        help="Agent name. Defaults to AZURE_AI_PROJECT_AGENT_NAME.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without updating the agent.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def configure_logging(verbose: bool = False) -> None:
    """Configure logging based on verbosity level.

    Args:
        verbose: Whether to enable debug logging.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _build_update_info_schema() -> dict[str, Any]:
    """Build the JSON schema for the update_info tool.

    Returns:
        JSON schema for the update_info parameters.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "project": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "location": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "country": {"type": "string"},
                            "district": {"type": "string"},
                            "lat": {"type": "number"},
                            "long": {"type": "number"},
                        },
                        "required": ["country", "district", "lat", "long"],
                    },
                    "components": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "environment_impact": {"type": "string"},
                            },
                            "required": ["type", "description", "environment_impact"],
                        },
                    },
                },
                "required": ["name", "description", "location", "components"],
            }
        },
        "required": ["project"],
    }


def _build_location_schema() -> dict[str, Any]:
    """Build the JSON schema for a location object.

    Returns:
        JSON schema for location.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "country": {"type": "string"},
            "district": {"type": "string"},
            "lat": {"type": "number"},
            "long": {"type": "number"},
        },
        "required": ["country", "district", "lat", "long"],
    }


def _build_component_schema() -> dict[str, Any]:
    """Build the JSON schema for a component object.

    Returns:
        JSON schema for a project component.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "type": {"type": "string"},
            "description": {"type": "string"},
            "environment_impact": {"type": "string"},
        },
        "required": ["type", "description", "environment_impact"],
    }


def _build_update_title_schema() -> dict[str, Any]:
    """Build the JSON schema for the update_title tool.

    Returns:
        JSON schema for the update_title parameters.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
        },
        "required": ["name"],
    }


def _build_update_description_schema() -> dict[str, Any]:
    """Build the JSON schema for the update_description tool.

    Returns:
        JSON schema for the update_description parameters.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "description": {"type": "string"},
        },
        "required": ["description"],
    }


def _build_update_location_schema() -> dict[str, Any]:
    """Build the JSON schema for the update_location tool.

    Returns:
        JSON schema for the update_location parameters.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "location": _build_location_schema(),
        },
        "required": ["location"],
    }


def _build_add_component_schema() -> dict[str, Any]:
    """Build the JSON schema for the add_component tool.

    Returns:
        JSON schema for the add_component parameters.
    """
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "components": {
                "type": "array",
                "items": _build_component_schema(),
            },
        },
        "required": ["components"],
    }


def _build_project_tools() -> list[models.FunctionTool]:
    """Build all project update tools for the agent definition.

    Returns:
        FunctionTool definitions for project state updates.
    """
    return [
        models.FunctionTool(
            name="update_info",
            description="Update the project object with new or modified content.",
            parameters=_build_update_info_schema(),
            strict=True,
        ),
        models.FunctionTool(
            name="update_title",
            description="Update the project title.",
            parameters=_build_update_title_schema(),
            strict=True,
        ),
        models.FunctionTool(
            name="update_description",
            description="Update the project description.",
            parameters=_build_update_description_schema(),
            strict=True,
        ),
        models.FunctionTool(
            name="update_location",
            description="Update the project location.",
            parameters=_build_update_location_schema(),
            strict=True,
        ),
        models.FunctionTool(
            name="add_component",
            description="Update project components after adding or editing an item.",
            parameters=_build_add_component_schema(),
            strict=True,
        ),
    ]


def _get_tool_names(definition: models.AgentDefinition) -> list[str]:
    """Return tool names from an agent definition.

    Args:
        definition: Agent definition to inspect.

    Returns:
        List of tool names.
    """
    tools = list(getattr(definition, "tools", []) or [])
    names = []
    for tool in tools:
        name = getattr(tool, "name", None)
        if name:
            names.append(name)
    return names


def _verify_version_tools(
    client: AIProjectClient,
    agent_name: str,
    version: int,
    expected_tool_names: list[str],
) -> bool:
    """Verify persisted tools for a specific agent version.

    Args:
        client: AIProjectClient instance.
        agent_name: Name of the agent.
        version: Version number to verify.
        expected_tool_names: Tool names expected to be present.

    Returns:
        True when all expected tool names are present.
    """
    persisted = client.agents.get_version(agent_name, version)
    persisted_definition = getattr(persisted, "definition", None)
    persisted_tools = []
    if persisted_definition is not None:
        persisted_tools = _get_tool_names(persisted_definition)

    missing_tools = [name for name in expected_tool_names if name not in persisted_tools]
    logger.info("Persisted tool list for version %s: %s", version, ", ".join(persisted_tools))

    if missing_tools:
        logger.warning("Missing expected tools on persisted version %s: %s", version, ", ".join(missing_tools))
        return False

    return True


def run(endpoint: str, agent_name: str, dry_run: bool) -> int:
    """Update the agent definition with project state tools.

    Args:
        endpoint: Foundry project endpoint.
        agent_name: Name of the agent to update.
        dry_run: Whether to skip the update call.

    Returns:
        Exit code.
    """
    credential = DefaultAzureCredential()

    client = AIProjectClient(endpoint=endpoint, credential=credential)
    agent = client.agents.get(agent_name)

    definition = agent.versions.latest.definition
    if not hasattr(definition, "tools"):
        logger.error("Agent definition does not support tools: %s", type(definition))
        return EXIT_FAILURE

    tools = list(getattr(definition, "tools", []) or [])
    project_tools = _build_project_tools()

    indexed_tool_names = {
        getattr(existing_tool, "name", ""): index
        for index, existing_tool in enumerate(tools)
        if getattr(existing_tool, "name", "")
    }

    for project_tool in project_tools:
        project_tool_name = getattr(project_tool, "name", "")
        if not project_tool_name:
            continue

        existing_index = indexed_tool_names.get(project_tool_name)
        if existing_index is None:
            tools.append(project_tool)
            indexed_tool_names[project_tool_name] = len(tools) - 1
        else:
            tools[existing_index] = project_tool

    definition.tools = tools

    logger.info("Planned tool list: %s", ", ".join(_get_tool_names(definition)))

    expected_tool_names = [
        name
        for name in (getattr(project_tool, "name", "") for project_tool in project_tools)
        if name
    ]

    if dry_run:
        logger.info("Dry run enabled. No update was performed.")
        return EXIT_SUCCESS

    updated = client.agents.update(agent_name, definition=definition)
    version = updated.versions.latest.version
    logger.info("Agent updated successfully. New version: %s", version)

    if not _verify_version_tools(client, agent_name, version, expected_tool_names):
        logger.warning(
            "Update call succeeded, but persisted version verification failed. "
            "Confirm you are viewing agent '%s' version %s in Foundry.",
            agent_name,
            version,
        )

    return EXIT_SUCCESS


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code.
    """
    load_dotenv()
    parser = create_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)

    if not args.endpoint:
        logger.error("Missing endpoint. Use --endpoint or AZURE_AI_PROJECT_ENDPOINT.")
        return EXIT_ERROR
    if not args.agent_name:
        logger.error("Missing agent name. Use --agent-name or AZURE_AI_PROJECT_AGENT_NAME.")
        return EXIT_ERROR

    try:
        return run(args.endpoint, args.agent_name, args.dry_run)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 130
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Error: %s", exc)
        return EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())

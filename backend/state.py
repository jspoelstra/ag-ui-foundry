"""Recipe agent example demonstrating shared state management (Feature 3)."""

from __future__ import annotations

from agent_framework import tool
from pydantic import BaseModel, Field

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


def _rebuild_tool_models() -> None:
    tool_models = (
        update_info,
        update_location,
        add_component,
    )
    type_namespace = globals()
    for tool_fn in tool_models:
        input_model = getattr(tool_fn, "input_model", None)
        if input_model is not None:
            input_model.model_rebuild(_types_namespace=type_namespace)


_rebuild_tool_models()

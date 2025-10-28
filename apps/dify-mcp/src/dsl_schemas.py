"""
Dify DSL Schema Definitions

Self-contained Pydantic schemas for Dify workflow DSL.
These schemas are designed for DSL validation and construction,
with stricter rules than Dify's internal schemas where needed.

Key differences from Dify internal schemas:
- environment_variables require 'value' field (prevents runtime errors)
- Focused on DSL structure rather than runtime requirements
"""

from typing import Any, Literal
from pydantic import BaseModel, Field


# ============================================================================
# Variables
# ============================================================================


class EnvironmentVariable(BaseModel):
    """
    Environment variable definition.

    IMPORTANT: 'value' is REQUIRED here (unlike Dify's internal validation)
    to prevent runtime "missing value" errors when the workflow executes.
    """

    id: str = Field(..., description="Unique variable identifier")
    name: str = Field(..., description="Display name")
    value_type: Literal["string", "number", "secret"] = Field(
        ..., description="Value type"
    )
    value: str = Field(
        ...,
        description="Variable value (REQUIRED for runtime execution). "
        "Use empty string '' if you want to set it later via UI."
    )
    required: bool = Field(default=True, description="Whether this variable is required")


class ConversationVariable(BaseModel):
    """Conversation variable that persists across conversation turns."""

    id: str = Field(..., description="Unique variable identifier")
    name: str = Field(..., description="Display name")
    value_type: Literal[
        "string",
        "number",
        "array[string]",
        "array[number]",
        "array[object]",
        "object"
    ] = Field(..., description="Value type")
    description: str = Field(default="", description="Variable description")


# ============================================================================
# Workflow Graph Components
# ============================================================================


class NodePosition(BaseModel):
    """Node position in the workflow canvas."""

    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate")


class NodeBase(BaseModel):
    """
    Base structure for all workflow nodes.

    Every node in the workflow graph must have:
    - id: unique identifier
    - data: node-specific configuration
    - position: canvas coordinates
    """

    id: str = Field(..., description="Unique node identifier")
    data: dict[str, Any] = Field(
        ...,
        description="Node configuration data. Must include 'type' and 'title' fields."
    )
    position: NodePosition = Field(..., description="Node position on canvas")
    width: int | None = Field(
        default=None,
        description="Node width (optional, frontend calculates dynamically)"
    )
    height: int | None = Field(
        default=None,
        description="Node height (optional, frontend calculates dynamically)"
    )


class Edge(BaseModel):
    """Connection between two nodes in the workflow."""

    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    sourceHandle: str = Field(default="source", description="Source handle name")
    targetHandle: str = Field(default="target", description="Target handle name")
    id: str | None = Field(default=None, description="Optional edge ID")
    type: str = Field(default="custom", description="Edge type")
    data: dict[str, Any] | None = Field(default=None, description="Additional edge data")
    zIndex: int = Field(default=0, description="Z-index for rendering")


class Viewport(BaseModel):
    """Viewport configuration for the workflow canvas."""

    x: float = Field(default=0, description="Viewport X offset")
    y: float = Field(default=0, description="Viewport Y offset")
    zoom: float = Field(default=1, description="Zoom level")


class WorkflowGraph(BaseModel):
    """Workflow graph structure containing nodes and edges."""

    nodes: list[NodeBase] = Field(default_factory=list, description="List of workflow nodes")
    edges: list[Edge] = Field(default_factory=list, description="List of node connections")
    viewport: Viewport = Field(default_factory=Viewport, description="Canvas viewport settings")


# ============================================================================
# Workflow Configuration
# ============================================================================


class Workflow(BaseModel):
    """Workflow configuration for workflow/advanced-chat apps."""

    environment_variables: list[EnvironmentVariable] = Field(
        default_factory=list,
        description="Environment variables (workspace-level configuration)"
    )
    conversation_variables: list[ConversationVariable] = Field(
        default_factory=list,
        description="Conversation variables (persist across turns)"
    )
    graph: WorkflowGraph = Field(..., description="Workflow graph with nodes and edges")
    features: dict[str, Any] = Field(
        default_factory=dict,
        description="Workflow features configuration (file upload, etc.)"
    )
    rag_pipeline_variables: list[Any] = Field(
        default_factory=list,
        description="RAG pipeline variables"
    )


# ============================================================================
# App Configuration
# ============================================================================


class App(BaseModel):
    """Application metadata and configuration."""

    mode: Literal["workflow", "chat", "agent-chat", "advanced-chat", "completion"] = Field(
        ..., description="Application mode"
    )
    name: str = Field(..., description="Application name")
    description: str = Field(default="", description="Application description")
    icon: str = Field(default="🤖", description="Application icon (emoji or URL)")
    icon_background: str = Field(
        default="#FFEAD5",
        description="Icon background color (hex)"
    )
    use_icon_as_answer_icon: bool = Field(
        default=False,
        description="Whether to use app icon as answer icon"
    )


# ============================================================================
# Top-Level DSL Structure
# ============================================================================


class DifyDSL(BaseModel):
    """
    Complete Dify DSL schema for workflow definitions.

    This is the root schema for validating and constructing Dify workflow YAML files.
    """

    version: str = Field(
        default="0.4.0",
        description="DSL version (current: 0.4.0)"
    )
    kind: Literal["app"] = Field(
        default="app",
        description="Resource kind (must be 'app')"
    )
    app: App = Field(..., description="Application configuration")
    workflow: Workflow | None = Field(
        default=None,
        description="Workflow configuration (required for workflow/advanced-chat modes)"
    )
    app_model_config: dict[str, Any] | None = Field(
        default=None,
        description="Model configuration (required for chat/completion modes)",
        alias="model_config"  # Use alias to map to YAML field name
    )
    dependencies: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Plugin/tool/model dependencies"
    )

    model_config = {"populate_by_name": True}  # Allow both field name and alias


# ============================================================================
# Helper Functions
# ============================================================================


def create_empty_workflow(
    name: str,
    description: str = "",
    icon: str = "🤖",
    icon_background: str = "#FFEAD5"
) -> DifyDSL:
    """
    Create an empty workflow with default configuration.

    Args:
        name: Workflow name
        description: Workflow description
        icon: Icon emoji or URL
        icon_background: Icon background color

    Returns:
        Empty DifyDSL workflow ready for adding nodes
    """
    return DifyDSL(
        version="0.4.0",
        kind="app",
        app=App(
            mode="workflow",
            name=name,
            description=description,
            icon=icon,
            icon_background=icon_background,
        ),
        workflow=Workflow(
            graph=WorkflowGraph()
        )
    )


def validate_dsl(dsl_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate DSL data against schema.

    Args:
        dsl_data: Dictionary representation of DSL

    Returns:
        Tuple of (is_valid, error_messages)
    """
    try:
        DifyDSL.model_validate(dsl_data)
        return True, []
    except Exception as e:
        from pydantic import ValidationError
        if isinstance(e, ValidationError):
            errors = []
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                errors.append(f"{field_path}: {error['msg']}")
            return False, errors
        return False, [str(e)]

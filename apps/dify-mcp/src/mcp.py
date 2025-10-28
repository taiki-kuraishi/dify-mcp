"""
Dify Workflow MCP Server

Provides Model Context Protocol (MCP) tools and resources for working with Dify workflow DSL YAML.
"""

import json
from fastmcp import FastMCP
from .dsl_schema_info import (
    get_node_schema_details,
)
from .validator import validate_workflow_yaml
from .workflow_manager import WorkflowManager, WorkflowManagerError
from .node_builders import (
    create_start_node,
    create_end_node,
    create_llm_node,
    create_template_node,
    create_answer_node,
)

# Initialize MCP server
fast_mcp = FastMCP("Dify Workflow Validator")


@fast_mcp.tool()
def validate_dify_workflow(yaml_content: str) -> dict:
    """
    Validate a Dify workflow YAML file.

    This tool validates the structure, syntax, and semantics of a Dify workflow DSL YAML file
    without requiring a database connection. It performs the same validation as Dify's
    AppDslService.import_app() but in a dry-run mode.

    Args:
        yaml_content: The complete YAML content of the workflow file as a string.

    Returns:
        A dictionary containing validation results with the following structure:
        {
            "success": bool,           # Whether validation passed
            "errors": list[dict],      # List of errors found (if any)
            "warnings": list[dict],    # List of warnings (if any)
            "info": dict              # Additional information about the workflow
        }

        Each error/warning contains:
        - stage: The validation stage where the issue occurred
        - code: A machine-readable error code
        - message: A human-readable description
        - details: Optional additional information (dict)

        The info dict may contain:
        - dsl_version: The DSL version from the YAML
        - app_mode: The application mode (workflow, chat, etc.)
        - node_count: Number of nodes in the workflow graph
        - edge_count: Number of edges in the workflow graph
    """
    return validate_workflow_yaml(yaml_content)


@fast_mcp.tool()
def get_dify_dsl_version() -> str:
    """
    Get the current supported Dify DSL version.

    Returns:
        The current DSL version string (e.g., "0.4.0")
    """
    from .validator import CURRENT_DSL_VERSION

    return CURRENT_DSL_VERSION


@fast_mcp.tool()
def get_supported_app_modes() -> list[str]:
    """
    Get the list of supported Dify app modes.

    Returns:
        List of supported app mode strings: ["workflow", "advanced-chat", "chat", "agent-chat", "completion"]
    """
    from .validator import AppMode

    return [mode.value for mode in AppMode]


@fast_mcp.tool()
def get_node_schema(node_type: str) -> dict:
    """
    Get detailed schema information for a specific node type.

    Args:
        node_type: The node type identifier (e.g., "llm", "code", "http-request", "if-else")

    Returns:
        A dictionary containing:
        - type: The node type
        - schema_available: Whether Pydantic schema validation is available
        - schema_class: Name of the Pydantic schema class (if available)
        - fields: Dictionary of field definitions with types and requirements
        - example_structure: Example node structure
        - error: Error message if node type is unknown

    Example:
        >>> schema = get_node_schema("llm")
        >>> print(schema["schema_available"])
        True
        >>> print(schema["fields"]["model"]["required"])
        True
    """
    return get_node_schema_details(node_type)

@fast_mcp.tool()
def create_workflow(
    name: str,
    description: str = "",
    icon: str = "🤖",
    icon_background: str = "#FFEAD5"
) -> str:
    """
    Create a new empty Dify workflow.

    Args:
        name: Workflow name
        description: Workflow description (optional)
        icon: Icon emoji or URL (default: "🤖")
        icon_background: Icon background color hex (default: "#FFEAD5")

    Returns:
        YAML string of the empty workflow

    Example:
        >>> workflow_yaml = create_workflow("My AI Workflow", "A workflow for AI tasks")
    """
    try:
        manager = WorkflowManager.create_new(name, description, icon, icon_background)
        return manager.to_yaml()
    except Exception as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def add_start_node(
    workflow_yaml: str,
    node_id: str | None = None,
    title: str = "開始",
    x: float = 80,
    y: float = 282,
    variables: list[dict] | None = None
) -> str:
    """
    Add a Start node to a workflow.

    Args:
        workflow_yaml: Current workflow YAML string
        node_id: Node ID (auto-generated if not provided)
        title: Node title (default: "開始")
        x: X coordinate (default: 80)
        y: Y coordinate (default: 282)
        variables: List of input variables, each with:
            - variable: Variable name (str)
            - label: Display label (str)
            - type: "text-input", "paragraph", "select", "number", "file", etc.
            - required: Whether required (bool, default: False)
            - default: Default value (str, default: "")
            - placeholder: Placeholder text (str, optional)
            - options: List of options for select type (list[str], optional)

    Returns:
        Updated workflow YAML string with the new Start node

    Example:
        >>> workflow = create_workflow("Test")
        >>> workflow = add_start_node(
        ...     workflow,
        ...     variables=[
        ...         {"variable": "query", "label": "Query", "type": "text-input", "required": True}
        ...     ]
        ... )
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        builder = create_start_node(node_id, title, x, y)

        # Add variables if provided
        if variables:
            for var in variables:
                var_type = var.get("type", "text-input")
                if var_type == "text-input":
                    builder.add_text_input(
                        variable=var["variable"],
                        label=var["label"],
                        required=var.get("required", False),
                        default=var.get("default", ""),
                        max_length=var.get("max_length"),
                        placeholder=var.get("placeholder", "")
                    )
                elif var_type == "paragraph":
                    builder.add_paragraph(
                        variable=var["variable"],
                        label=var["label"],
                        required=var.get("required", False),
                        default=var.get("default", ""),
                        placeholder=var.get("placeholder", "")
                    )
                elif var_type == "select":
                    builder.add_select(
                        variable=var["variable"],
                        label=var["label"],
                        options=var.get("options", []),
                        required=var.get("required", False),
                        default=var.get("default", "")
                    )

        manager.add_node(builder)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def add_end_node(
    workflow_yaml: str,
    node_id: str | None = None,
    title: str = "終了",
    x: float = 756,
    y: float = 300,
    outputs: list[dict] | None = None
) -> str:
    """
    Add an End node to a workflow.

    Args:
        workflow_yaml: Current workflow YAML string
        node_id: Node ID (auto-generated if not provided)
        title: Node title (default: "終了")
        x: X coordinate (default: 756)
        y: Y coordinate (default: 300)
        outputs: List of output variables, each with:
            - variable: Output variable name (str)
            - value_selector: Path to source value (list[str]), e.g., ["llm_node", "text"]

    Returns:
        Updated workflow YAML string with the new End node

    Example:
        >>> workflow = add_end_node(
        ...     workflow,
        ...     outputs=[{"variable": "result", "value_selector": ["llm_1", "text"]}]
        ... )
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        builder = create_end_node(node_id, title, x, y)

        # Add outputs if provided
        if outputs:
            for output in outputs:
                builder.add_output(
                    variable_name=output["variable"],
                    value_selector=output["value_selector"]
                )

        manager.add_node(builder)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def add_llm_node(
    workflow_yaml: str,
    node_id: str | None = None,
    title: str = "LLM",
    x: float = 382,
    y: float = 282,
    provider: str = "openai",
    model_name: str = "gpt-4",
    temperature: float = 0.7,
    max_tokens: int | None = None,
    system_prompt: str = "",
    user_prompt: str = "",
    context_enabled: bool = False,
    context_variable_selector: list[str] | None = None
) -> str:
    """
    Add an LLM node to a workflow.

    Args:
        workflow_yaml: Current workflow YAML string
        node_id: Node ID (auto-generated if not provided)
        title: Node title (default: "LLM")
        x: X coordinate (default: 382)
        y: Y coordinate (default: 282)
        provider: Model provider (e.g., "openai", "anthropic")
        model_name: Model name (e.g., "gpt-4", "claude-3-sonnet")
        temperature: Temperature (0-2, default: 0.7)
        max_tokens: Maximum tokens to generate (optional)
        system_prompt: System prompt text
        user_prompt: User prompt text (can include variable references like {{#node.field#}})
        context_enabled: Whether to enable context input (default: False)
        context_variable_selector: Path to context variable (e.g., ["start", "context"])

    Returns:
        Updated workflow YAML string with the new LLM node

    Example:
        >>> workflow = add_llm_node(
        ...     workflow,
        ...     provider="openai",
        ...     model_name="gpt-4",
        ...     system_prompt="You are a helpful assistant.",
        ...     user_prompt="{{#start.query#}}"
        ... )
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        builder = create_llm_node(node_id, title, x, y)

        builder.set_model(provider, model_name, "chat", temperature, max_tokens)

        if system_prompt:
            builder.add_system_prompt(system_prompt)

        if user_prompt:
            builder.add_user_prompt(user_prompt)

        if context_enabled:
            builder.set_context(enabled=True, variable_selector=context_variable_selector)

        manager.add_node(builder)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def add_template_transform_node(
    workflow_yaml: str,
    node_id: str | None = None,
    title: str = "テンプレート変換",
    x: float = 0,
    y: float = 0,
    variables: list[dict] | None = None,
    template: str = ""
) -> str:
    """
    Add a Template Transform node to a workflow.

    Args:
        workflow_yaml: Current workflow YAML string
        node_id: Node ID (auto-generated if not provided)
        title: Node title (default: "テンプレート変換")
        x: X coordinate
        y: Y coordinate
        variables: List of variables to use in template, each with:
            - variable: Variable name (str)
            - value_selector: Path to source value (list[str])
        template: Jinja2 template string (e.g., "Hello {{name}}!")

    Returns:
        Updated workflow YAML string with the new Template Transform node

    Example:
        >>> workflow = add_template_transform_node(
        ...     workflow,
        ...     variables=[{"variable": "name", "value_selector": ["start", "user_name"]}],
        ...     template="Hello {{name}}!"
        ... )
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        builder = create_template_node(node_id, title, x, y)

        if variables:
            for var in variables:
                builder.add_variable(var["variable"], var["value_selector"])

        if template:
            builder.set_template(template)

        manager.add_node(builder)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def add_answer_node(
    workflow_yaml: str,
    node_id: str | None = None,
    title: str = "直接応答",
    x: float = 0,
    y: float = 0,
    answer_template: str = ""
) -> str:
    """
    Add an Answer node to a workflow (used in advanced-chat mode).

    Args:
        workflow_yaml: Current workflow YAML string
        node_id: Node ID (auto-generated if not provided)
        title: Node title (default: "直接応答")
        x: X coordinate
        y: Y coordinate
        answer_template: Answer text with variable references (e.g., "Result: {{#llm.text#}}")

    Returns:
        Updated workflow YAML string with the new Answer node

    Example:
        >>> workflow = add_answer_node(
        ...     workflow,
        ...     answer_template="The result is: {{#llm_node.text#}}"
        ... )
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        builder = create_answer_node(node_id, title, x, y)

        if answer_template:
            builder.set_answer(answer_template)

        manager.add_node(builder)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def add_edge(
    workflow_yaml: str,
    source_node_id: str,
    target_node_id: str,
    source_handle: str = "source",
    target_handle: str = "target"
) -> str:
    """
    Add an edge (connection) between two nodes in a workflow.

    Args:
        workflow_yaml: Current workflow YAML string
        source_node_id: Source node ID
        target_node_id: Target node ID
        source_handle: Source handle name (default: "source")
        target_handle: Target handle name (default: "target")

    Returns:
        Updated workflow YAML string with the new edge

    Example:
        >>> workflow = add_edge(workflow, "start_node", "llm_node")
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        manager.add_edge(source_node_id, target_node_id, source_handle, target_handle)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def remove_node(workflow_yaml: str, node_id: str) -> str:
    """
    Remove a node from a workflow.

    Also removes all edges connected to this node.

    Args:
        workflow_yaml: Current workflow YAML string
        node_id: ID of node to remove

    Returns:
        Updated workflow YAML string without the node

    Example:
        >>> workflow = remove_node(workflow, "old_node_id")
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        manager.remove_node(node_id)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def remove_edge(
    workflow_yaml: str,
    source_node_id: str,
    target_node_id: str
) -> str:
    """
    Remove an edge between two nodes.

    Args:
        workflow_yaml: Current workflow YAML string
        source_node_id: Source node ID
        target_node_id: Target node ID

    Returns:
        Updated workflow YAML string without the edge

    Example:
        >>> workflow = remove_edge(workflow, "node1", "node2")
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        manager.remove_edge(source_node_id, target_node_id)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def add_environment_variable(
    workflow_yaml: str,
    id: str,
    name: str,
    value_type: str,
    value: str = "",
    required: bool = True
) -> str:
    """
    Add an environment variable to a workflow.

    IMPORTANT: The 'value' field is REQUIRED (even if empty string) to prevent
    runtime "missing value" errors when the workflow executes.

    Args:
        workflow_yaml: Current workflow YAML string
        id: Variable ID (used for referencing: {{env.id}})
        name: Display name
        value_type: "string", "number", or "secret"
        value: Variable value (default: empty string "")
        required: Whether variable is required (default: True)

    Returns:
        Updated workflow YAML string with the new environment variable

    Example:
        >>> workflow = add_environment_variable(
        ...     workflow,
        ...     id="api_key",
        ...     name="API Key",
        ...     value_type="secret",
        ...     value="sk-..."
        ... )
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        manager.add_environment_variable(id, name, value_type, value, required)
        return manager.to_yaml()
    except WorkflowManagerError as e:
        return json.dumps({"error": str(e)})


@fast_mcp.tool()
def list_workflow_nodes(workflow_yaml: str) -> dict:
    """
    List all nodes in a workflow.

    Args:
        workflow_yaml: Workflow YAML string

    Returns:
        Dictionary with:
        - nodes: List of node summaries (id, type, title)
        - count: Number of nodes

    Example:
        >>> result = list_workflow_nodes(workflow)
        >>> print(f"Workflow has {result['count']} nodes")
    """
    try:
        manager = WorkflowManager.from_yaml(workflow_yaml)
        nodes = manager.list_nodes()
        return {
            "nodes": [
                {
                    "id": node.get("id"),
                    "type": node.get("data", {}).get("type"),
                    "title": node.get("data", {}).get("title")
                }
                for node in nodes
            ],
            "count": len(nodes)
        }
    except WorkflowManagerError as e:
        return {"error": str(e)}


def main() -> None:
    """Main entry point for the dify-mcp command."""
    fast_mcp.run()


if __name__ == "__main__":
    main()

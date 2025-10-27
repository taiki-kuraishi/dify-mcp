"""
Dify Workflow MCP Server

Provides Model Context Protocol (MCP) tools for validating Dify workflow DSL YAML.
"""

from fastmcp import FastMCP
from .validator import validate_workflow_yaml

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

    Example:
        >>> result = validate_dify_workflow('''
        ... version: "0.4.0"
        ... kind: app
        ... app:
        ...   mode: workflow
        ...   name: My Workflow
        ... workflow:
        ...   graph:
        ...     nodes: []
        ...     edges: []
        ... ''')
        >>> print(result["success"])
        True
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


def main() -> None:
    """Main entry point for the dify-mcp command."""
    fast_mcp.run()


if __name__ == "__main__":
    main()

"""
Workflow Manager

Provides high-level operations for managing Dify workflows:
- Load/save workflows from/to YAML
- Add/remove/update nodes
- Add/remove edges
- Add/remove variables
- Validate workflows
"""

from typing import Any
import yaml

from .dsl_schemas import (
    EnvironmentVariable,
    ConversationVariable,
    create_empty_workflow,
)
from .validator import validate_workflow_yaml
from .node_builders import NodeBuilder


class WorkflowManagerError(Exception):
    """Error during workflow management operations."""
    pass


class WorkflowManager:
    """
    Manager for Dify workflow operations.

    Provides a high-level API for constructing and modifying workflows
    without directly manipulating the DSL structure.
    """

    def __init__(self, yaml_content: str | None = None):
        """
        Initialize workflow manager.

        Args:
            yaml_content: Optional YAML content to load. If None, creates empty workflow.
        """
        if yaml_content:
            self.data = yaml.safe_load(yaml_content)
        else:
            # Create empty workflow structure
            empty = create_empty_workflow(name="Untitled Workflow")
            self.data = empty.model_dump(exclude_none=True)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "WorkflowManager":
        """
        Create manager from YAML content.

        Args:
            yaml_content: YAML string

        Returns:
            WorkflowManager instance

        Raises:
            WorkflowManagerError: If YAML is invalid
        """
        try:
            return cls(yaml_content=yaml_content)
        except yaml.YAMLError as e:
            raise WorkflowManagerError(f"Invalid YAML: {e}") from e

    @classmethod
    def create_new(
        cls,
        name: str,
        description: str = "",
        icon: str = "🤖",
        icon_background: str = "#FFEAD5"
    ) -> "WorkflowManager":
        """
        Create a new empty workflow.

        Args:
            name: Workflow name
            description: Workflow description
            icon: Icon emoji or URL
            icon_background: Icon background color

        Returns:
            WorkflowManager instance with empty workflow
        """
        workflow = create_empty_workflow(name, description, icon, icon_background)
        manager = cls(yaml_content=None)
        manager.data = workflow.model_dump(exclude_none=True)
        return manager

    def to_yaml(self) -> str:
        """
        Convert workflow to YAML string.

        Returns:
            YAML string representation
        """
        return yaml.dump(self.data, allow_unicode=True, sort_keys=False)

    def validate(self) -> dict[str, Any]:
        """
        Validate the current workflow.

        Returns:
            Validation result dictionary with:
            - success: bool
            - errors: list of error dicts
            - warnings: list of warning dicts
            - info: dict with workflow info
        """
        yaml_content = self.to_yaml()
        return validate_workflow_yaml(yaml_content)

    # ========================================================================
    # Node Operations
    # ========================================================================

    def add_node(self, node_builder: NodeBuilder) -> str:
        """
        Add a node to the workflow.

        Args:
            node_builder: NodeBuilder instance

        Returns:
            Node ID of the added node

        Raises:
            WorkflowManagerError: If node cannot be added
        """
        try:
            node = node_builder.build()
        except Exception as e:
            raise WorkflowManagerError(f"Failed to build node: {e}") from e

        # Ensure workflow structure exists
        if "workflow" not in self.data:
            raise WorkflowManagerError("Workflow structure missing (not a workflow app?)")

        if "graph" not in self.data["workflow"]:
            self.data["workflow"]["graph"] = {"nodes": [], "edges": [], "viewport": {"x": 0, "y": 0, "zoom": 1}}

        if "nodes" not in self.data["workflow"]["graph"]:
            self.data["workflow"]["graph"]["nodes"] = []

        # Check for duplicate node ID
        existing_ids = {n.get("id") for n in self.data["workflow"]["graph"]["nodes"]}
        if node["id"] in existing_ids:
            raise WorkflowManagerError(f"Node with ID '{node['id']}' already exists")

        self.data["workflow"]["graph"]["nodes"].append(node)
        node_id: str = node["id"]
        return node_id

    def remove_node(self, node_id: str) -> None:
        """
        Remove a node from the workflow.

        Also removes all edges connected to this node.

        Args:
            node_id: ID of node to remove

        Raises:
            WorkflowManagerError: If node not found
        """
        if "workflow" not in self.data or "graph" not in self.data["workflow"]:
            raise WorkflowManagerError("Workflow structure missing")

        nodes = self.data["workflow"]["graph"].get("nodes", [])
        edges = self.data["workflow"]["graph"].get("edges", [])

        # Find and remove node
        original_length = len(nodes)
        self.data["workflow"]["graph"]["nodes"] = [n for n in nodes if n.get("id") != node_id]

        if len(self.data["workflow"]["graph"]["nodes"]) == original_length:
            raise WorkflowManagerError(f"Node '{node_id}' not found")

        # Remove connected edges
        self.data["workflow"]["graph"]["edges"] = [
            e for e in edges
            if e.get("source") != node_id and e.get("target") != node_id
        ]

    def get_node(self, node_id: str) -> dict[str, Any]:
        """
        Get a node by ID.

        Args:
            node_id: Node ID

        Returns:
            Node dictionary

        Raises:
            WorkflowManagerError: If node not found
        """
        if "workflow" not in self.data or "graph" not in self.data["workflow"]:
            raise WorkflowManagerError("Workflow structure missing")

        nodes = self.data["workflow"]["graph"].get("nodes", [])
        for node in nodes:
            if node.get("id") == node_id:
                result: dict[str, Any] = node
                return result

        raise WorkflowManagerError(f"Node '{node_id}' not found")

    def update_node(self, node_id: str, node_builder: NodeBuilder) -> None:
        """
        Update an existing node.

        Args:
            node_id: ID of node to update
            node_builder: NodeBuilder with new configuration

        Raises:
            WorkflowManagerError: If node not found or update fails
        """
        # Remove old node
        self.remove_node(node_id)

        # Add new node with same ID
        try:
            self.add_node(node_builder)
        except Exception as e:
            raise WorkflowManagerError(f"Failed to update node: {e}") from e

    def list_nodes(self) -> list[dict[str, Any]]:
        """
        Get list of all nodes.

        Returns:
            List of node dictionaries
        """
        if "workflow" not in self.data or "graph" not in self.data["workflow"]:
            return []
        nodes: list[dict[str, Any]] = self.data["workflow"]["graph"].get("nodes", [])
        return nodes

    # ========================================================================
    # Edge Operations
    # ========================================================================

    def add_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        source_handle: str = "source",
        target_handle: str = "target"
    ) -> str:
        """
        Add an edge between two nodes.

        Args:
            source_node_id: Source node ID
            target_node_id: Target node ID
            source_handle: Source handle name
            target_handle: Target handle name

        Returns:
            Edge ID

        Raises:
            WorkflowManagerError: If nodes don't exist or edge cannot be added
        """
        if "workflow" not in self.data or "graph" not in self.data["workflow"]:
            raise WorkflowManagerError("Workflow structure missing")

        # Verify nodes exist
        node_ids = {n.get("id") for n in self.data["workflow"]["graph"].get("nodes", [])}
        if source_node_id not in node_ids:
            raise WorkflowManagerError(f"Source node '{source_node_id}' not found")
        if target_node_id not in node_ids:
            raise WorkflowManagerError(f"Target node '{target_node_id}' not found")

        if "edges" not in self.data["workflow"]["graph"]:
            self.data["workflow"]["graph"]["edges"] = []

        edge_id = f"{source_node_id}-{source_handle}-{target_node_id}-{target_handle}"

        edge = {
            "id": edge_id,
            "source": source_node_id,
            "target": target_node_id,
            "sourceHandle": source_handle,
            "targetHandle": target_handle,
            "type": "custom",
            "zIndex": 0,
        }

        self.data["workflow"]["graph"]["edges"].append(edge)
        return edge_id

    def remove_edge(self, source_node_id: str, target_node_id: str) -> None:
        """
        Remove edge(s) between two nodes.

        Args:
            source_node_id: Source node ID
            target_node_id: Target node ID

        Raises:
            WorkflowManagerError: If no edge found
        """
        if "workflow" not in self.data or "graph" not in self.data["workflow"]:
            raise WorkflowManagerError("Workflow structure missing")

        edges = self.data["workflow"]["graph"].get("edges", [])
        original_length = len(edges)

        self.data["workflow"]["graph"]["edges"] = [
            e for e in edges
            if not (e.get("source") == source_node_id and e.get("target") == target_node_id)
        ]

        if len(self.data["workflow"]["graph"]["edges"]) == original_length:
            raise WorkflowManagerError(
                f"No edge found from '{source_node_id}' to '{target_node_id}'"
            )

    def list_edges(self) -> list[dict[str, Any]]:
        """
        Get list of all edges.

        Returns:
            List of edge dictionaries
        """
        if "workflow" not in self.data or "graph" not in self.data["workflow"]:
            return []
        edges: list[dict[str, Any]] = self.data["workflow"]["graph"].get("edges", [])
        return edges

    # ========================================================================
    # Variable Operations
    # ========================================================================

    def add_environment_variable(
        self,
        id: str,
        name: str,
        value_type: str,
        value: str = "",
        required: bool = True
    ) -> None:
        """
        Add an environment variable.

        Args:
            id: Variable ID
            name: Display name
            value_type: "string", "number", or "secret"
            value: Variable value (default: empty string)
            required: Whether variable is required

        Raises:
            WorkflowManagerError: If variable cannot be added
        """
        if "workflow" not in self.data:
            raise WorkflowManagerError("Workflow structure missing")

        if "environment_variables" not in self.data["workflow"]:
            self.data["workflow"]["environment_variables"] = []

        # Check for duplicate ID
        existing_ids = {v.get("id") for v in self.data["workflow"]["environment_variables"]}
        if id in existing_ids:
            raise WorkflowManagerError(f"Environment variable '{id}' already exists")

        # Validate using our schema
        try:
            var = EnvironmentVariable(
                id=id,
                name=name,
                value_type=value_type,  # type: ignore
                value=value,
                required=required
            )
        except Exception as e:
            raise WorkflowManagerError(f"Invalid environment variable: {e}") from e

        self.data["workflow"]["environment_variables"].append(
            var.model_dump(exclude_none=True)
        )

    def add_conversation_variable(
        self,
        id: str,
        name: str,
        value_type: str,
        description: str = ""
    ) -> None:
        """
        Add a conversation variable.

        Args:
            id: Variable ID
            name: Display name
            value_type: Variable type
            description: Variable description

        Raises:
            WorkflowManagerError: If variable cannot be added
        """
        if "workflow" not in self.data:
            raise WorkflowManagerError("Workflow structure missing")

        if "conversation_variables" not in self.data["workflow"]:
            self.data["workflow"]["conversation_variables"] = []

        # Check for duplicate ID
        existing_ids = {v.get("id") for v in self.data["workflow"]["conversation_variables"]}
        if id in existing_ids:
            raise WorkflowManagerError(f"Conversation variable '{id}' already exists")

        # Validate using our schema
        try:
            var = ConversationVariable(
                id=id,
                name=name,
                value_type=value_type,  # type: ignore
                description=description
            )
        except Exception as e:
            raise WorkflowManagerError(f"Invalid conversation variable: {e}") from e

        self.data["workflow"]["conversation_variables"].append(
            var.model_dump(exclude_none=True)
        )

    def remove_environment_variable(self, id: str) -> None:
        """Remove an environment variable by ID."""
        if "workflow" not in self.data:
            raise WorkflowManagerError("Workflow structure missing")

        variables = self.data["workflow"].get("environment_variables", [])
        original_length = len(variables)

        self.data["workflow"]["environment_variables"] = [
            v for v in variables if v.get("id") != id
        ]

        if len(self.data["workflow"]["environment_variables"]) == original_length:
            raise WorkflowManagerError(f"Environment variable '{id}' not found")

    def remove_conversation_variable(self, id: str) -> None:
        """Remove a conversation variable by ID."""
        if "workflow" not in self.data:
            raise WorkflowManagerError("Workflow structure missing")

        variables = self.data["workflow"].get("conversation_variables", [])
        original_length = len(variables)

        self.data["workflow"]["conversation_variables"] = [
            v for v in variables if v.get("id") != id
        ]

        if len(self.data["workflow"]["conversation_variables"]) == original_length:
            raise WorkflowManagerError(f"Conversation variable '{id}' not found")

    # ========================================================================
    # Metadata Operations
    # ========================================================================

    def set_app_name(self, name: str) -> None:
        """Set the app name."""
        if "app" not in self.data:
            self.data["app"] = {}
        self.data["app"]["name"] = name

    def set_app_description(self, description: str) -> None:
        """Set the app description."""
        if "app" not in self.data:
            self.data["app"] = {}
        self.data["app"]["description"] = description

    def set_app_icon(self, icon: str, icon_background: str | None = None) -> None:
        """
        Set the app icon.

        Args:
            icon: Icon emoji or URL
            icon_background: Optional background color (hex)
        """
        if "app" not in self.data:
            self.data["app"] = {}
        self.data["app"]["icon"] = icon
        if icon_background:
            self.data["app"]["icon_background"] = icon_background

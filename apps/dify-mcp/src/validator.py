"""
Dify Workflow YAML Validator

Validates Dify workflow DSL YAML without database dependencies.
Uses Pydantic schemas directly from Dify for validation.
"""

from enum import StrEnum
from typing import Any

import yaml
from packaging import version as pkg_version
from pydantic import ValidationError
from .schemas import NODE_SCHEMAS, PluginDependency

CURRENT_DSL_VERSION = "0.4.0"
DSL_MAX_SIZE = 10 * 1024 * 1024  # 10MB


class AppMode(StrEnum):
    """App modes from Dify models.AppMode"""

    COMPLETION = "completion"
    CHAT = "chat"
    AGENT_CHAT = "agent-chat"
    ADVANCED_CHAT = "advanced-chat"
    WORKFLOW = "workflow"


def validate_workflow_yaml(yaml_content: str) -> dict[str, Any]:
    """
    Validate workflow YAML using the same logic as AppDslService.import_app()
    but without database operations.

    Args:
        yaml_content: YAML content string to validate

    Returns:
        Dictionary with validation results:
        {
            "success": bool,
            "errors": list[dict],
            "warnings": list[dict],
            "info": dict
        }
    """
    result: dict[str, Any] = {
        "success": False,
        "errors": [],
        "warnings": [],
        "info": {},
    }

    try:
        # Check content size
        if len(yaml_content) > DSL_MAX_SIZE:
            result["errors"].append(
                {
                    "stage": "size_check",
                    "code": "FILE_TOO_LARGE",
                    "message": f"File size exceeds the limit of {DSL_MAX_SIZE / 1024 / 1024}MB",
                }
            )
            return result

        if not yaml_content.strip():
            result["errors"].append(
                {
                    "stage": "content_check",
                    "code": "EMPTY_CONTENT",
                    "message": "Empty YAML content",
                }
            )
            return result

        # Parse YAML to validate format
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            result["errors"].append(
                {
                    "stage": "yaml_parsing",
                    "code": "YAML_SYNTAX_ERROR",
                    "message": f"Invalid YAML format: {str(e)}",
                }
            )
            return result

        if not isinstance(data, dict):
            result["errors"].append(
                {
                    "stage": "yaml_parsing",
                    "code": "INVALID_YAML_TYPE",
                    "message": "Invalid YAML format: content must be a mapping",
                }
            )
            return result

        imported_version = data.get("version", "0.1.0")
        if not isinstance(imported_version, str):
            result["errors"].append(
                {
                    "stage": "version_check",
                    "code": "INVALID_VERSION_TYPE",
                    "message": f"Invalid version type, expected str, got {type(imported_version)}",
                }
            )
            return result

        result["info"]["dsl_version"] = imported_version

        # Check version compatibility
        try:
            pkg_version.parse(CURRENT_DSL_VERSION)
            pkg_version.parse(imported_version)
        except pkg_version.InvalidVersion:
            result["errors"].append(
                {
                    "stage": "version_check",
                    "code": "INVALID_VERSION_FORMAT",
                    "message": f"Invalid version format: {imported_version}",
                }
            )
            return result

        # Extract app data
        app_data = data.get("app")
        if not app_data:
            result["errors"].append(
                {
                    "stage": "schema_validation",
                    "code": "MISSING_APP_DATA",
                    "message": "Missing app data in YAML content",
                }
            )
            return result

        # Check app mode
        app_mode = app_data.get("mode")
        if not app_mode:
            result["errors"].append(
                {
                    "stage": "schema_validation",
                    "code": "MISSING_APP_MODE",
                    "message": "Missing app mode",
                }
            )
            return result

        try:
            app_mode_enum = AppMode(app_mode)
            result["info"]["app_mode"] = app_mode
        except ValueError:
            result["errors"].append(
                {
                    "stage": "schema_validation",
                    "code": "INVALID_APP_MODE",
                    "message": f"Invalid app mode: {app_mode}. Must be one of: {[m.value for m in AppMode]}",
                }
            )
            return result

        # Check for workflow or model_config based on mode
        if app_mode_enum in {AppMode.ADVANCED_CHAT, AppMode.WORKFLOW}:
            workflow_data = data.get("workflow")
            if not workflow_data or not isinstance(workflow_data, dict):
                result["errors"].append(
                    {
                        "stage": "schema_validation",
                        "code": "MISSING_WORKFLOW_DATA",
                        "message": "Missing workflow data for workflow/advanced chat app",
                    }
                )
                return result

            # Basic workflow structure check
            graph = workflow_data.get("graph", {})
            if not isinstance(graph, dict):
                result["errors"].append(
                    {
                        "stage": "workflow_validation",
                        "code": "INVALID_GRAPH_TYPE",
                        "message": "Workflow graph must be a mapping",
                    }
                )
                return result

            nodes = graph.get("nodes", None)
            edges = graph.get("edges", None)

            if not isinstance(nodes, list):
                result["errors"].append(
                    {
                        "stage": "workflow_validation",
                        "code": "INVALID_NODES_TYPE",
                        "message": "Workflow nodes must be a list",
                    }
                )
                return result

            if not isinstance(edges, list):
                result["errors"].append(
                    {
                        "stage": "workflow_validation",
                        "code": "INVALID_EDGES_TYPE",
                        "message": "Workflow edges must be a list",
                    }
                )
                return result

            result["info"]["node_count"] = len(nodes)
            result["info"]["edge_count"] = len(edges)

            # Basic node structure validation
            for idx, node in enumerate(nodes):
                if not isinstance(node, dict):
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "INVALID_NODE_TYPE",
                            "message": f"Node at index {idx} must be a mapping",
                        }
                    )
                    continue

                node_id = node.get("id", f"node_{idx}")

                if "id" not in node:
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "MISSING_NODE_ID",
                            "message": f"Node at index {idx} is missing 'id' field",
                        }
                    )

                if "data" not in node or not isinstance(node["data"], dict):
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "MISSING_NODE_DATA",
                            "message": f"Node '{node_id}' is missing or has invalid 'data' field",
                        }
                    )
                    continue

                node_data = node.get("data", {})
                node_type = node_data.get("type")

                # Validate node using Pydantic schemas
                if node_type in NODE_SCHEMAS:
                    schema_class = NODE_SCHEMAS[node_type]
                    if (
                        schema_class is not None
                    ):  # Check if schema was successfully imported
                        try:
                            # Validate node data using Pydantic
                            schema_class.model_validate(node_data)
                        except ValidationError as e:
                            # Convert Pydantic validation errors to our format
                            for error in e.errors():
                                field_path = ".".join(str(loc) for loc in error["loc"])
                                result["errors"].append(
                                    {
                                        "stage": "node_validation",
                                        "code": "PYDANTIC_VALIDATION_ERROR",
                                        "message": f"Node '{node_id}' ({node_type}): {field_path} - {error['msg']}",
                                        "details": {
                                            "node_id": node_id,
                                            "node_type": node_type,
                                            "field": field_path,
                                            "error_type": error["type"],
                                        },
                                    }
                                )
                        except Exception as e:
                            # Catch any other validation errors
                            result["errors"].append(
                                {
                                    "stage": "node_validation",
                                    "code": "NODE_VALIDATION_ERROR",
                                    "message": f"Node '{node_id}' ({node_type}): {str(e)}",
                                }
                            )
                    else:
                        # Schema not available (missing dependencies)
                        result["warnings"].append(
                            {
                                "stage": "node_validation",
                                "code": "NODE_SCHEMA_UNAVAILABLE",
                                "message": f"Node '{node_id}' ({node_type}): Schema validation unavailable (missing dependencies). Basic validation only.",
                            }
                        )
                else:
                    # Unknown node type
                    result["warnings"].append(
                        {
                            "stage": "node_validation",
                            "code": "UNKNOWN_NODE_TYPE",
                            "message": f"Node '{node_id}': Unknown node type '{node_type}'. Schema validation skipped.",
                        }
                    )

                # Frontend compatibility: Check node position
                if "position" not in node:
                    result["errors"].append(
                        {
                            "stage": "frontend_compatibility",
                            "code": "MISSING_NODE_POSITION",
                            "message": f"Node '{node_id}' is missing 'position' field required by frontend",
                        }
                    )
                    continue

                position = node.get("position")
                if not isinstance(position, dict):
                    result["errors"].append(
                        {
                            "stage": "frontend_compatibility",
                            "code": "INVALID_NODE_POSITION_TYPE",
                            "message": f"Node '{node_id}' position must be a mapping with x and y coordinates",
                        }
                    )
                    continue

                if "x" not in position or "y" not in position:
                    result["errors"].append(
                        {
                            "stage": "frontend_compatibility",
                            "code": "INCOMPLETE_NODE_POSITION",
                            "message": f"Node '{node_id}' position must have both 'x' and 'y' coordinates",
                        }
                    )
                    continue

                # Check position values are numeric
                if not isinstance(position.get("x"), (int, float)) or not isinstance(
                    position.get("y"), (int, float)
                ):
                    result["errors"].append(
                        {
                            "stage": "frontend_compatibility",
                            "code": "INVALID_NODE_POSITION_VALUES",
                            "message": f"Node '{node_id}' position x and y must be numeric values",
                        }
                    )

            # Basic edge validation
            node_ids = {
                node.get("id")
                for node in nodes
                if isinstance(node, dict) and "id" in node
            }
            for idx, edge in enumerate(edges):
                if not isinstance(edge, dict):
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "INVALID_EDGE_TYPE",
                            "message": f"Edge at index {idx} must be a mapping",
                        }
                    )
                    continue

                source = edge.get("source")
                target = edge.get("target")

                if not source:
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "MISSING_EDGE_SOURCE",
                            "message": f"Edge at index {idx} is missing 'source' field",
                        }
                    )

                if not target:
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "MISSING_EDGE_TARGET",
                            "message": f"Edge at index {idx} is missing 'target' field",
                        }
                    )

                if source and source not in node_ids:
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "INVALID_EDGE_SOURCE",
                            "message": f"Edge references non-existent source node '{source}'",
                        }
                    )

                if target and target not in node_ids:
                    result["errors"].append(
                        {
                            "stage": "workflow_validation",
                            "code": "INVALID_EDGE_TARGET",
                            "message": f"Edge references non-existent target node '{target}'",
                        }
                    )

        elif app_mode_enum in {AppMode.CHAT, AppMode.AGENT_CHAT, AppMode.COMPLETION}:
            if "model_config" not in data:
                result["errors"].append(
                    {
                        "stage": "schema_validation",
                        "code": "MISSING_MODEL_CONFIG",
                        "message": f"Missing model_config for {app_mode} app",
                    }
                )
                return result

        # Frontend compatibility validation for workflow features
        if app_mode_enum in {AppMode.WORKFLOW, AppMode.ADVANCED_CHAT}:
            workflow_data = data.get("workflow", {})
            features = workflow_data.get("features", {})

            # Check file_upload structure for frontend compatibility
            file_upload = features.get("file_upload")
            if (
                file_upload
                and isinstance(file_upload, dict)
                and file_upload.get("enabled")
            ):
                required_arrays = [
                    "allowed_file_types",
                    "allowed_file_extensions",
                    "allowed_file_upload_methods",
                ]
                for field in required_arrays:
                    if field not in file_upload:
                        result["warnings"].append(
                            {
                                "stage": "frontend_compatibility",
                                "code": "MISSING_FILE_UPLOAD_FIELD",
                                "message": f"file_upload.{field} is missing. Frontend may use default values.",
                            }
                        )
                    elif not isinstance(file_upload[field], list):
                        result["warnings"].append(
                            {
                                "stage": "frontend_compatibility",
                                "code": "INVALID_FILE_UPLOAD_FIELD_TYPE",
                                "message": f"file_upload.{field} should be an array",
                            }
                        )

                # Check fileUploadConfig
                if "fileUploadConfig" not in file_upload:
                    result["warnings"].append(
                        {
                            "stage": "frontend_compatibility",
                            "code": "MISSING_FILE_UPLOAD_CONFIG",
                            "message": "file_upload.fileUploadConfig is missing. Frontend may use default values.",
                        }
                    )

                # Check image config
                if file_upload.get("image", {}).get("enabled"):
                    image_config = file_upload.get("image", {})
                    if "transfer_methods" not in image_config or not isinstance(
                        image_config.get("transfer_methods"), list
                    ):
                        result["warnings"].append(
                            {
                                "stage": "frontend_compatibility",
                                "code": "MISSING_IMAGE_TRANSFER_METHODS",
                                "message": "file_upload.image.transfer_methods should be an array",
                            }
                        )

            # Check suggested_questions
            suggested_questions = features.get("suggested_questions")
            if suggested_questions is not None and not isinstance(
                suggested_questions, list
            ):
                result["errors"].append(
                    {
                        "stage": "frontend_compatibility",
                        "code": "INVALID_SUGGESTED_QUESTIONS_TYPE",
                        "message": "features.suggested_questions must be an array",
                    }
                )

        # Validate dependencies if present
        dependencies_list = data.get("dependencies", [])
        if dependencies_list:
            _validate_dependencies(dependencies_list, result)

        # Validate environment_variables and conversation_variables for workflow apps
        if app_mode_enum in {AppMode.ADVANCED_CHAT, AppMode.WORKFLOW}:
            workflow_data = data.get("workflow", {})

            environment_variables = workflow_data.get("environment_variables", [])
            if environment_variables:
                _validate_environment_variables(environment_variables, result)

            conversation_variables = workflow_data.get("conversation_variables", [])
            if conversation_variables:
                _validate_conversation_variables(conversation_variables, result)

            # Validate variable references in nodes
            if workflow_data:
                _validate_variable_references(
                    workflow_data, environment_variables, conversation_variables, result
                )

        # If we got here with no errors, validation passed
        if not result["errors"]:
            result["success"] = True

    except Exception as e:
        result["errors"].append(
            {"stage": "unexpected_error", "code": "VALIDATION_ERROR", "message": str(e)}
        )

    return result


def _validate_dependencies(dependencies: list[dict], result: dict[str, Any]) -> None:
    """Validate dependencies structure and format."""
    if not isinstance(dependencies, list):
        result["errors"].append(
            {
                "stage": "dependencies_validation",
                "code": "INVALID_DEPENDENCIES_TYPE",
                "message": "dependencies must be an array",
            }
        )
        return

    for idx, dep in enumerate(dependencies):
        if not isinstance(dep, dict):
            result["errors"].append(
                {
                    "stage": "dependencies_validation",
                    "code": "INVALID_DEPENDENCY_TYPE",
                    "message": f"Dependency at index {idx} must be a mapping",
                }
            )
            continue

        # Validate using PluginDependency schema if available
        if PluginDependency is not None:
            try:
                PluginDependency.model_validate(dep)
            except ValidationError as e:
                for error in e.errors():
                    field_path = ".".join(str(loc) for loc in error["loc"])
                    result["errors"].append(
                        {
                            "stage": "dependencies_validation",
                            "code": "DEPENDENCY_VALIDATION_ERROR",
                            "message": f"Dependency at index {idx}: {field_path} - {error['msg']}",
                            "details": {
                                "dependency_index": idx,
                                "field": field_path,
                                "error_type": error["type"],
                            },
                        }
                    )
        else:
            # Basic validation if PluginDependency is not available
            if "type" not in dep:
                result["errors"].append(
                    {
                        "stage": "dependencies_validation",
                        "code": "MISSING_DEPENDENCY_TYPE",
                        "message": f"Dependency at index {idx} is missing 'type' field",
                    }
                )
            if "value" not in dep:
                result["errors"].append(
                    {
                        "stage": "dependencies_validation",
                        "code": "MISSING_DEPENDENCY_VALUE",
                        "message": f"Dependency at index {idx} is missing 'value' field",
                    }
                )


def _validate_environment_variables(
    variables: list[dict], result: dict[str, Any]
) -> None:
    """Validate environment variables structure."""
    if not isinstance(variables, list):
        result["errors"].append(
            {
                "stage": "environment_variables_validation",
                "code": "INVALID_ENV_VARS_TYPE",
                "message": "environment_variables must be an array",
            }
        )
        return

    for idx, var in enumerate(variables):
        if not isinstance(var, dict):
            result["errors"].append(
                {
                    "stage": "environment_variables_validation",
                    "code": "INVALID_ENV_VAR_TYPE",
                    "message": f"Environment variable at index {idx} must be a mapping",
                }
            )
            continue

        # Check required fields
        required_fields = ["id", "name", "value_type"]
        for field in required_fields:
            if field not in var:
                result["errors"].append(
                    {
                        "stage": "environment_variables_validation",
                        "code": "MISSING_ENV_VAR_FIELD",
                        "message": f"Environment variable at index {idx} is missing required field '{field}'",
                    }
                )

        # Validate value_type
        if "value_type" in var:
            valid_types = ["string", "number", "secret"]
            if var["value_type"] not in valid_types:
                result["errors"].append(
                    {
                        "stage": "environment_variables_validation",
                        "code": "INVALID_ENV_VAR_VALUE_TYPE",
                        "message": f"Environment variable at index {idx} has invalid value_type: {var['value_type']}. Must be one of: {valid_types}",
                    }
                )


def _validate_conversation_variables(
    variables: list[dict], result: dict[str, Any]
) -> None:
    """Validate conversation variables structure."""
    if not isinstance(variables, list):
        result["errors"].append(
            {
                "stage": "conversation_variables_validation",
                "code": "INVALID_CONV_VARS_TYPE",
                "message": "conversation_variables must be an array",
            }
        )
        return

    for idx, var in enumerate(variables):
        if not isinstance(var, dict):
            result["errors"].append(
                {
                    "stage": "conversation_variables_validation",
                    "code": "INVALID_CONV_VAR_TYPE",
                    "message": f"Conversation variable at index {idx} must be a mapping",
                }
            )
            continue

        # Check required fields
        required_fields = ["id", "name", "value_type"]
        for field in required_fields:
            if field not in var:
                result["errors"].append(
                    {
                        "stage": "conversation_variables_validation",
                        "code": "MISSING_CONV_VAR_FIELD",
                        "message": f"Conversation variable at index {idx} is missing required field '{field}'",
                    }
                )

        # Validate value_type
        if "value_type" in var:
            valid_types = [
                "string",
                "number",
                "array[string]",
                "array[number]",
                "array[object]",
                "object",
            ]
            if var["value_type"] not in valid_types:
                result["errors"].append(
                    {
                        "stage": "conversation_variables_validation",
                        "code": "INVALID_CONV_VAR_VALUE_TYPE",
                        "message": f"Conversation variable at index {idx} has invalid value_type: {var['value_type']}. Must be one of: {valid_types}",
                    }
                )


def _validate_variable_references(
    workflow_data: dict,
    environment_variables: list[dict],
    conversation_variables: list[dict],
    result: dict[str, Any],
) -> None:
    """Validate that variable references in nodes exist in defined variables."""
    # Build sets of available variable IDs
    env_var_ids: set[str] = {
        var["id"]
        for var in environment_variables
        if isinstance(var, dict) and "id" in var
    }
    conv_var_ids: set[str] = {
        var["id"]
        for var in conversation_variables
        if isinstance(var, dict) and "id" in var
    }

    # Get all node IDs for node output references
    graph = workflow_data.get("graph", {})
    nodes = graph.get("nodes", [])
    node_ids: set[str] = {
        node["id"] for node in nodes if isinstance(node, dict) and "id" in node
    }

    # Check variable references in nodes
    for node in nodes:
        if not isinstance(node, dict):
            continue

        node_id = node.get("id", "unknown")
        node_data = node.get("data", {})

        # Recursively check for variable references in node data
        _check_variable_refs_recursive(
            node_data, node_id, env_var_ids, conv_var_ids, node_ids, result
        )


def _check_variable_refs_recursive(
    data: Any,
    node_id: str,
    env_var_ids: set[str],
    conv_var_ids: set[str],
    node_ids: set[str],
    result: dict[str, Any],
    path: str = "",
) -> None:
    """Recursively check variable references in node data."""
    import re

    # Pattern to match Dify's variable references: {{#node_id.variable#}}
    # This matches the actual format used by Dify (see variable_template_parser.py)
    var_pattern = re.compile(
        r"\{\{#([a-zA-Z0-9_]{1,50}(?:\.[a-zA-Z_][a-zA-Z0-9_]{0,29}){1,10})#\}\}"
    )

    if isinstance(data, str):
        # Find all variable references in the string
        matches = var_pattern.findall(data)
        for match in matches:
            # Parse the variable reference
            # Format: env.var_id, conversation.var_id, or node_id.output
            parts = match.strip().split(".", 1)
            if len(parts) < 2:
                # Invalid format, just warn
                result["warnings"].append(
                    {
                        "stage": "variable_reference_validation",
                        "code": "INVALID_VARIABLE_REFERENCE_FORMAT",
                        "message": f"Node '{node_id}'{path}: Invalid variable reference format: {{{{#{match}#}}}}",
                    }
                )
                continue

            prefix, var_name = parts

            # Check if the referenced variable exists
            if prefix == "env":
                # Check environment variable
                var_id = var_name.strip()
                if var_id not in env_var_ids:
                    result["errors"].append(
                        {
                            "stage": "variable_reference_validation",
                            "code": "UNDEFINED_ENVIRONMENT_VARIABLE",
                            "message": f"Node '{node_id}'{path}: References undefined environment variable: {{{{#{match}#}}}}",
                            "details": {
                                "node_id": node_id,
                                "variable_id": var_id,
                                "reference": match,
                            },
                        }
                    )
            elif prefix == "conversation":
                # Check conversation variable
                var_id = var_name.strip()
                if var_id not in conv_var_ids:
                    result["errors"].append(
                        {
                            "stage": "variable_reference_validation",
                            "code": "UNDEFINED_CONVERSATION_VARIABLE",
                            "message": f"Node '{node_id}'{path}: References undefined conversation variable: {{{{#{match}#}}}}",
                            "details": {
                                "node_id": node_id,
                                "variable_id": var_id,
                                "reference": match,
                            },
                        }
                    )
            else:
                # Assume it's a node output reference
                referenced_node_id = prefix.strip()
                if referenced_node_id not in node_ids:
                    result["errors"].append(
                        {
                            "stage": "variable_reference_validation",
                            "code": "UNDEFINED_NODE_REFERENCE",
                            "message": f"Node '{node_id}'{path}: References undefined node: {{{{#{match}#}}}}",
                            "details": {
                                "node_id": node_id,
                                "referenced_node_id": referenced_node_id,
                                "reference": match,
                            },
                        }
                    )

    elif isinstance(data, dict):
        # Recursively check dictionary values
        for key, value in data.items():
            new_path = f"{path}.{key}" if path else key
            _check_variable_refs_recursive(
                value, node_id, env_var_ids, conv_var_ids, node_ids, result, new_path
            )

    elif isinstance(data, list):
        # Recursively check list items
        for idx, item in enumerate(data):
            new_path = f"{path}[{idx}]"
            _check_variable_refs_recursive(
                item, node_id, env_var_ids, conv_var_ids, node_ids, result, new_path
            )

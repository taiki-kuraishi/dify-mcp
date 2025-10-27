"""
Dify Workflow YAML Validator

Validates Dify workflow DSL YAML without database dependencies.
Extracted from AppDslService.import_app() validation logic.
"""

from enum import StrEnum
from typing import Any

import yaml
from packaging import version as pkg_version

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
                {"stage": "content_check", "code": "EMPTY_CONTENT", "message": "Empty YAML content"}
            )
            return result

        # Parse YAML to validate format
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            result["errors"].append(
                {"stage": "yaml_parsing", "code": "YAML_SYNTAX_ERROR", "message": f"Invalid YAML format: {str(e)}"}
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

        # Validate and fix DSL version
        if not data.get("version"):
            data["version"] = "0.1.0"
        if not data.get("kind") or data.get("kind") != "app":
            data["kind"] = "app"

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
            current_ver = pkg_version.parse(CURRENT_DSL_VERSION)
            imported_ver = pkg_version.parse(imported_version)

            if imported_ver > current_ver:
                result["warnings"].append(
                    {
                        "stage": "version_check",
                        "code": "VERSION_NEWER",
                        "message": f"DSL version {imported_version} is newer than current {CURRENT_DSL_VERSION}. User confirmation may be required.",
                        "details": {
                            "imported_version": imported_version,
                            "current_version": CURRENT_DSL_VERSION,
                        },
                    }
                )
            elif imported_ver.major < current_ver.major:
                result["warnings"].append(
                    {
                        "stage": "version_check",
                        "code": "VERSION_MAJOR_MISMATCH",
                        "message": f"DSL version {imported_version} has different major version. User confirmation may be required.",
                        "details": {
                            "imported_version": imported_version,
                            "current_version": CURRENT_DSL_VERSION,
                        },
                    }
                )
            elif imported_ver.minor < current_ver.minor:
                result["warnings"].append(
                    {
                        "stage": "version_check",
                        "code": "VERSION_MINOR_OLDER",
                        "message": f"DSL version {imported_version} is older than current {CURRENT_DSL_VERSION}",
                        "details": {
                            "imported_version": imported_version,
                            "current_version": CURRENT_DSL_VERSION,
                        },
                    }
                )
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
                {"stage": "schema_validation", "code": "MISSING_APP_DATA", "message": "Missing app data in YAML content"}
            )
            return result

        # Check app mode
        app_mode = app_data.get("mode")
        if not app_mode:
            result["errors"].append(
                {"stage": "schema_validation", "code": "MISSING_APP_MODE", "message": "Missing app mode"}
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

            nodes = graph.get("nodes", [])
            edges = graph.get("edges", [])

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

                # Warn if width/height are missing (frontend calculates dynamically)
                if "width" not in node or "height" not in node:
                    result["warnings"].append(
                        {
                            "stage": "frontend_compatibility",
                            "code": "MISSING_NODE_DIMENSIONS",
                            "message": f"Node '{node_id}' is missing 'width' or 'height'. Frontend will calculate these dynamically.",
                        }
                    )

            # Basic edge validation
            node_ids = {node.get("id") for node in nodes if isinstance(node, dict) and "id" in node}
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
            if file_upload and isinstance(file_upload, dict) and file_upload.get("enabled"):
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
            if suggested_questions is not None and not isinstance(suggested_questions, list):
                result["errors"].append(
                    {
                        "stage": "frontend_compatibility",
                        "code": "INVALID_SUGGESTED_QUESTIONS_TYPE",
                        "message": "features.suggested_questions must be an array",
                    }
                )

        # If we got here with no errors, validation passed
        if not result["errors"]:
            result["success"] = True

    except Exception as e:
        result["errors"].append({"stage": "unexpected_error", "code": "VALIDATION_ERROR", "message": str(e)})

    return result

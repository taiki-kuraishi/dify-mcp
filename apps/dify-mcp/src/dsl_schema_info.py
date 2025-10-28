"""
Dify DSL Schema Information

Provides structured information about Dify DSL schema for MCP resources.
Extracts information dynamically from Dify source code where possible.
"""

from typing import Any
from .schemas import NODE_SCHEMAS

def get_node_schema_details(node_type: str) -> dict[str, Any]:
    """Get detailed schema information for a specific node type."""
    if node_type not in NODE_SCHEMAS:
        return {
            "error": f"Unknown node type: {node_type}",
            "available_types": list(NODE_SCHEMAS.keys()),
        }

    schema = NODE_SCHEMAS[node_type]
    if schema is None:
        return {
            "type": node_type,
            "schema_available": False,
            "message": "Schema validation is unavailable for this node type (missing dependencies)",
            "required_fields": ["id", "type", "title"],
        }

    # Extract field information from Pydantic schema
    try:
        fields_info = {}
        if hasattr(schema, "model_fields"):
            for field_name, field_info in schema.model_fields.items():
                field_data = {
                    "required": field_info.is_required(),
                    "type": str(field_info.annotation)
                    if field_info.annotation
                    else "Any",
                }
                if field_info.description:
                    field_data["description"] = field_info.description
                if field_info.default is not None:
                    field_data["default"] = str(field_info.default)

                fields_info[field_name] = field_data

        return {
            "type": node_type,
            "schema_available": True,
            "schema_class": schema.__name__,
            "fields": fields_info,
            "example_structure": {
                "id": "node_id",
                "position": {"x": 100, "y": 100},
                "data": {
                    "type": node_type,
                    "title": "Node Title",
                    # Additional fields depend on node type
                },
            },
        }
    except Exception as e:
        return {
            "type": node_type,
            "schema_available": True,
            "error": f"Failed to extract schema details: {str(e)}",
        }

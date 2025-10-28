"""
Node Builder Classes

Provides builder pattern interfaces for constructing Dify workflow nodes.
Each builder validates node data using Dify's internal Pydantic schemas.
"""

from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4
from .schemas import NODE_SCHEMAS

class NodeBuilderError(Exception):
    """Error during node construction."""
    pass

class NodeBuilder(ABC):
    """
    Base class for node builders.

    Provides common functionality for building workflow nodes:
    - Node ID generation
    - Position management
    - Data validation using Dify schemas
    - Conversion to DSL format
    """

    def __init__(
        self, node_id: str | None = None, title: str = "", x: float = 0, y: float = 0
    ):
        """
        Initialize node builder.

        Args:
            node_id: Unique node ID (auto-generated if not provided)
            title: Node title
            x: X coordinate on canvas
            y: Y coordinate on canvas
        """
        self.node_id = node_id or str(uuid4())[:13]  # Dify uses 13-char IDs
        self.x = x
        self.y = y
        self.data: dict[str, Any] = {
            "type": self.get_node_type(),
            "title": title or self.get_default_title(),
        }

    @abstractmethod
    def get_node_type(self) -> str:
        """Return the node type identifier (e.g., 'start', 'llm', 'end')."""
        pass

    @abstractmethod
    def get_default_title(self) -> str:
        """Return default title for this node type."""
        pass

    def set_position(self, x: float, y: float) -> "NodeBuilder":
        """
        Set node position on canvas.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Self for method chaining
        """
        self.x = x
        self.y = y
        return self

    def validate(self) -> None:
        """
        Validate node data using Dify's internal schema.

        Raises:
            NodeBuilderError: If validation fails
        """
        node_type = self.get_node_type()
        schema_class = NODE_SCHEMAS.get(node_type)

        if schema_class is None:
            raise NodeBuilderError(
                f"Schema validation unavailable for node type '{node_type}'"
            )

        try:
            schema_class.model_validate(self.data)
        except Exception as e:
            raise NodeBuilderError(
                f"Node validation failed for '{node_type}': {str(e)}"
            ) from e

    def build(self) -> dict[str, Any]:
        """
        Build the final node structure.

        Returns:
            Dictionary representing the complete node for DSL

        Raises:
            NodeBuilderError: If validation fails
        """
        self.validate()

        return {
            "id": self.node_id,
            "data": self.data,
            "position": {"x": self.x, "y": self.y},
            "type": "custom",  # Dify uses 'custom' for all nodes in DSL
            "sourcePosition": "right",
            "targetPosition": "left",
        }


# ============================================================================
# Start Node Builder
# ============================================================================


class StartNodeBuilder(NodeBuilder):
    """Builder for Start nodes."""

    def get_node_type(self) -> str:
        return "start"

    def get_default_title(self) -> str:
        return "開始"

    def add_text_input(
        self,
        variable: str,
        label: str,
        required: bool = True,
        default: str = "",
        max_length: int | None = None,
        placeholder: str = "",
    ) -> "StartNodeBuilder":
        """
        Add a text input variable.

        Args:
            variable: Variable name
            label: Display label
            required: Whether variable is required
            default: Default value
            max_length: Maximum length
            placeholder: Placeholder text

        Returns:
            Self for method chaining
        """
        if "variables" not in self.data:
            self.data["variables"] = []

        var_config = {
            "variable": variable,
            "label": label,
            "type": "text-input",
            "required": required,
            "default": default,
            "placeholder": placeholder,
            "options": [],
        }

        if max_length is not None:
            var_config["max_length"] = max_length

        self.data["variables"].append(var_config)
        return self

    def add_paragraph(
        self,
        variable: str,
        label: str,
        required: bool = False,
        default: str = "",
        placeholder: str = "",
    ) -> "StartNodeBuilder":
        """Add a paragraph (multiline text) input variable."""
        if "variables" not in self.data:
            self.data["variables"] = []

        self.data["variables"].append(
            {
                "variable": variable,
                "label": label,
                "type": "paragraph",
                "required": required,
                "default": default,
                "placeholder": placeholder,
                "options": [],
            }
        )
        return self

    def add_select(
        self,
        variable: str,
        label: str,
        options: list[str],
        required: bool = False,
        default: str = "",
    ) -> "StartNodeBuilder":
        """Add a select (dropdown) input variable."""
        if "variables" not in self.data:
            self.data["variables"] = []

        self.data["variables"].append(
            {
                "variable": variable,
                "label": label,
                "type": "select",
                "required": required,
                "default": default,
                "options": options,
            }
        )
        return self


# ============================================================================
# End Node Builder
# ============================================================================


class EndNodeBuilder(NodeBuilder):
    """Builder for End nodes."""

    def get_node_type(self) -> str:
        return "end"

    def get_default_title(self) -> str:
        return "終了"

    def __init__(
        self, node_id: str | None = None, title: str = "", x: float = 0, y: float = 0
    ):
        super().__init__(node_id, title, x, y)
        self.data["outputs"] = []

    def add_output(
        self, variable_name: str, value_selector: list[str]
    ) -> "EndNodeBuilder":
        """
        Add an output variable.

        Args:
            variable_name: Output variable name
            value_selector: Path to source value (e.g., ["llm_node", "text"])

        Returns:
            Self for method chaining
        """
        self.data["outputs"].append(
            {
                "variable": variable_name,
                "value_selector": value_selector,
            }
        )
        return self


# ============================================================================
# Answer Node Builder
# ============================================================================


class AnswerNodeBuilder(NodeBuilder):
    """Builder for Answer nodes (used in advanced-chat mode)."""

    def get_node_type(self) -> str:
        return "answer"

    def get_default_title(self) -> str:
        return "直接応答"

    def set_answer(self, answer_template: str) -> "AnswerNodeBuilder":
        """
        Set the answer template.

        Args:
            answer_template: Answer text with variable references (e.g., "Result: {{#llm.text#}}")

        Returns:
            Self for method chaining
        """
        self.data["answer"] = answer_template
        return self


# ============================================================================
# Template Transform Node Builder
# ============================================================================


class TemplateTransformNodeBuilder(NodeBuilder):
    """Builder for Template Transform nodes."""

    def get_node_type(self) -> str:
        return "template-transform"

    def get_default_title(self) -> str:
        return "テンプレート変換"

    def __init__(
        self, node_id: str | None = None, title: str = "", x: float = 0, y: float = 0
    ):
        super().__init__(node_id, title, x, y)
        self.data["variables"] = []
        self.data["template"] = ""

    def add_variable(
        self, variable_name: str, value_selector: list[str]
    ) -> "TemplateTransformNodeBuilder":
        """
        Add a variable to use in the template.

        Args:
            variable_name: Variable name to use in template
            value_selector: Path to source value (e.g., ["start", "user_name"])

        Returns:
            Self for method chaining
        """
        self.data["variables"].append(
            {
                "variable": variable_name,
                "value_selector": value_selector,
            }
        )
        return self

    def set_template(self, template: str) -> "TemplateTransformNodeBuilder":
        """
        Set the Jinja2 template string.

        Args:
            template: Jinja2 template (e.g., "Hello {{name}}!")

        Returns:
            Self for method chaining
        """
        self.data["template"] = template
        return self


# ============================================================================
# LLM Node Builder
# ============================================================================


class LLMNodeBuilder(NodeBuilder):
    """Builder for LLM nodes."""

    def get_node_type(self) -> str:
        return "llm"

    def get_default_title(self) -> str:
        return "LLM"

    def __init__(
        self, node_id: str | None = None, title: str = "", x: float = 0, y: float = 0
    ):
        super().__init__(node_id, title, x, y)
        self.data["model"] = {}
        self.data["prompt_template"] = []
        self.data["context"] = {"enabled": False}
        self.data["vision"] = {"enabled": False}
        self.data["prompt_config"] = {"jinja2_variables": []}

    def set_model(
        self,
        provider: str,
        name: str,
        mode: str = "chat",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> "LLMNodeBuilder":
        """
        Configure the LLM model.

        Args:
            provider: Model provider (e.g., "openai", "anthropic")
            name: Model name (e.g., "gpt-4", "claude-3-sonnet")
            mode: "chat" or "completion"
            temperature: Temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional completion parameters

        Returns:
            Self for method chaining
        """
        completion_params = {"temperature": temperature}
        if max_tokens is not None:
            completion_params["max_tokens"] = max_tokens
        completion_params.update(kwargs)

        self.data["model"] = {
            "provider": f"langgenius/{provider}/{provider}",  # Dify format
            "name": name,
            "mode": mode,
            "completion_params": completion_params,
        }
        return self

    def add_system_prompt(self, text: str) -> "LLMNodeBuilder":
        """
        Add a system prompt.

        Args:
            text: System prompt text

        Returns:
            Self for method chaining
        """
        self.data["prompt_template"].append(
            {
                "role": "system",
                "text": text,
                "edition_type": "basic",
            }
        )
        return self

    def add_user_prompt(self, text: str) -> "LLMNodeBuilder":
        """
        Add a user prompt.

        Args:
            text: User prompt text (can include variable references like {{#node.field#}})

        Returns:
            Self for method chaining
        """
        self.data["prompt_template"].append(
            {
                "role": "user",
                "text": text,
            }
        )
        return self

    def set_context(
        self, enabled: bool = True, variable_selector: list[str] | None = None
    ) -> "LLMNodeBuilder":
        """
        Configure context input.

        Args:
            enabled: Whether to enable context
            variable_selector: Path to context variable (e.g., ["start", "context"])

        Returns:
            Self for method chaining
        """
        self.data["context"] = {
            "enabled": enabled,
            "variable_selector": variable_selector,
        }
        return self


# ============================================================================
# Helper Functions
# ============================================================================


def create_start_node(
    node_id: str | None = None, title: str = "開始", x: float = 80, y: float = 282
) -> StartNodeBuilder:
    """
    Create a start node builder with default configuration.

    Args:
        node_id: Node ID (auto-generated if not provided)
        title: Node title
        x: X coordinate
        y: Y coordinate

    Returns:
        StartNodeBuilder instance
    """
    return StartNodeBuilder(node_id, title, x, y)


def create_end_node(
    node_id: str | None = None, title: str = "終了", x: float = 756, y: float = 300
) -> EndNodeBuilder:
    """Create an end node builder with default configuration."""
    return EndNodeBuilder(node_id, title, x, y)


def create_llm_node(
    node_id: str | None = None, title: str = "LLM", x: float = 382, y: float = 282
) -> LLMNodeBuilder:
    """Create an LLM node builder with default configuration."""
    return LLMNodeBuilder(node_id, title, x, y)


def create_template_node(
    node_id: str | None = None,
    title: str = "テンプレート変換",
    x: float = 0,
    y: float = 0,
) -> TemplateTransformNodeBuilder:
    """Create a template transform node builder with default configuration."""
    return TemplateTransformNodeBuilder(node_id, title, x, y)


def create_answer_node(
    node_id: str | None = None, title: str = "直接応答", x: float = 0, y: float = 0
) -> AnswerNodeBuilder:
    """Create an answer node builder with default configuration."""
    return AnswerNodeBuilder(node_id, title, x, y)


# ============================================================================
# HTTP Request Node Builder
# ============================================================================


class HttpRequestNodeBuilder(NodeBuilder):
    """Builder for HTTP Request nodes."""

    def get_node_type(self) -> str:
        return "http-request"

    def get_default_title(self) -> str:
        return "HTTP リクエスト"

    def __init__(
        self, node_id: str | None = None, title: str = "", x: float = 0, y: float = 0
    ):
        super().__init__(node_id, title, x, y)
        self.data["method"] = "GET"
        self.data["url"] = ""
        self.data["authorization"] = {"type": "no-auth"}
        self.data["headers"] = "{}"
        self.data["params"] = "{}"
        self.data["body"] = None
        self.data["timeout"] = None

    def set_method(self, method: str) -> "HttpRequestNodeBuilder":
        """
        Set HTTP method.

        Args:
            method: HTTP method ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")

        Returns:
            Self for method chaining
        """
        self.data["method"] = method.upper()
        return self

    def set_url(self, url: str) -> "HttpRequestNodeBuilder":
        """
        Set request URL.

        Args:
            url: URL string (can include variable references like {{#node.field#}})

        Returns:
            Self for method chaining
        """
        self.data["url"] = url
        return self

    def set_authorization(
        self, auth_type: str = "no-auth", config: dict[str, Any] | None = None
    ) -> "HttpRequestNodeBuilder":
        """
        Set authorization configuration.

        Args:
            auth_type: "no-auth" or "api-key"
            config: Authorization config dict with:
                - type: "basic", "bearer", or "custom"
                - api_key: API key value (str)
                - header: Header name for custom type (str, optional)

        Returns:
            Self for method chaining
        """
        self.data["authorization"] = {"type": auth_type}
        if config:
            self.data["authorization"]["config"] = config
        return self

    def set_headers(self, headers: dict[str, str] | str) -> "HttpRequestNodeBuilder":
        """
        Set request headers.

        Args:
            headers: Headers as dict or JSON string

        Returns:
            Self for method chaining
        """
        import json

        if isinstance(headers, dict):
            self.data["headers"] = json.dumps(headers)
        else:
            self.data["headers"] = headers
        return self

    def set_params(self, params: dict[str, str] | str) -> "HttpRequestNodeBuilder":
        """
        Set query parameters.

        Args:
            params: Parameters as dict or JSON string

        Returns:
            Self for method chaining
        """
        import json

        if isinstance(params, dict):
            self.data["params"] = json.dumps(params)
        else:
            self.data["params"] = params
        return self

    def set_body(
        self, body_type: str = "json", data: list[dict] | None = None
    ) -> "HttpRequestNodeBuilder":
        """
        Set request body.

        Args:
            body_type: "none", "form-data", "x-www-form-urlencoded", "raw-text", "json", "binary"
            data: List of body data items, each with:
                - key: Field name (str)
                - type: "file" or "text" (str)
                - value: Field value (str)

        Returns:
            Self for method chaining
        """
        self.data["body"] = {"type": body_type, "data": data or []}
        return self


def create_http_request_node(
    node_id: str | None = None,
    title: str = "HTTP リクエスト",
    x: float = 0,
    y: float = 0,
) -> HttpRequestNodeBuilder:
    """Create an HTTP request node builder with default configuration."""
    return HttpRequestNodeBuilder(node_id, title, x, y)


# ============================================================================
# Code Node Builder
# ============================================================================


class CodeNodeBuilder(NodeBuilder):
    """Builder for Code nodes."""

    def get_node_type(self) -> str:
        return "code"

    def get_default_title(self) -> str:
        return "コード実行"

    def __init__(
        self, node_id: str | None = None, title: str = "", x: float = 0, y: float = 0
    ):
        super().__init__(node_id, title, x, y)
        self.data["variables"] = []
        self.data["code_language"] = "python3"
        self.data["code"] = ""
        self.data["outputs"] = {}

    def set_language(self, language: str = "python3") -> "CodeNodeBuilder":
        """
        Set code language.

        Args:
            language: "python3" or "javascript"

        Returns:
            Self for method chaining
        """
        self.data["code_language"] = language
        return self

    def set_code(self, code: str) -> "CodeNodeBuilder":
        """
        Set code to execute.

        Args:
            code: Code string

        Returns:
            Self for method chaining
        """
        self.data["code"] = code
        return self

    def add_variable(
        self, variable_name: str, value_selector: list[str]
    ) -> "CodeNodeBuilder":
        """
        Add an input variable.

        Args:
            variable_name: Variable name to use in code
            value_selector: Path to source value (e.g., ["start", "input"])

        Returns:
            Self for method chaining
        """
        self.data["variables"].append(
            {
                "variable": variable_name,
                "value_selector": value_selector,
            }
        )
        return self

    def add_output(
        self, output_name: str, output_type: str = "string"
    ) -> "CodeNodeBuilder":
        """
        Add an output variable.

        Args:
            output_name: Output variable name
            output_type: Output type ("string", "number", "object", "array[string]", etc.)

        Returns:
            Self for method chaining
        """
        self.data["outputs"][output_name] = {"type": output_type}
        return self


def create_code_node(
    node_id: str | None = None, title: str = "コード実行", x: float = 0, y: float = 0
) -> CodeNodeBuilder:
    """Create a code node builder with default configuration."""
    return CodeNodeBuilder(node_id, title, x, y)


# ============================================================================
# If-Else Node Builder
# ============================================================================


class IfElseNodeBuilder(NodeBuilder):
    """Builder for If-Else nodes."""

    def get_node_type(self) -> str:
        return "if-else"

    def get_default_title(self) -> str:
        return "IF/ELSE"

    def __init__(
        self, node_id: str | None = None, title: str = "", x: float = 0, y: float = 0
    ):
        super().__init__(node_id, title, x, y)
        self.data["cases"] = []

    def add_case(
        self,
        case_id: str,
        logical_operator: str = "and",
        conditions: list[dict] | None = None,
    ) -> "IfElseNodeBuilder":
        """
        Add a conditional case.

        Args:
            case_id: Unique case ID
            logical_operator: "and" or "or"
            conditions: List of condition dicts, each with:
                - variable_selector: Path to variable (list[str])
                - comparison_operator: Operator like "contains", "=", ">", "is", etc.
                - value: Comparison value (str or bool or list)

        Returns:
            Self for method chaining
        """
        self.data["cases"].append(
            {
                "case_id": case_id,
                "logical_operator": logical_operator,
                "conditions": conditions or [],
            }
        )
        return self

    def add_condition_to_case(
        self,
        case_id: str,
        variable_selector: list[str],
        comparison_operator: str,
        value: Any,
    ) -> "IfElseNodeBuilder":
        """
        Add a condition to an existing case.

        Args:
            case_id: Case ID to add condition to
            variable_selector: Path to variable (e.g., ["start", "score"])
            comparison_operator: Operator like "contains", "=", ">", etc.
            value: Comparison value

        Returns:
            Self for method chaining
        """
        for case in self.data["cases"]:
            if case["case_id"] == case_id:
                case["conditions"].append(
                    {
                        "variable_selector": variable_selector,
                        "comparison_operator": comparison_operator,
                        "value": value,
                    }
                )
                break
        return self


def create_if_else_node(
    node_id: str | None = None, title: str = "IF/ELSE", x: float = 0, y: float = 0
) -> IfElseNodeBuilder:
    """Create an if-else node builder with default configuration."""
    return IfElseNodeBuilder(node_id, title, x, y)

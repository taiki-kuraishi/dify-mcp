"""Unit tests for validator module"""

import pytest

from src.validator import (
    CURRENT_DSL_VERSION,
    DSL_MAX_SIZE,
    AppMode,
    validate_workflow_yaml,
)


class TestValidateWorkflowYaml:
    """Tests for validate_workflow_yaml function"""

    def test_valid_workflow_yaml(self):
        """Test validation with a valid workflow YAML"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test Workflow
workflow:
  graph:
    nodes:
      - id: start_node
        data:
          type: start
          title: Start
        position:
          x: 100
          y: 100
        width: 240
        height: 80
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is True
        assert len(result["errors"]) == 0
        assert result["info"]["dsl_version"] == "0.4.0"
        assert result["info"]["app_mode"] == "workflow"
        assert result["info"]["node_count"] == 1
        assert result["info"]["edge_count"] == 0

    def test_empty_content(self):
        """Test validation with empty content"""
        result = validate_workflow_yaml("")

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "EMPTY_CONTENT"
        assert result["errors"][0]["stage"] == "content_check"

    def test_file_too_large(self):
        """Test validation with content exceeding size limit"""
        large_content = "x" * (DSL_MAX_SIZE + 1)
        result = validate_workflow_yaml(large_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "FILE_TOO_LARGE"
        assert result["errors"][0]["stage"] == "size_check"

    def test_invalid_yaml_syntax(self):
        """Test validation with invalid YAML syntax"""
        invalid_yaml = """
version: "0.4.0
kind: app
app:
  mode: workflow
  - invalid
    syntax here
"""
        result = validate_workflow_yaml(invalid_yaml)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "YAML_SYNTAX_ERROR"
        assert result["errors"][0]["stage"] == "yaml_parsing"

    def test_yaml_not_dict(self):
        """Test validation when YAML content is not a dictionary"""
        yaml_content = "- item1\n- item2"
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "INVALID_YAML_TYPE"
        assert result["errors"][0]["stage"] == "yaml_parsing"

    def test_invalid_version_type(self):
        """Test validation with non-string version"""
        yaml_content = """
version: 0.4
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes: []
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "INVALID_VERSION_TYPE"
        assert result["errors"][0]["stage"] == "version_check"

    def test_invalid_version_format(self):
        """Test validation with invalid version format"""
        yaml_content = """
version: "not-a-version"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes: []
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "INVALID_VERSION_FORMAT"

    def test_missing_app_data(self):
        """Test validation when app data is missing"""
        yaml_content = """
version: "0.4.0"
kind: app
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "MISSING_APP_DATA"

    def test_missing_app_mode(self):
        """Test validation when app mode is missing"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  name: Test
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "MISSING_APP_MODE"

    def test_invalid_app_mode(self):
        """Test validation with invalid app mode"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: invalid_mode
  name: Test
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "INVALID_APP_MODE"

    def test_missing_workflow_data(self):
        """Test validation when workflow data is missing for workflow mode"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert len(result["errors"]) == 1
        assert result["errors"][0]["code"] == "MISSING_WORKFLOW_DATA"

    def test_invalid_graph_type(self):
        """Test validation when graph is not a dict"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph: "invalid"
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INVALID_GRAPH_TYPE" for e in result["errors"])

    def test_invalid_nodes_type(self):
        """Test validation when nodes is not a list"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes: "invalid"
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INVALID_NODES_TYPE" for e in result["errors"])

    def test_invalid_edges_type(self):
        """Test validation when edges is not a list"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes: []
    edges: "invalid"
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INVALID_EDGES_TYPE" for e in result["errors"])

    def test_node_missing_id(self):
        """Test validation when a node is missing an id"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - data:
          type: start
        position:
          x: 0
          y: 0
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "MISSING_NODE_ID" for e in result["errors"])

    def test_node_missing_data(self):
        """Test validation when a node is missing data"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        position:
          x: 0
          y: 0
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "MISSING_NODE_DATA" for e in result["errors"])

    def test_node_missing_position(self):
        """Test validation when a node is missing position"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "MISSING_NODE_POSITION" for e in result["errors"])

    def test_node_invalid_position_type(self):
        """Test validation when position is not a dict"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
        position: "invalid"
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INVALID_NODE_POSITION_TYPE" for e in result["errors"])

    def test_node_incomplete_position(self):
        """Test validation when position is missing x or y"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
        position:
          x: 100
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INCOMPLETE_NODE_POSITION" for e in result["errors"])

    def test_node_invalid_position_values(self):
        """Test validation when position x or y are not numeric"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
        position:
          x: "100"
          y: 100
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INVALID_NODE_POSITION_VALUES" for e in result["errors"])

    def test_edge_missing_source(self):
        """Test validation when edge is missing source"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
        position:
          x: 0
          y: 0
    edges:
      - target: node1
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "MISSING_EDGE_SOURCE" for e in result["errors"])

    def test_edge_missing_target(self):
        """Test validation when edge is missing target"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
        position:
          x: 0
          y: 0
    edges:
      - source: node1
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "MISSING_EDGE_TARGET" for e in result["errors"])

    def test_edge_invalid_source(self):
        """Test validation when edge references non-existent source node"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
        position:
          x: 0
          y: 0
    edges:
      - source: nonexistent
        target: node1
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INVALID_EDGE_SOURCE" for e in result["errors"])

    def test_edge_invalid_target(self):
        """Test validation when edge references non-existent target node"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: workflow
  name: Test
workflow:
  graph:
    nodes:
      - id: node1
        data:
          type: start
        position:
          x: 0
          y: 0
    edges:
      - source: node1
        target: nonexistent
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "INVALID_EDGE_TARGET" for e in result["errors"])

    def test_chat_app_missing_model_config(self):
        """Test validation for chat app without model_config"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: chat
  name: Test Chat
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is False
        assert any(e["code"] == "MISSING_MODEL_CONFIG" for e in result["errors"])

    def test_chat_app_with_model_config(self):
        """Test validation for chat app with model_config"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: chat
  name: Test Chat
model_config:
  provider: openai
  model: gpt-3.5-turbo
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is True
        assert result["info"]["app_mode"] == "chat"

    def test_advanced_chat_mode(self):
        """Test validation for advanced-chat mode"""
        yaml_content = """
version: "0.4.0"
kind: app
app:
  mode: advanced-chat
  name: Test Advanced Chat
workflow:
  graph:
    nodes:
      - id: start
        data:
          type: start
          title: Start
        position:
          x: 0
          y: 0
    edges: []
"""
        result = validate_workflow_yaml(yaml_content)

        assert result["success"] is True
        assert result["info"]["app_mode"] == "advanced-chat"


class TestAppMode:
    """Tests for AppMode enum"""

    def test_app_mode_values(self):
        """Test that AppMode has all expected values"""
        expected_modes = ["completion", "chat", "agent-chat", "advanced-chat", "workflow"]
        actual_modes = [mode.value for mode in AppMode]

        assert set(expected_modes) == set(actual_modes)

    def test_app_mode_conversion(self):
        """Test converting string to AppMode"""
        assert AppMode("workflow") == AppMode.WORKFLOW
        assert AppMode("chat") == AppMode.CHAT
        assert AppMode("completion") == AppMode.COMPLETION

    def test_app_mode_invalid_value(self):
        """Test that invalid value raises ValueError"""
        with pytest.raises(ValueError):
            AppMode("invalid_mode")


class TestConstants:
    """Tests for module constants"""

    def test_current_dsl_version(self):
        """Test that CURRENT_DSL_VERSION is properly set"""
        assert isinstance(CURRENT_DSL_VERSION, str)
        assert len(CURRENT_DSL_VERSION) > 0

    def test_dsl_max_size(self):
        """Test that DSL_MAX_SIZE is properly set"""
        assert DSL_MAX_SIZE == 10 * 1024 * 1024
        assert isinstance(DSL_MAX_SIZE, int)

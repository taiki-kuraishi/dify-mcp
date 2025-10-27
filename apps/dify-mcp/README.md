# Dify Workflow MCP Server

Model Context Protocol (MCP) server for validating Dify workflow DSL YAML files.

## Features

- ✅ **Validates Dify workflow YAML** without requiring database
- ✅ **Structured error messages** optimized for LLM consumption
- ✅ **Version compatibility checking** for DSL versions
- ✅ **Complete workflow structure validation** (nodes, edges, schema)
- ✅ **Based on official Dify validation logic** from `AppDslService`

## Tools Provided

### `validate_dify_workflow`

Validates a Dify workflow YAML file.

**Parameters:**

- `yaml_content` (string): Complete YAML content of the workflow

**Returns:**

```json
{
  "success": boolean,
  "errors": [...],
  "warnings": [...],
  "info": {
    "dsl_version": "string",
    "app_mode": "string",
    "node_count": number,
    "edge_count": number
  }
}
```

### `get_dify_dsl_version`

Returns the current supported DSL version (e.g., "0.4.0").

### `get_supported_app_modes`

Returns list of supported app modes.

## Installation

This MCP server should be installed within the parent dify-mcp project:

```bash
# From the dify-mcp root directory
cd dify-workflow-mcp
uv sync
```

## Usage

### Development Mode (with Inspector)

```bash
uv run fastmcp dev src/dify_workflow_mcp/server.py
```

Opens MCP Inspector at `http://localhost:6274`.

### Claude Desktop Integration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dify-workflow-validator": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/dify-workflow-mcp",
        "run",
        "fastmcp",
        "run",
        "src/dify_workflow_mcp/server.py"
      ]
    }
  }
}
```

**Config location:**

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`

## Testing

The test script validates workflows using sample files from the dify submodule:

```bash
# From the dify-workflow-mcp directory
uv run python test_mcp.py
```

Note: The dify submodule must be initialized in the parent directory for tests to access sample workflow files.

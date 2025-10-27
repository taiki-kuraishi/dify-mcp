"""
HTTP Server for Dify Workflow MCP Server

Serves the MCP server over HTTP using Streamable HTTP transport.
This allows clients to connect via Streamable HTTP.
"""


from .mcp import fast_mcp

if __name__ == "__main__":
    fast_mcp.run(transport="http", host="0.0.0.0", port=8000)

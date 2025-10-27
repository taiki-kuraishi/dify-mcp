"""Entry point for running the Dify Workflow MCP server."""

from .mcp import fast_mcp


def main() -> None:
    """Main entry point for the dify-mcp command."""
    fast_mcp.run()


if __name__ == "__main__":
    main()

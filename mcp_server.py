"""Entry point for the STDIO MCP server used by Codex CLI."""

from app.mcp.server import create_server
if __name__ == "__main__":
    create_server().run()

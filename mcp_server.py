"""Compatibility entry point for the local STDIO MCP transport."""

from app.mcp.stdio import run_stdio


if __name__ == "__main__":
    run_stdio()

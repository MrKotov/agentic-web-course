"""A minimal MCP client, enough to grade a student's server over stdio."""

from .client import McpError, McpStdioClient, ServerLaunch, load_launch_manifest

__all__ = ["McpError", "McpStdioClient", "ServerLaunch", "load_launch_manifest"]

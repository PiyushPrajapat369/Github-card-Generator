"""
Agent orchestrator definition using Google's Agent Development Kit (ADK).
Connects an Agent to a local FastMCP server using stdio transport parameters.
"""

import os
import sys
from google.adk.agents import Agent
from mcp import StdioServerParameters

# Highly resilient imports supporting different versions of google-adk
try:
    from google.adk.tools.mcp_tool import McpToolset
except ImportError:
    try:
        from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset as McpToolset
    except ImportError:
        McpToolset = None

try:
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
except ImportError:
    try:
        from google.adk.tools.mcp_tool.mcp_toolset import StdioConnectionParams
    except ImportError:
        StdioConnectionParams = None

# Define the absolute path to the local FastMCP server file
MCP_SERVER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")

# Configure StdioServerParameters to launch the local FastMCP server
# Using sys.executable guarantees it executes in the same virtualenv/environment
server_params = StdioServerParameters(
    command=sys.executable,
    args=[MCP_SERVER_PATH]
)

# Connect to the local MCP server using stdio transport
if StdioConnectionParams is not None and McpToolset is not None:
    mcp_tools = McpToolset(
        connection_params=StdioConnectionParams(
            server_params=server_params,
            timeout=60
        )
    )
else:
    # Fail-safe empty list if imports failed (to keep backend working in direct tool mode)
    mcp_tools = []

# Custom system instructions detailing strict sequence execution and persona
SYSTEM_INSTRUCTION = (
    "You are a GitHub profile analyst and dev card generator. "
    "When a user gives you a GitHub username, you ALWAYS follow this exact sequence: "
    "first call scrape_github, then analyze_profile with the result, "
    "then generate_card_html with all three inputs, then save_card. Never skip steps. "
    "Be enthusiastic about developers' work. If the profile is private or doesn't exist, say so clearly."
)

# Initialize the ADK Agent utilizing the MCP tools
github_card_agent = Agent(
    name="github_card_agent",
    model="gemini-2.5-flash",
    instruction=SYSTEM_INSTRUCTION,
    tools=[mcp_tools] if isinstance(mcp_tools, McpToolset) else mcp_tools
)

# Export aliases for compatibility and user requirements
root_agent = github_card_agent

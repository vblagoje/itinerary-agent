# SPDX-FileCopyrightText: 2022-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

### Overview
# This script shows how to use multiple MCP Servers in combination with the **Haystack Agent**
# and **OpenAI's Chat Generator** to create comprehensive travel itineraries.
# It combines:
# - Google Maps for location search and navigation
# - Weather data for activity planning
# - User preferences storage for personalization
# - Brave Search for additional context and information
# - A system message to guide the agent's behavior and capabilities

# ---

# ### 🔧 Step 1: Start the Required MCP Servers

# 1. Google Maps MCP Server (port 8100):
# ```bash
# docker run -it --rm -p 8100:8100 \
#   -e GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY \
#   supercorp/supergateway \
#   --stdio "npx -y @modelcontextprotocol/server-google-maps" \
#   --port 8100
# ```

# 2. Weather MCP Server (port 8101):
# ```bash
# docker run -it --rm -p 8101:8101 \
#   -e OPENWEATHER_API_KEY=$OPENWEATHER_API_KEY \
#   supercorp/supergateway \
#   --stdio "npx -y @vblagoje/openweather-mcp" \
#   --port 8101
# ```

# 3. Qdrant MCP Server for preferences (port 8102):
# ```bash
# docker run -p 8102:8000 \
#   -e QDRANT_URL="Your Qdrant URL remote or local" \
#   -e QDRANT_API_KEY="<your-qdrant-api-key>" \
#   -e COLLECTION_NAME="user-preferences" \
#   -e TOOL_FIND_DESCRIPTION="Search for user's stored preferences and personal information including food preferences, favorite activities, travel style, dietary restrictions, and general likes/dislikes" \
#   mcp-server-qdrant
# ```

# 4. Set BRAVE_API_KEY as we will use Brave Search via MCP Stdio Server directly
# export BRAVE_API_KEY="your_brave_api_key"
# ---

# ### ⚙️ Step 2: Configure Langfuse Tracing (Optional)

# To enable tracing with Langfuse:
# 1. Install the Langfuse Haystack integration:
#    ```bash
#    pip install langfuse-haystack
#    ```
# 2. Set the following environment variables BEFORE running the script:
#    ```bash
#    export LANGFUSE_SECRET_KEY="your-langfuse-secret-key"
#    export LANGFUSE_PUBLIC_KEY="your-langfuse-public-key"
#    export HAYSTACK_CONTENT_TRACING_ENABLED="true"
#    export LANGFUSE_HOST=https://us.cloud.langfuse.com or another host where your Langfuse project is hosted
#    ```
#    You can get the keys from your Langfuse project settings.
#    Setting `HAYSTACK_CONTENT_TRACING_ENABLED` to `true` ensures Haystack tracing is enabled.

# ---

# ### 🕵️ Step 3: Available Tools

# The agent has access to:
# - Maps tools: geocoding, place search, directions, etc.
# - Weather tools: current and forecast weather
# - Preferences: store and retrieve user preferences
# - Brave Search: for additional context and real-time information

# ---

# ### ▶️ Step 4: Run the Python Script

# Example query:
# > "Create a personalized day plan in Amsterdam tomorrow:
# > - Must include: morning coffee (must have cortado coffee), italian lunch spot, afternoon coffee for people watching
# > - Include museums and art galleries if rainy
# > - Keep everything walking distance within one neighborhood"

import os
import pathlib

# Set Langfuse environment variables if they are present
# NOTE: It's recommended to set these in your shell environment rather than directly in the code.
# os.environ["LANGFUSE_SECRET_KEY"] = "your-langfuse-secret-key" # Uncomment and replace if setting here
# os.environ["LANGFUSE_PUBLIC_KEY"] = "your-langfuse-public-key" # Uncomment and replace if setting here
# os.environ["HAYSTACK_CONTENT_TRACING_ENABLED"] = "true" # Set to true to enable detailed tracing

# Import Haystack components *after* setting environment variables
from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.dataclasses import ChatMessage, StreamingChunk

from haystack_integrations.components.connectors.langfuse.langfuse_connector import (
    LangfuseConnector,
)
from haystack_integrations.components.generators.amazon_bedrock.chat.chat_generator import (
    AmazonBedrockChatGenerator,
)
from haystack_integrations.tools.mcp.mcp_tool import SSEServerInfo, StdioServerInfo
from haystack_integrations.tools.mcp.mcp_toolset import MCPToolset


def load_system_message():
    """Load the system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        return f.read()


def main():

    # Initialize LangfuseConnector - it will be active if environment variables are set
    tracer = LangfuseConnector("Agent itinerary")

    # Optionally, you can use Langfuse to trace the agent's activity but it needs
    # additional configuration.
    # See [Langfuse integration](https://github.com/deepset-ai/haystack-core-integrations/tree/main/integrations/langfuse) for more information.

    # Create toolsets for each service
    maps_toolset = MCPToolset(
        SSEServerInfo(base_url="http://localhost:8100"),
        tool_names=["maps_geocode", "maps_search_places", "maps_place_details"],
    )

    weather_toolset = MCPToolset(
        SSEServerInfo(base_url="http://localhost:8101"),
        tool_names=[
            "get_weather_forecast",
        ],
    )

    preferences_toolset = MCPToolset(SSEServerInfo(base_url="http://localhost:8102"))

    # Add Brave Search toolset
    brave_search_toolset = MCPToolset(
        StdioServerInfo(
            command="docker",
            args=["run", "-i", "--rm", "-e", "BRAVE_API_KEY", "mcp/brave-search"],
            env={"BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY")},
        ),
        tool_names=["brave_web_search"],
    )

    # Combine all tools
    all_tools = (
        maps_toolset + weather_toolset + preferences_toolset + brave_search_toolset
    )

    # Create the agent with all tools and system message

    # llm = AmazonBedrockChatGenerator(model="anthropic.claude-3-5-sonnet-20240620-v1:0")
    llm = OpenAIChatGenerator(model="gpt-4.1", tools=all_tools)
    agent = Agent(
        system_prompt=load_system_message(),
        chat_generator=llm,
        tools=all_tools,
        streaming_callback=print_streaming_chunk,
    )

    # Example query for creating a personalized itinerary
    result = agent.run(
        messages=[
            ChatMessage.from_user(
                text="""
                                  Create a personalized day plan in Bangalore, India tomorrow:
                                  - Must include: morning coffee (must have espresso), Indian fusion lunch spot, afternoon coffee for people watching
                                  - Include museums and art galleries if rainy
                                  - Keep everything walking distance within one neighborhood
                                  """
            )
        ]
    )
    # print(result["messages"][-1].text)


if __name__ == "__main__":
    main()

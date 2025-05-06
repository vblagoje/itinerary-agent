# SPDX-FileCopyrightText: 2022-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

# Overview: This script runs a Haystack agent that uses MCP tools to create personalized itineraries.

import pathlib

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
from haystack_integrations.tools.mcp.mcp_tool import SSEServerInfo
from haystack_integrations.tools.mcp.mcp_toolset import MCPToolset


def load_system_message():
    """Load the system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        return f.read()


def main():

    # Initialize LangfuseConnector - it will be active if environment variables are set
    # if you don't want to use Langfuse, just comment out the following line
    tracer = LangfuseConnector("Agent itinerary")

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
        SSEServerInfo(base_url="http://localhost:8103"),
        tool_names=["brave_web_search"],
    )

    # Combine all tools
    all_tools = (
        maps_toolset + weather_toolset + preferences_toolset + brave_search_toolset
    )

    # Create the agent with all tools and system message

    # llm = AmazonBedrockChatGenerator(model="anthropic.claude-3-5-sonnet-20240620-v1:0")
    llm = OpenAIChatGenerator(model="gpt-4.1")
    agent = Agent(
        system_prompt=load_system_message(),
        chat_generator=llm,
        tools=all_tools,
        streaming_callback=print_streaming_chunk,
    )

    # Example query for creating a personalized itinerary
    agent.run(
        messages=[
            ChatMessage.from_user(
                text="""
                    Create a personalized day plan in Munich, Germany tomorrow:
                    - Must include: morning coffee (must have espresso), Italian lunch spot, afternoon coffee for people watching
                    - Include museums and art galleries if rainy
                    - Keep everything walking distance within one neighborhood
                    """
            )
        ]
    )


if __name__ == "__main__":
    main()

# SPDX-FileCopyrightText: 2022-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

# Overview: This script runs a Haystack agent that uses MCP tools to create personalized itineraries.

import pathlib

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.dataclasses import ChatMessage
from haystack.tools import ComponentTool

from haystack_integrations.components.connectors.langfuse.langfuse_connector import (
    LangfuseConnector,
)
from haystack_integrations.components.generators.amazon_bedrock.chat.chat_generator import (
    AmazonBedrockChatGenerator,
)
from haystack_integrations.tools.mcp.mcp_tool import SSEServerInfo, StdioServerInfo
from haystack_integrations.tools.mcp.mcp_toolset import MCPToolset


def load_day_itinerary_system_message():
    """Load the system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "day_itinerary_system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        return f.read()


def load_macro_itinerary_system_message():
    """Load the system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "macro_itinerary_system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        return f.read()


def main():
    # Use streaming to print the response
    use_streaming = True

    # Initialize LangfuseConnector - it will be active if environment variables are set
    # if you don't want to use Langfuse, just comment out the following line
    tracer = LangfuseConnector("Agent itinerary")

    maps_toolset = MCPToolset(
        SSEServerInfo(url="http://localhost:8100/sse"),
        tool_names=["maps_search_places", "maps_place_details"],
    )

    routing_toolset = MCPToolset(
        SSEServerInfo(url="http://localhost:8104/sse"),
        tool_names=["compute_optimal_route"],
    )

    preferences_toolset = MCPToolset(
        SSEServerInfo(url="http://localhost:8102/sse"), tool_names=["qdrant-find"]
    )

    perplexity_toolset = MCPToolset(
        SSEServerInfo(
            url="http://localhost:8105/sse", timeout=90
        ),  # seconds, as perplexity takes time to respond
        tool_names=["perplexity_ask"],
    )

    # Combine all tools
    all_tools = (
        maps_toolset + routing_toolset + preferences_toolset + perplexity_toolset
    )

    # Create the agent with all tools and system message

    # llm = AmazonBedrockChatGenerator(model="anthropic.claude-3-5-sonnet-20240620-v1:0")
    llm = OpenAIChatGenerator(model="gpt-4.1-mini")

    day_itinerary_agent = Agent(
        system_prompt=load_day_itinerary_system_message(),
        chat_generator=llm,
        tools=all_tools,
        streaming_callback=print_streaming_chunk if use_streaming else None,
    )

    day_tool = ComponentTool(
        name="daily_itinerary_planning_agent",
        description="Daily Itinerary Planning Agent (DIPA) - creates detailed single-day itineraries based on macro itinerary locations",
        component=day_itinerary_agent,
    )

    macro_itinerary_agent = Agent(
        system_prompt=load_macro_itinerary_system_message(),
        chat_generator=llm,
        tools=all_tools + [day_tool],
        streaming_callback=print_streaming_chunk if use_streaming else None,
    )

    try:
        response = macro_itinerary_agent.run(
            messages=[
                ChatMessage.from_user(
                    text="""
                        Create a personalized a 10 day trip itinerary in south of France. 
                        - Start in Nice and end in Marseille
                        - Every day morning specialty espresso coffee is a must
                        - Visit the most beautiful villages, towns and cities in Provence and Côte d'Azur.
                        - Don't use hub and spoke approach of staying in one town and visiting the surrounding towns, but rather move around dynamically.
                        - See authentic towns and villages, not just the usual tourist traps, although must have tourist attractions are ok.
                        - Aim to have 12-14 towns/villages/cities in the itinerary.
                        - Must include cities/towns:
                            - Nice, Provence
                            - Cannes, Provence
                            - Saint-Tropez, Provence
                            - That place with lavender fields, Provence
                            - Aix-en-Provence, Provence
                            - Marseille, Provence
                        """
                )
            ]
        )
        if not use_streaming:
            print(response["messages"][-1].text)
    finally:
        for toolset in all_tools:
            if hasattr(toolset, "close"):
                toolset.close()


if __name__ == "__main__":
    main()

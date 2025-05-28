# SPDX-FileCopyrightText: 2022-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

# Overview: This script runs a Haystack agent that uses MCP tools to create personalized itineraries.

import pathlib
import questionary

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.components.generators.utils import print_streaming_chunk
from haystack.dataclasses import ChatMessage
from haystack.tools import ComponentTool

from haystack_integrations.components.connectors.langfuse.langfuse_connector import (
    LangfuseConnector,
)

from haystack_integrations.tools.mcp.mcp_tool import SSEServerInfo
from haystack_integrations.tools.mcp.mcp_toolset import MCPToolset

from user_input_tooling import hand_off_to_next_tool, human_in_loop_tool


def load_day_itinerary_system_message():
    """Load the system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "day_itinerary_system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        return f.read()

def load_objective_clarifier_system_message():
    """Load the system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "objective_clarifier_system_prompt.txt"
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

    perplexity_toolset = MCPToolset(
        SSEServerInfo(
            url="http://localhost:8105/sse", timeout=90
        ),  # seconds, as perplexity takes time to respond
        tool_names=["perplexity_ask"],
    )

    # Combine all tools
    all_tools = maps_toolset + routing_toolset + perplexity_toolset

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

    objective_clarifier_agent = Agent(
        chat_generator=llm,
        tools=[human_in_loop_tool, hand_off_to_next_tool],
        streaming_callback=None,
        system_prompt=load_objective_clarifier_system_message(),
        exit_conditions=["hand_off_to_next_tool"]
    )

    objective_clarifier_tool = ComponentTool(
        component=objective_clarifier_agent,
        description="Use this tool to clarify user's objective and constraints of user's intention",
        name="travel_objective_clarifier_tool"
    )


    macro_itinerary_agent = Agent(
        system_prompt=load_macro_itinerary_system_message(),
        chat_generator=llm,
        tools=all_tools + [day_tool, objective_clarifier_tool],
        streaming_callback=print_streaming_chunk if use_streaming else None,
    )

    try:
        # Get user input interactively
        user_input = questionary.text(
            "What kind of itinerary would you like me to create for you?",
            default="For example, the default is a 4 day trip in south of France."
        ).ask()
        
        if not user_input:
            print("No input provided. Exiting...")
            return
            
        response = macro_itinerary_agent.run(
            messages=[
                ChatMessage.from_user(text=user_input)
            ]
        )
        if not use_streaming:
            print(response["messages"][-1].text)
    finally:
        for tool in all_tools:
            if (isinstance(tool, MCPToolset)):
                tool.close()


if __name__ == "__main__":
    main()

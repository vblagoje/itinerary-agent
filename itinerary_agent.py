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
from haystack_integrations.components.generators.amazon_bedrock import AmazonBedrockChatGenerator

from haystack_integrations.tools.mcp.mcp_tool import SSEServerInfo
from haystack_integrations.tools.mcp.mcp_toolset import MCPToolset

from user_input_tooling import hand_off_to_next_tool, human_in_loop_tool


def load_day_itinerary_system_message():
    """Load the system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "day_itinerary_system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        return f.read()

def load_lodging_itinerary_system_message():
    """Load the lodging itinerary system message from the external file."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "lodging_itinerary_system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        return f.read()

def load_objective_clarifier_system_message(questioning_mode: str = "normal"):
    """Load the system message from the external file and inject questioning mode."""
    current_dir = pathlib.Path(__file__).parent
    system_file = current_dir / "objective_clarifier_system_prompt.txt"
    with open(system_file, encoding="utf-8") as f:
        system_prompt_template = f.read()

    # Define questioning mode instructions
    mode_instructions = {
        "minimal": "**QUESTIONING MODE: MINIMAL** - Ask only one batch of most essential questions. Focus on core goal and basic context. Do not explore preferences or edge cases unless volunteered. Limit yourself to 3 questions maximum.",
        "normal": "**QUESTIONING MODE: NORMAL** - Default mode. Ask two batches of questions maximum - strategically covering objective, context, preferences, and relevant constraints.",
        "deep": "**QUESTIONING MODE: DEEP** - Be thorough. Ask detailed and specific questions about motivations, constraints, edge cases, and subjective preferences. Prioritize clarity and completeness. You may ask up to 10 questions if needed."
    }
    # Get the instruction for the current mode
    questioning_mode_instructions = mode_instructions.get(questioning_mode, "normal")

    # Format the template with the questioning mode instructions
    system_prompt = system_prompt_template.format(
        questioning_mode_instructions=questioning_mode_instructions
    )

    return system_prompt

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
    # Uncomment this line below to use Langfuse tracing
    #tracer = LangfuseConnector("Agent itinerary")

    maps_toolset = MCPToolset(
        SSEServerInfo(url="http://localhost:8100/sse"),
        tool_names=["maps_search_places", "maps_place_details"],
    )

    routing_toolset = MCPToolset(
        SSEServerInfo(url="http://localhost:8104/sse"),
        tool_names=["compute_optimal_route", "get_distance_direction"],
    )

    perplexity_toolset = MCPToolset(
        SSEServerInfo(
            url="http://localhost:8105/sse"
        ),
        tool_names=["perplexity_ask"],
        invocation_timeout=120, # seconds, as perplexity takes time to respond
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
        description="Plans a detailed one-day itinerary. Input: 'Plan detailed day [X] for [location(s)], with activities drawn from [preferences], and stay at[accommodation].' Call this tool separately per day.",
        component=day_itinerary_agent,
    )

    lodging_itinerary_agent = Agent(
        system_prompt=load_lodging_itinerary_system_message(),
        chat_generator=llm,
        tools=all_tools,
        streaming_callback=print_streaming_chunk if use_streaming else None,
    )

    lodging_tool = ComponentTool(
        name="accommodation_strategy_optimizer",
        description="Determines optimal accommodation placement for multi-day travel itineraries. Input: 'Optimize accommodation strategy for [X]-day route: [destination sequence], transportation: [mode], lodging preferences: [preferences and budget].'",
        component=lodging_itinerary_agent,
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
        tools=all_tools + [day_tool, lodging_tool, objective_clarifier_tool],
        streaming_callback=print_streaming_chunk if use_streaming else None,
    )

    try:
        # Get user input interactively
        user_input = questionary.text(
            "What kind of itinerary would you like me to create for you? For example: A 4-day trip in the south of France."
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

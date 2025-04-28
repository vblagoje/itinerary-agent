# SPDX-FileCopyrightText: 2022-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

### Overview
# This script shows how to use multiple MCP Servers (managed via docker-compose)
# in combination with the **Haystack Agent** and **OpenAI's Chat Generator**
# to create comprehensive travel itineraries.
# It combines:
# - Google Maps for location search and navigation
# - Weather data for activity planning
# - User preferences storage for personalization (using Qdrant)
# - Brave Search for additional context and information
# - A system message to guide the agent's behavior and capabilities

# ---

# ### ⚙️ Step 1: Configuration & Prerequisites

# 1.  **Install Dependencies:**
#     ```bash
#     pip install -r requirements.txt
#     ```

# 2.  **Set Environment Variables:**
#     Create a `.env` file in the project root directory (where `docker-compose.yml` is)
#     or export these variables in your shell before running `docker-compose up` or the script.

#     **Required:**
#     - `GOOGLE_MAPS_API_KEY`: Your Google Maps API key. Get one from the Google Cloud Console:
#       https://console.cloud.google.com/google/maps-apis/overview
#       Ensure you have enabled the "Geocoding API", "Places API", and "Directions API".
#     - `OPENWEATHER_API_KEY`: Your OpenWeatherMap API key. Get one from:
#       https://openweathermap.org/appid
#     - `BRAVE_API_KEY`: Your Brave Search API key. Get one from:
#       https://brave.com/search/api/
#     - `OPENAI_API_KEY`: Your OpenAI API key (if using `OpenAIChatGenerator`). Get one from:
#       https://platform.openai.com/api-keys
#       *Alternatively, if using `AmazonBedrockChatGenerator`, ensure your AWS credentials
#       are configured (e.g., via `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
#       or an IAM role).* Refer to AWS documentation.

#     **For Qdrant (if using a Cloud Instance):**
#     *(Note: The default docker-compose likely runs a local Qdrant instance, requiring no extra env vars.
#     Only set these if you modify docker-compose to use a cloud Qdrant.)*
#     - `QDRANT_URL`: The URL of your Qdrant Cloud instance.
#     - `QDRANT_API_KEY`: The API key for your Qdrant Cloud instance.

#     **Optional (for Langfuse Tracing):**
#     - `LANGFUSE_SECRET_KEY`: Your Langfuse Secret Key.
#     - `LANGFUSE_PUBLIC_KEY`: Your Langfuse Public Key.
#     - `LANGFUSE_HOST`: The host URL for your Langfuse instance (e.g., https://cloud.langfuse.com).
#     - `HAYSTACK_CONTENT_TRACING_ENABLED=true`: Set to enable detailed Haystack tracing.
#       Get keys and host from your Langfuse project settings.

# ---

# ### 🐳 Step 2: Start Services with Docker Compose

# Run the following command from the project root directory:
# ```bash
# docker-compose up -d
# ```
# This will start the Google Maps, Weather, Qdrant, and Brave Search MCP servers
# based on the configuration in `docker-compose.yml`.

# ---

# ### ✍️ Step 3: Populate User Preferences (One-time Setup)

# For the agent to personalize itineraries, you need to store your preferences in Qdrant.
# 1. **Generate Preferences:** Think about your travel style, likes, dislikes, food preferences,
#    dietary restrictions, preferred activities (e.g., museums, nightlife, relaxation),
#    budget considerations, etc. You can use an LLM like ChatGPT to help you formulate
#    these into a descriptive paragraph or a list.
#    *Example:* "I love trying local street food but avoid spicy dishes. Prefer boutique hotels
#    over large chains. Enjoy walking tours and visiting historical sites. Not interested in
#    nightclubs. My budget is mid-range. I need a good espresso in the morning."
# Example: I used ChatGPT to generate my travel preferences by asking:
# "Based on everything we've discussed, could you create a comprehensive travel preferences
# profile for me that I can use with a travel planning system? Include my style, interests,
# budget level, and any restrictions."

# 2. **Store Preferences:** Use an MCP client tool (like the MCP Inspector,
#    Cursor if it has MCP integration, or another IDE/tool supporting MCP) connected to
#    your Qdrant MCP server (running on port 8102 by default in docker-compose).
#    - Invoke the `qdrant-store` tool.
#    - Paste your generated preferences string into the `information` field.
#    - Execute the call. This only needs to be done once or whenever your preferences change.

# ---

# ### ▶️ Step 4: Run the Python Script

# Execute the script:
# ```bash
# python itinerary_agent.py
# ```
# The agent will use the running MCP services and your configured LLM to generate the itinerary.

# --- Example Query (inside the script):
# Create a personalized day plan in Munich, Germany tomorrow:
# - Must include: morning coffee (must have espresso), Italian lunch spot, afternoon coffee for people watching
# - Include museums and art galleries if rainy
# - Keep everything walking distance within one neighborhood

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
    llm = OpenAIChatGenerator(model="gpt-4.1", tools=all_tools)
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

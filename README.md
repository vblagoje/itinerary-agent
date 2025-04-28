# Personalized Itinerary Agent with Haystack & MCP

This project demonstrates a personalized travel itinerary agent built using [Haystack](https://haystack.deepset.ai/) and the [Model Context Protocol (MCP)](https://modelcontextprotocol.com/). The agent leverages multiple MCP servers (managed via `docker-compose`) to create detailed day plans based on user preferences and real-time data.

**Features:**

*   **Personalization:** Uses preferences stored in Qdrant to tailor suggestions.
*   **Real-time Data:** Integrates Google Maps, OpenWeatherMap, and Brave Search via MCP servers.
*   **Extensible:** Easily add more tools or change the LLM.
*   **Traceable:** Optional integration with Langfuse for monitoring and debugging.

## Prerequisites

*   Python 3.10+
*   Docker & Docker Compose
*   Access to the required API keys (see below)

## Setup

1.  **Clone the Repository (if you haven't already):**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a file named `.env` in the project root directory (alongside `docker-compose.yml`) and add the following variables with your keys. Alternatively, export these variables in your shell environment.

    **Required:**
    *   `GOOGLE_MAPS_API_KEY`: Your Google Maps API key. Get one from [Google Cloud Console](https://console.cloud.google.com/google/maps-apis/overview). Enable "Geocoding API", "Places API", and "Directions API".
    *   `OPENWEATHER_API_KEY`: Your OpenWeatherMap API key. Get one from [OpenWeatherMap](https://openweathermap.org/appid).
    *   `BRAVE_API_KEY`: Your Brave Search API key. Get one from [Brave Search API](https://brave.com/search/api/).
    *   `OPENAI_API_KEY`: Your OpenAI API key (if using `OpenAIChatGenerator` in `itinerary_agent.py`). Get one from [OpenAI Platform](https://platform.openai.com/api-keys).
        *   *Note:* If you modify `itinerary_agent.py` to use `AmazonBedrockChatGenerator`, ensure your AWS credentials are configured instead (e.g., via `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`).

    **Optional (for Langfuse Tracing):**
    *   `LANGFUSE_SECRET_KEY`: Your Langfuse Secret Key.
    *   `LANGFUSE_PUBLIC_KEY`: Your Langfuse Public Key.
    *   `LANGFUSE_HOST`: Your Langfuse instance host (e.g., `https://cloud.langfuse.com`).
    *   `HAYSTACK_CONTENT_TRACING_ENABLED=true`: Enables detailed Haystack tracing.
        Get keys and host from your [Langfuse](https://langfuse.com/) project settings.

    *(Note: The default `docker-compose.yml` runs a local Qdrant instance, so `QDRANT_URL` and `QDRANT_API_KEY` are typically not needed unless you modify the setup to use a cloud instance.)*

4.  **Start MCP Services:**
    Run the following command from the project root:
    ```bash
    docker-compose up -d
    ```
    This starts the Google Maps, Weather, Qdrant, and Brave Search MCP servers defined in `docker-compose.yml`.

5.  **Populate User Preferences (One-time Setup):**
    For personalized results, store your preferences in the Qdrant database:
    *   **Generate:** Create a text description of your travel style, likes, dislikes, food preferences, budget, etc.
        *Example:* "Loves local cafes with good espresso, enjoys art galleries and walking tours. Mid-range budget. Prefers Italian or Thai food. Not interested in nightlife."
    *   **Store:** Use an MCP client tool (like the [MCP Inspector](https://marketplace.visualstudio.com/items?itemName=MCPInspector.mcp-inspector-vscode) VS Code extension, Cursor, or another tool) connected to the Qdrant MCP server (running at `http://localhost:8102` by default).
        *   Invoke the `qdrant-store` tool.
        *   Paste your preferences text into the `information` field.
        *   Execute the call.

## Running the Agent

Once the services are running and preferences are stored (optional but recommended), execute the Python script:

```bash
python itinerary_agent.py
```

The script contains an example query (e.g., planning a day in Munich). You can modify this query directly within the `itinerary_agent.py` file to ask for different itineraries. The agent will interact with the running MCP services and the configured LLM to generate and stream the response to your terminal.

## How it Works

*   `itinerary_agent.py`: Contains the main Haystack Agent logic, tool definitions, and system prompt loading.
*   `docker-compose.yml`: Defines the MCP services (Google Maps, Weather, Qdrant, Brave Search) and their configurations.
*   `requirements.txt`: Lists the required Python packages.
*   `.env` (you create this): Stores the necessary API keys.
*   `system_prompt.txt`: Contains the instructions guiding the LLM's behavior as the itinerary agent. 
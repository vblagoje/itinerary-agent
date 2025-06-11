# Personalized Itinerary Agent with Haystack & MCP

This project demonstrates a personalized travel itinerary agent built using [Haystack](https://haystack.deepset.ai/) and the [Model Context Protocol (MCP)](https://modelcontextprotocol.com/). The system uses a multi-tier agent architecture:

1. **Macro Itinerary Planning Agent**: Plans the overall trip, determining major stops and routing across multiple days
2. **Lodging Agent**: Determines optimal lodging selection taking into account preferences and overal itinerary dynamics
3. **Daily Itinerary Planning Agent**: Handles detailed day-by-day planning with lodging context and themed focus (invoked as a tool by the Macro Agent)
4. **Objective Clarifier Agent**: Interactively gathers user preferences, constraints, and requirements

The agents leverage multiple MCP servers (managed via `docker-compose`) to create detailed itineraries based on user preferences and real-time data.

**Features:**

*   **Hierarchical Planning:** Macro agent plans the overall trip, lodging agent strategically places lodging and assigns daily themes, while day agent handles detailed daily itineraries.
*   **Strategic Lodging:** Optimizes lodging locations based on preferences and overall itinerary dynamics. 
*   **Interactive Preference Gathering:** Uses an objective clarifier agent to gather user preferences through conversational interaction.
*   **Real-time Data:** Integrates Google Maps, Perplexity, and optimal route calculation via MCP servers.
*   **Extensible:** Easily add more tools or change the LLM.
*   **Traceable:** Optional integration with Langfuse for monitoring and debugging.

## Prerequisites

*   Python 3.10+
*   Docker & Docker Compose
*   Access to the required API keys (see below)

## Setup

1.  **Clone the Repository (if you haven't already):**
    ```bash
    git clone https://github.com/vblagoje/itinerary-agent.git
    cd itinerary-agent
    ```

2.  **Install Python Dependencies:**
    *It's highly recommended to create and activate a virtual environment first:* 
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
    *Then, install the required packages:*
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a file named `.env` in the project root directory (alongside `docker-compose.yml`) and add the following variables with your keys. Alternatively, export these variables in your shell environment.

    **Required:**
    *   `GOOGLE_MAPS_API_KEY`: Your Google Maps API key. Get one from [Google Cloud Console](https://console.cloud.google.com/google/maps-apis/overview). Enable "Geocoding API", "Places API", and "Directions API". This key is also used by the optimal route calculation service.
    *   `PERPLEXITY_API_KEY`: Your Perplexity API key. Get one from [Perplexity API](https://docs.perplexity.ai/).
    *   `OPENAI_API_KEY`: Your OpenAI API key (if using `OpenAIChatGenerator` in `itinerary_agent.py`). Get one from [OpenAI Platform](https://platform.openai.com/api-keys).
        *   *Note:* If you modify `itinerary_agent.py` to use `AmazonBedrockChatGenerator`, ensure your AWS credentials are configured instead (e.g., via `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`).

    **Optional (for Langfuse Tracing):**
    *   `LANGFUSE_SECRET_KEY`: Your Langfuse Secret Key.
    *   `LANGFUSE_PUBLIC_KEY`: Your Langfuse Public Key.
    *   `LANGFUSE_HOST`: Your Langfuse instance host (e.g., `https://cloud.langfuse.com`).
    *   `HAYSTACK_CONTENT_TRACING_ENABLED=true`: Enables detailed Haystack tracing.
        Get keys and host from your [Langfuse](https://langfuse.com/) project settings.

4.  **Start MCP Services:**
    Run the following command from the project root:
    ```bash
    docker-compose up
    ```
    This starts the Google Maps, Perplexity, and optimal route calculation (vblagoje/optimal-route) MCP servers defined in `docker-compose.yml`.

## Running the Agent

Once the services are running, execute the Python script:

```bash
python itinerary_agent.py
```

The script will prompt you interactively for your travel requirements using `questionary`. The system includes an objective clarifier agent that will gather detailed preferences, constraints, and requirements through conversational interaction. The macro agent will then interact with the running MCP services and utilize the day itinerary agent as needed to generate detailed plans. Results are streamed to your terminal.

## Example Run

You can view an example of the agent's execution with full tracing in Langfuse:
[South of France 10-day Itinerary Trace](https://us.cloud.langfuse.com/project/cm9inpne801ruad07ci8vevid/traces/68546d29-d41b-429f-8c27-ca5ecf273391?timestamp=2025-05-22T08:30:02.403Z&display=timeline)

## How it Works

*   `itinerary_agent.py`: Contains the Haystack Agent logic for macro, lodging strategy, day itinerary, and objective clarifier agents, tool definitions, and system prompt loading.
*   `user_input_tooling.py`: Contains tools for human-in-the-loop interaction and agent handoff functionality.
*   `docker-compose.yml`: Defines the MCP services (Google Maps, Perplexity, and optimal route calculation) and their configurations.
*   `requirements.txt`: Lists the required Python packages including `questionary` for interactive prompts.
*   `.env` (you create this): Stores the necessary API keys.
*   `macro_itinerary_system_prompt.txt`: Contains the instructions guiding the LLM's behavior as the macro itinerary agent.
*   `lodging_itinerary_system_prompt.txt`: Contains the instructions for the lodging agent that determines lodging placement and daily themes.
*   `day_itinerary_system_prompt.txt`: Contains the instructions for the day-by-day planning agent.
*   `objective_clarifier_system_prompt.txt`: Contains the instructions for the objective clarifier agent that gathers user preferences.
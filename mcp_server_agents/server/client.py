import asyncio
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

from mcp_use import MCPAgent, MCPClient
import os
load_dotenv()

async def run_memory_chat():
    """Run a chat using MCPAgent's built-in conversation memory."""

    config_file = "server/weather.json"

    client = MCPClient.from_config_file(config_file)
    llm =llm =  init_chat_model(
    model = os.getenv("MODEL_NAME"),
    api_key = os.getenv("OPENROUTER_API_KEY"),
    model_provider="openrouter",
    base_url = "https://openrouter.ai/api/v1",
    temperature = 0
    )
    agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=15,
        memory_enabled=True,  # Enable built-in conversation memory
    )

    print("\n===== Interactive MCP Chat =====")
    print("Type 'exit' or 'quit' to end the conversation")
    print("Type 'clear' to clear conversation history")
    print("==================================\n")

    try:
        # Main chat loop
        while True:
            # Get user input
            user_input = input("\nYou: ")

            # Check for exit command
            if user_input.lower() in ["exit", "quit"]:
                print("Ending conversation...")
                break

            # Check for clear history command
            if user_input.lower() == "clear":
                agent.clear_conversation_history()
                print("Conversation history cleared.")
                continue

            # Get response from agent
            print("\nAssistant: ", end="", flush=True)

            try:
                # Run the agent with the user input (memory handling is automatic)
                response = await agent.run(user_input)
                print(response)

            except Exception as e:
                print(f"\nError: {e}")

    finally:
        # Clean up
        if client and client.sessions:
            await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(run_memory_chat())
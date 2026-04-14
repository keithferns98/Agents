import os
import sys
import asyncio
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_community.tools.tavily_search import TavilySearchResults
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage
from rich.console import Console
from urllib.parse import quote_plus

load_dotenv()

rich_console = Console()

llm = init_chat_model()

llm =  init_chat_model(
    model = os.getenv("MODEL_NAME"),
    api_key = os.getenv("OPENROUTER_API_KEY"),
    model_provider="openrouter",
    base_url = "https://openrouter.ai/api/v1",
    temperature = 0
)

tavily = TavilySearchResults(max_results=3)

def process_chunks(chunk):
    """
    Processes a chunk from the agent and displays information about tool calls or the agent's answer.

    Parameters:
        chunk (dict): A dictionary containing information about the agent's messages.

    Returns:
        None

    This function processes a chunk of data to check for agent messages.
    It iterates over the messages and checks for tool calls.
    If a tool call is found, it extracts the tool name and query, then prints a formatted message using the Rich library.
    If no tool call is found, it extracts and prints the agent's answer using the Rich library.
    """

    # Check if the chunk contains an agent's message
    if "agent" in chunk:
        # Iterate over the messages in the chunk
        for message in chunk["agent"]["messages"]:
            # Check if the message contains tool calls
            if "tool_calls" in message.additional_kwargs:
                # If the message contains tool calls, extract and display an informative message with tool call details

                # Extract all the tool calls
                tool_calls = message.additional_kwargs["tool_calls"]

                # Iterate over the tool calls
                for tool_call in tool_calls:
                    # Extract the tool name
                    tool_name = tool_call["function"]["name"]

                    # Extract the tool query
                    tool_arguments = eval(tool_call["function"]["arguments"])
                    tool_query = tool_arguments["query"]

                    # Display an informative message with tool call details
                    rich_console.print(
                        f"\nThe agent is calling the tool [on deep_sky_blue1]{tool_name}[/on deep_sky_blue1] with the query [on deep_sky_blue1]{tool_query}[/on deep_sky_blue1]. Please wait for the agent's answer[deep_sky_blue1]...[/deep_sky_blue1]",
                        style="deep_sky_blue1",
                    )
            else:
                # If the message doesn't contain tool calls, extract and display the agent's answer

                # Extract the agent's answer
                agent_answer = message.content

                # Display the agent's answer
                rich_console.print(f"\nAgent:\n{agent_answer}", style="black on white")


async def process_checkpoints(checkpoints):
    """
    Asynchronously processes a list of checkpoints and displays relevant information.
    Each checkpoint consists of a tuple where the first element is the index and the second element is an object
    containing various details about the checkpoint. The function distinguishes between messages from the user
    and the agent, displaying them accordingly.

    Parameters:
        checkpoints (list): A list of checkpoint tuples to process.

    Returns:
        None

    This function processes a list of checkpoints asynchronously.
    It iterates over the checkpoints and displays the following information for each checkpoint:
    - Timestamp
    - Checkpoint ID
    - Messages associated with the checkpoint
    """
    
    rich.print("\n==========================================================\n")

    # Initialize an empty list to store the checkpoints
    checkpoints_list = []

    # Iterate over the checkpoints and add them to the list in an async way
    async for checkpoint_tuple in checkpoints:
        checkpoints_list.append(checkpoint_tuple)

    # Iterate over the list of checkpoints
    for idx, checkpoint_tuple in enumerate(checkpoints_list):
        # Extract key information about the checkpoint
        checkpoint = checkpoint_tuple.checkpoint
        messages = checkpoint["channel_values"].get("messages", [])

        # Display checkpoint information
        rich_console.print(f"[white]Checkpoint:[/white]")
        rich_console.print(f"[black]Timestamp: {checkpoint['ts']}[/black]")
        rich_console.print(f"[black]Checkpoint ID: {checkpoint['id']}[/black]")

        # Display checkpoint messages
        for message in messages:
            if isinstance(message, HumanMessage):
                rich_console.print(
                    f"[bright_magenta]User: {message.content}[/bright_magenta] [bright_cyan](Message ID: {message.id})[/bright_cyan]"
                )
            elif isinstance(message, AIMessage):
                rich_console.print(
                    f"[bright_magenta]Agent: {message.content}[/bright_magenta] [bright_cyan](Message ID: {message.id})[/bright_cyan]"
                )

        rich_console.print("")

    rich_console.print("==========================================================")

def build_pg_conn_string():
    user = os.getenv("USER")
    password = quote_plus(os.getenv("PASSWORD"))  # handles special chars
    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "5432")
    db = os.getenv("PSQL_DATABASE")
    sslmode = os.getenv("PSQL_SSLMODE", "prefer")

    return f"postgresql://{user}:{password}@{host}:{port}/{db}?sslmode={sslmode}"

async def main():
    """
    Entry point of the application. Connects to a PostgreSQL database, initializes a persistant chat memory,
    creates a LangGraph agent, and handles user interaction in a loop until the user chooses to quit.

    Parameters: 
        None
    Returns: None

    This function performs the following steps:
    1. Connects to the PostgreSQL database using an async connection pool.
    2. Initializes a persistent chat memory.
    3. Creates a LangGraph agent with the specified model and tools.
    4. Enters a loop to interact with the user:
       - Prompts the user for a question.
       - Checks if the user wants to quit.
       - Uses the LangGraph agent to get the agent's answer.
       - Processes the chunks from the agent.
       - Lists and processes all checkpoints that match a given configuration.

    """
    conn_str = build_pg_conn_string()

    async with AsyncConnectionPool(
    conninfo=conn_str,
    max_size=20,
    kwargs={
        "autocommit": True,
        "prepare_threshold": 0,
        "row_factory": dict_row,
    },
) as pool, pool.connection() as conn:
        
        memory = AsyncPostgresSaver(conn)

        # IMPORTANT: You need to call .setup() the first time you're using your memory
        await memory.setup()

        langgraph_agent = create_react_agent(model = llm,
                                             tools =[tavily], checkpointer= memory)
        
        while True:
            user_question = input("\nUser:\n")

            if user_question.lower() == "quit":
                rich_console.print(
                    "\nAgent:\nHave a nice day! :wave:\n", style="black on white"
                )
                break

            async for chunk in langgraph_agent.astream(
                {
                    "messages": [HumanMessage(content = user_question)]
                },
                {"configurable": {"thread_id": 1}},
            ):
                process_chunks(chunk)

                # Use the async list method of the memory to list all checkpoints that match a given configuration
                checkpoints = memory.alist({"configurable": {"thread_id": "1"}})
                # Process the checkpoints from the memory in an async way
                await process_checkpoints(checkpoints)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Run the main async function
    asyncio.run(main())

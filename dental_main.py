"""
Dental Appointment System - powered by LangGraph + LLM
"""

from dotenv import load_dotenv
load_dotenv()
import asyncio
from langchain_core.messages import HumanMessage, AIMessageChunk
from dental_agent.workflow.graphs import dental_graph
from dental_agent.db.conn_db import Database



BANNER = """
╔══════════════════════════════════════════════════════════╗
║         Dental Appointment Management System             ║
║         Powered by LangGraph + LLM                       ║
╚══════════════════════════════════════════════════════════╝
Examples:
  • Show available slots for an orthodontist
  • Book patient 1000082 with Emily Johnson on 5/10/2026 9:00
  • Cancel appointment for patient 1000082 at 5/10/2026 9:00
  • Reschedule patient 1000082 from 5/10/2026 9:00 to 5/12/2026 10:00
  • What appointments does patient 1000048 have?

Type 'quit' to exit.
"""

async def run():
    print(BANNER)
    await Database.init()
    history =[]
    while True:
        try:
            user_input = input("\nYou: ").strip()
            cmd = user_input.lower()

            if not cmd:
                continue

            if cmd in {"quit", "exit", "bye"}:
                print("Goodbye!")
                break

        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        history.append(HumanMessage(content = user_input))
        print("\nAgent: ", end = "", flush = True)
        final_messsages = None

        try:
            async for event_type, data in dental_graph.astream(
                {"messages": history},
                stream_mode = ["messages", "values"],
                config = {"recursion_limit": 20},
            ):
                if event_type == "messages":
                    chunk, meta = data
                    # Stream tokens only from the agent (not tool results)
                    if (
                        isinstance(chunk, AIMessageChunk)
                        and chunk.content
                        and not getattr(chunk, "tool_calls", None)
                    ):
                        print(chunk.content, end="", flush=True)
                elif event_type == "values":
                    final_messages = data.get("messages", [])
        except Exception as exc:
            print(f"\nError: {exc}")
            history.pop()  # Remove the HumanMessage to avoid consecutive user messages
            continue

        print()
        if final_messages:
            history = final_messages
# Can you patients appointments patient_id is 1000046?

if __name__ == "__main__":
    asyncio.run(run())

# from dental_agent.db.conn_db import Database
# from dental_agent.workflow.graphs import graph
# import asyncio

# async def main():
#     # init DB once
#     await Database.init()

#     # input state
#     input_data = {
#         "specialization": "general_dentist",
#         "doctor_name": "john doe",
#         "date_filter": "2026-08-08",
#         "result": None
#     }

#     result = await graph.ainvoke(input_data)

#     # print("\nFinal Output:\n", result["result"])

#     # close DB
#     await Database.close()


# if __name__ == "__main__":
#     asyncio.run(main())
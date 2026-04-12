from dental_agent.db.conn_db import Database
from dental_agent.workflow.graphs import graph
import asyncio

async def main():
    # init DB once
    await Database.init()

    # input state
    input_data = {
        "specialization": "general_dentist",
        "doctor_name": "john doe",
        "date_filter": "2026-08-08",
        "result": None
    }

    result = await graph.ainvoke(input_data)

    # print("\nFinal Output:\n", result["result"])

    # close DB
    await Database.close()


if __name__ == "__main__":
    asyncio.run(main())
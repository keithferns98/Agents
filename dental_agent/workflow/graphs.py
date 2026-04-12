from typing import TypedDict, Optional
from langgraph.graph import StateGraph
import asyncio
from dental_agent.tools.csv_reader import get_available_slots, get_patient_appointments, check_slot_availability, list_doctors_by_specialization
from dental_agent.tools.csv_writer import book_appointment, cancel_appointment

# ---- State ----
class GraphState(TypedDict):
    specialization: str
    doctor_name: str
    date_filter: str
    result: Optional[list]


# ---- Node ----
async def tool_node(state: GraphState):
    result = await get_available_slots.ainvoke({
        "specialization": state.get("specialization", ""),
        "doctor_name": state.get("doctor_name", ""),
        "date_filter": state.get("date_filter", "")
    })
    # print(result, "result")
    val1 = await get_patient_appointments.ainvoke({
    "patient_id": "1000046"
        })
    val2 = await check_slot_availability.ainvoke({
        "doctor_name": "john doe",
        "date_slot": "12/08/2026 08:00"
    })
    val3 = await list_doctors_by_specialization.ainvoke({
        "specialization": "general_dentist"
    })
    # val4 = await book_appointment.ainvoke({
    #     "patient_id": "1000046",
    #     "doctor_name": "john doe",
    #     "date_slot": "7/8/2026 8:30"
    # })
    # val5 = await cancel_appointment.ainvoke({
    #     "patient_id": "1000046",
    #     "date_slot": "08/24/2026 09:30"
    # })
    print(val1)
    # print(val)
    state["result"] = result
    return state


# ---- Build Graph ----
builder = StateGraph(GraphState)

builder.add_node("get_slots", tool_node)
builder.set_entry_point("get_slots")

graph = builder.compile()
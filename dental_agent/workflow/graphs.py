from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage

from dental_agent.models.state import AppointmentState
from dental_agent.agents.supervisor import supervisor_node
from dental_agent.agents.info_agent import info_agent_node, info_tool_node
from dental_agent.agents.booking_agent import booking_agent_node, booking_tool_node
from dental_agent.agents.cancellation_agent import cancellation_agent_node, cancellation_tool_node
from dental_agent.agents.rescheduling_agent import rescheduling_agent_node, rescheduling_tool_node

def route_from_supervisor(state: AppointmentState)-> str:
    """Read next_agent from state and return the corresponding node name."""
    target = state.get("next_agent", "info_agent")
    valid = {"info_agent", "booking_agent", "cancellation_agent", "rescheduling_agent", "end"}
    return target if target in valid else "info_agent"

def _should_continue(state: AppointmentState):
    """
    If the last AI message has tool_cools, route to tool execution.
    Otherwise the agent has finished - go directly to END.
    (Avoids a redundant supervisor LLM call after every agent response.)
    """
    messages = state.get("messages", [])
    if messages and isinstance(messages[-1], AIMessage) and messages[-1].tool_calls:
        return "tools"
    return "end"


def build_graph():
    print(AppointmentState)
    graph = StateGraph(AppointmentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("info_agent", info_agent_node)
    graph.add_node("info_tools", info_tool_node)
    graph.add_node("booking_agent", booking_agent_node)
    graph.add_node("booking_tools", booking_tool_node)
    graph.add_node("cancellation_agent", cancellation_agent_node)
    graph.add_node("cancellation_tools", cancellation_tool_node)
    graph.add_node("rescheduling_agent", rescheduling_agent_node)
    graph.add_node("rescheduling_tools", rescheduling_tool_node)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "info_agent": "info_agent",
            "booking_agent": "booking_agent",
            "cancellation_agent": "cancellation_agent",
            "rescheduling_agent": "rescheduling_agent",
            "end": END,
        }
    )
     # Info agent loop: agent → tools → agent → END
    graph.add_conditional_edges(
        "info_agent",
        _should_continue,
        {"tools": "info_tools", "end": "supervisor"},
    )
    graph.add_edge("info_tools", "info_agent")

    # Booking agent loop
    graph.add_conditional_edges(
        "booking_agent",
        _should_continue,
        {"tools": "booking_tools", "end": "supervisor"}
    )

    graph.add_edge("booking_tools", "booking_agent")

    # Cancellation agent loop
    graph.add_conditional_edges(
        "cancellation_agent",
        _should_continue,
        {"tools": "cancellation_tools", "end": "supervisor"}
    )
    graph.add_edge("cancellation_tools", "cancellation_agent")

    # Rescheduling agent loop
    graph.add_conditional_edges(
        "rescheduling_agent",
        _should_continue,
        {"tools": "rescheduling_tools", "end": "supervisor"}
    )
    graph.add_edge("rescheduling_tools", "rescheduling_agent")

    return graph.compile()


dental_graph = build_graph()

    #Rescheduling agent loop
# from typing import TypedDict, Optional
# from langgraph.graph import StateGraph
# import asyncio
# from dental_agent.tools.csv_reader import get_available_slots, get_patient_appointments, check_slot_availability, list_doctors_by_specialization
# from dental_agent.tools.csv_writer import book_appointment, cancel_appointment

# # ---- State ----
# class GraphState(TypedDict):
#     specialization: str
#     doctor_name: str
#     date_filter: str
#     result: Optional[list]


# # ---- Node ----
# async def tool_node(state: GraphState):
#     result = await get_available_slots.ainvoke({
#         "specialization": state.get("specialization", ""),
#         "doctor_name": state.get("doctor_name", ""),
#         "date_filter": state.get("date_filter", "")
#     })
#     # print(result, "result")
#     val1 = await get_patient_appointments.ainvoke({
#     "patient_id": "1000046"
#         })
#     val2 = await check_slot_availability.ainvoke({
#         "doctor_name": "john doe",
#         "date_slot": "12/08/2026 08:00"
#     })
#     val3 = await list_doctors_by_specialization.ainvoke({
#         "specialization": "general_dentist"
#     })
#     # val4 = await book_appointment.ainvoke({
#     #     "patient_id": "1000046",
#     #     "doctor_name": "john doe",
#     #     "date_slot": "7/8/2026 8:30"
#     # })
#     # val5 = await cancel_appointment.ainvoke({
#     #     "patient_id": "1000046",
#     #     "date_slot": "08/24/2026 09:30"
#     # })
#     print(val1)
#     # print(val)
#     state["result"] = result
#     return state


# # ---- Build Graph ----
# builder = StateGraph(GraphState)

# builder.add_node("get_slots", tool_node)
# builder.set_entry_point("get_slots")

# graph = builder.compile()
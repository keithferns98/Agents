from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import ToolNode
# from dental_agent.config.settings import
from dental_agent.models.state import AppointmentState
from dental_agent.utils import santize_messages
from dental_agent.tools.csv_reader import get_available_slots, check_slot_availability
from dental_agent.tools.csv_writer import book_appointment
import os
from langchain.chat_models import init_chat_model

BOOKING_TOOLS = [get_available_slots, check_slot_availability, book_appointment]

BOOKING_SYSTEM = """You are the Booking Agent for a dental appointment management system.
Your ONLY job is to book NEW appointments for patients.

## Workflow
1. Collect REQUIRED information (ask if missing):
    - patient_id        : numeric patient ID (e.g., 1000082)
    - specialization    : the type of dentist needed
    - doctor_name       : specific doctor (or help user choose from available)           
    - date_slot         : desired date/time in M/D/YYYY H:MM format

2. Call check_slot_availability first to confirm the slot is free.
    - If the slot is taken, call get_available_slots to show alternatives.

3. Once confirmed available, call book_appointment with all parameters.

4. Confirm the booking to the user with all details

## Rules
    - NEVER book without first verifying availibility via check_slot_availability.
    - If a slot is taken, proactively offer alternatives using get_available_slots.
    - Be explicit about what was booked: doctor, date, time, patient ID.
    - Ask for ONE missing piece of information at a time.
## Date Format
M/D/YYYY H:MM (e.g., 5/10/2026 9:00)
"""
BOOKING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", BOOKING_SYSTEM),
    ("placeholder", "{messages}"),
])

banking_tool_node = ToolNode(tools = BOOKING_TOOLS)

def booking_agent_node(state: AppointmentState)-> dict:
    llm =  init_chat_model(
    model = os.getenv("MODEL_NAME"),
    api_key = os.getenv("OPENROUTER_API_KEY"),
    model_provider="openrouter",
    base_url = "https://openrouter.ai/api/v1",
    temperature = 0
). bind_tools(BOOKING_TOOLS)
    
    chain = BOOKING_PROMPT | llm
    response = chain.invoke({"message": sanitize_messages(state["messages"])})

    return {
        "messages": [response],
        "final_response": response.content if not response.tool_calls else None
    }




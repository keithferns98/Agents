from langchain.tools import tool
from dental_agent.config.settings import  DATE_FORMAT
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dental_agent.db.conn_db import Database

pool = None
 # assuming this

TABLE_NAME = "doctor_schedule_appointment"

@tool
async def get_available_slots(
    specialization: str = "",
    doctor_name: str = "",
    date_filter: str = "",
) -> List[Dict]:
    """
    Fetch available appointment slots from DB
    """

    pool = Database.get_pool()
    query = f"""
        SELECT date_slot, specialization, doctor_name
        FROM {TABLE_NAME}
        WHERE is_available = TRUE
    """

    conditions = []
    values = []
    idx = 1

    if specialization:
        conditions.append(f"specialization = ${idx}")
        values.append(specialization.lower().strip())
        idx += 1

    if doctor_name:
        conditions.append(f"doctor_name = ${idx}")
        values.append(doctor_name.lower().strip())
        idx += 1

    if date_filter:
        try:
            
            start = datetime.strptime(date_filter, "%Y-%m-%d")
            end = start + timedelta(days=1)

            conditions.append(f"date_slot >= ${idx} AND date_slot < ${idx+1}")
            values.extend([start, end])
            idx += 2
        except Exception as e:
            print(e)
            pass
    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += " ORDER BY date_slot LIMIT 20"

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *values, timeout=2.0)
    return [
        {
            "date_slot": r["date_slot"].strftime("%m/%d/%Y %H:%M"),
            "specialization": r["specialization"],
            "doctor_name": r["doctor_name"],
        }
        for r in rows
    ]

@tool
async def get_patient_appointments(patient_id: str):
    """
    Return all booked appointments for a given patient ID.

    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.

    Returns:
        List of dicts with keys: date_slot, specialization, doctor_name, patient_to_attend.
    """

    pool = Database.get_pool()

    query = f"""
        SELECT date_slot, specialization, doctor_name, patient_to_attend
        FROM {TABLE_NAME}
        WHERE patient_to_attend = $1
        ORDER BY date_slot ASC
    """
    print(patient_id)

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, int(patient_id))

    return [
        {
            "date_slot": r["date_slot"].strftime("%m/%d/%Y %H:%M"),
            "specialization": r["specialization"],
            "doctor_name": r["doctor_name"],
            "patient_to_attend": r["patient_to_attend"],
        }
        for r in rows
    ]

@tool
async def check_slot_availability(doctor_name: str, date_slot: str)-> dict:
    """
    Check if a specific doctor slot on that date is available.
    Args:
        doctor_name: Doctor name, e.g. 'emily johnson'.
        date_slot: Slot string in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.
    
    Returns:
        Dict with keys: found (bool), is_available (bool), patient_to_attend (str)
    """
    pool = Database.get_pool()

    query = f"""
            SELECT *
            FROM {TABLE_NAME}
    """
    conditions = []
    values = []
    idx = 1
    
    if doctor_name:
        conditions.append(f"doctor_name = ${idx}")
        values.append(doctor_name.lower().strip())
        idx += 1

    if date_slot:
        conditions.append(f"date_slot = ${idx}")
        values.append(datetime.strptime(date_slot, "%m/%d/%Y %H:%M"))
        idx += 1

    if conditions:
        query += "WHERE " + " AND ".join(conditions)
    
    query += " LIMIT 1"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *values, timeout = 2.0)
    if row is None:
        return {
            "found": False,
            "is_available": False,
            "patient_to_attend": ""
        }


    return {
        "found": True,
        "is_available": bool(row["is_available"]),
        "patient_to_attend": row["patient_to_attend"]
    }

@tool
async def list_doctors_by_specialization(specialization: str)-> list:
    """
    Return distinc doctor names for a given specialization.
    
    Args: 
        specialization: e.g. 'orthodentist'
    
    Returns:
        Sorted list of doctor name strings.
    """
    pool = Database.get_pool()

    query = f"""
            SELECT DISTINCT doctor_name
            FROM {TABLE_NAME}
            WHERE specialization = $1
            ORDER by doctor_name ASC
"""
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, specialization.lower().strip())

    doctor_names = [r["doctor_name"] for r in rows]

    return doctor_names
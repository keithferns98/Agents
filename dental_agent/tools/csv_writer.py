from langchain.tools import tool
from dental_agent.db.conn_db import Database
from datetime import datetime

TABLE_NAME = "doctor_schedule_appointment"

@tool
async def book_appointment(patient_id: str, doctor_name: str, date_slot: str) -> dict:
    """
    Book an appointment: mark slot as unavailable and assign patient_id.
    Args:
        patient_id: Numeric patient ID string, e.g. '1000082'.
        doctor_name: Doctor name (case-insensitive), e.g. 'emily johnson'.
        date_slot: Slot in M/D/YYYY H:MM format, e.g. '5/10/2026 9:00'.
    Returns:
        Dict with keys: success (bool), message (str).
    """
    pool = Database.get_pool()
    try:
        target_dt = datetime.strptime(date_slot, "%m/%d/%Y %H:%M")
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}
    
    print(target_dt)

    doc = doctor_name.lower().strip()
    patient_id = int(patient_id.strip())

    query = f"""
    UPDATE {TABLE_NAME}
    SET is_available = FALSE,
        patient_to_attend = $1
    WHERE doctor_name = $2
    AND date_slot = $3
    AND is_available = TRUE
    RETURNING doctor_name
"""

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query,
                                  patient_id,
                                  doc,
                                  target_dt)
    if row == "UPDATE 0":
        return {
            "success": False,
            "message": "Slot not found or already booked."
        }

    return {
        "success": True,
        "message": f"Appointment booked for patient {patient_id} with {doctor_name} at {date_slot}.",
    }

@tool 
async def cancel_appointment(patient_id: str, date_slot: str)-> dict:
    """
    Cancel an appointment: mark slot available and clear patient_id.

    Args:
        patient_id: Patient whose appointment to cancel.
        date_slot: Slot in M/D/YYYY H:MM format to cancel.

    Returns:
        Dict with keys: success (bool), message (str).
    """
    pool = Database.get_pool()

    try:
        target_dt = datetime.strptime(date_slot, "%m/%d/%Y %H:%M")
    except Exception:
        return {"success": False, "message": f"Invalid date_slot format: {date_slot}"}
    
    pid = int(patient_id.strip())

    query =f"""UPDATE {TABLE_NAME}
            SET is_available = TRUE,
                patient_to_attend = NULL
            WHERE patient_to_attend = $1
            AND date_slot = $2
            AND is_available = FALSE
            RETURNING 1
"""
    async with pool.acquire() as conn:
        async with conn.transaction():
            result = await conn.fetchrow(query,
                                      pid,
                                      target_dt)
    if not result:
        return {
            "success": False,
            "message": f"No booked appointment found for patient {patient_id} at {date_slot}.",
        }
    return {
        "success": True,
        "message": f"Appointment at {date_slot} for patient {patient_id} has been cancelled.",
    }

@tool
async def reschedule_appointment(patient_id: str, 
                                 current_date_slot: str,
                                 new_date_slot: str,
                                 doctor_name: str):
    """
    Reschedule by cancelling the old slot and booking a new one atomically.

    Args:
        patient_id: Patient whose appointment to reschedule.
        current_date_slot: Existing booked slot to vacate (M/D/YYYY H:MM).
        new_date_slot: Desired new slot (M/D/YYYY H:MM).
        doctor_name: Doctor name (must match the booking's doctor).

    Returns:
        Dict with keys: success (bool), message (str).
    """
    pool = Database.get_pool()
    try:
        current_dt = datetime.strptime(current_date_slot, "%m/%d/%Y %H:%M")
        new_dt = datetime.strptime(new_date_slot, "%m/%d/%Y %H:%M")
    except Exception as exc:
        return {"success": False, "message": f"Date parse error: {exc}"}
    
    try:
        pid = int(patient_id.strip())
    except ValueError:
        return {"success": False, "message": f"Invalid patient_id: {patient_id}"}
    
    doc = doctor_name.lower().strip()
    async with pool.acquire() as conn:
        async with conn.transaction():  
            old_row = await conn.fetchrow(
                f"""
                SELECT id
                FROM {TABLE_NAME}
                WHERE patient_to_attend = $1
                AND date_slot = $2
                AND is_available = FALSE
                """,
                pid,
                current_dt
            )

            if not old_row:
                return {
                    "success": False,
                    "message": f"No existing booking found for patient {pid} at {current_date_slot}.",
                }

            new_row = await conn.fetchrow(
                f"""
                UPDATE {TABLE_NAME}
                SET is_available = FALSE,
                    patient_to_attend = $1
                WHERE doctor_name = $2
                AND date_slot = $3
                AND is_available = TRUE
                RETURNING id
                """,
                pid,
                doc,
                new_dt
            )

            if not new_row:
                return {
                    "success": False,
                    "message": f"Slot {new_date_slot} is unavailable or does not exist.",
                }

            # 3️⃣ Cancel old slot
            await conn.execute(
                f"""
                UPDATE {TABLE_NAME}
                SET is_available = TRUE,
                    patient_to_attend = NULL
                WHERE id = $1
                """,
                old_row["id"]
            )

    return {
        "success": True,
        "message": (
            f"Appointment for patient {pid} rescheduled from "
            f"{current_date_slot} to {new_date_slot} with {doctor_name}."
        ),
    }
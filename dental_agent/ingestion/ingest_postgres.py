import asyncpg
import logging
import time, asyncio
from dental_agent.config.creds_vault import *
from pathlib import Path

# =========================
# CONFIG
# =========================
DB_CONFIG = {
    "database": DBNAME,
    "user": USER,
    "password": PASSWORD,
    "host": HOST,
    "port": PORT
}

TABLE_NAME = "doctor_schedule_appointment"
MAX_RETRIES = 3

# =========================
# LOGGING
# =========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =========================
# CREATE TABLE
# =========================
async def create_table(pool):
    query = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        date_slot TIMESTAMP,
        specialization TEXT,
        doctor_name TEXT,
        is_available BOOLEAN,
        patient_to_attend BIGINT
    );
    """

    async with pool.acquire() as conn:
        await conn.execute(query)

    logger.info("Table ensured.")


# =========================
# COPY CSV (RAW INGEST)
# =========================
async def copy_csv(pool, file_path):
    retries = 0

    while retries < MAX_RETRIES:
        try:
            async with pool.acquire() as conn:
                await conn.copy_to_table(
                    TABLE_NAME,
                    source=file_path,
                    format="csv",
                    header=True
                )

            logger.info("✅ File ingested successfully")
            return

        except Exception as e:
            retries += 1
            logger.error(f"Retry {retries}: {e}")
            await asyncio.sleep(2)

    raise Exception("❌ Failed after retries")


# =========================
# INGEST FUNCTION
# =========================
async def ingest(file_path, pool):
    logger.info("Starting async ingestion...")

    await create_table(pool)
    await copy_csv(pool, file_path)

    logger.info("🚀 Ingestion completed")


# =========================
# STANDALONE RUN
# =========================
async def main(file_path):
    pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=10)
    try:
        await ingest(file_path, pool)
    finally:
        await pool.close()


if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    # print(BASE_DIR)
    file_path = BASE_DIR / "doctor_availability.csv"
    asyncio.run(main(file_path))
import asyncpg
from dotenv import load_dotenv
import os 

load_dotenv()


class Database:
    _pool = None

    @classmethod
    async def init(cls):
        if cls._pool is None:
            cls._pool = await asyncpg.create_pool(
                user=os.getenv("USER"),
                password=os.getenv("PASSWORD"),
                database=os.getenv("DBNAME"),
                host=os.getenv("HOST"),
                port=os.getenv("PORT"),
                min_size=5,
                max_size=20
            )

    @classmethod
    def get_pool(cls):
        if cls._pool is None:
            raise RuntimeError("Database not initialized. Call Database.init() first.")
        return cls._pool

    @classmethod
    async def close(cls):
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
import os

import asyncpg


pool = None


async def connect():
    global pool

    dsn = os.getenv("POSTGRES_DSN")

    if not dsn:
        raise RuntimeError("PostgreSQL environment variables are not configured")

    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=5)


def get_pool():
    if pool is None:
        raise RuntimeError("PostgreSQL pool is not initialized")

    return pool


async def close():
    global pool

    if pool is not None:
        await pool.close()
        pool = None
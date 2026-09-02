import os

import redis.asyncio as redis


client = None


async def connect():
    global client

    url = os.getenv("REDIS_URL")

    if not url:
        raise RuntimeError("Redis environment variables are not configured")

    client = redis.Redis.from_url(url, decode_responses=True)

    await client.ping()


def get_client():
    if client is None:
        raise RuntimeError("Redis client is not initialized")

    return client


async def close():
    global client

    if client is not None:
        await client.aclose()
        client = None
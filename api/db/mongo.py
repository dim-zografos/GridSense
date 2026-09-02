import os

from motor.motor_asyncio import AsyncIOMotorClient


client = None
database = None


async def connect():
    global client, database

    uri = os.getenv("MONGO_URI")
    database_name = os.getenv("MONGO_DATABASE")

    if not uri or not database_name:
        raise RuntimeError("MongoDB environment variables are not configured")

    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
    await client.admin.command("ping")
    database = client[database_name]


def get_database():
    if database is None:
        raise RuntimeError("MongoDB database is not initialized")

    return database


async def close():
    global client, database

    if client is not None:
        client.close()

    database = None
    client = None
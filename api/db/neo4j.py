import os
from neo4j import AsyncGraphDatabase

driver = None

async def connect():
    global driver

    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not user or not password: raise RuntimeError("Neo4j environment variables are not configured")

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    await driver.verify_connectivity()

def get_driver():
    if driver is None:
        raise RuntimeError("Neo4j driver is not initialized")

    return driver

async def close():
    global driver

    if driver is not None:
        await driver.close()
        driver = None
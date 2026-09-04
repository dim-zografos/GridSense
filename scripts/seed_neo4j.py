import os
from neo4j import AsyncGraphDatabase


async def seed_neo4j():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    seed_path = os.path.join(os.path.dirname(__file__), "../neo4j/import/seed.cypher")

    with open(seed_path, "r", encoding="utf-8") as file: cypher = file.read()

    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))

    try:
        async with driver.session() as session:
            for statement in cypher.split(";"):
                statement = statement.strip()

                if statement:
                    result = await session.run(statement)
                    await result.consume()

        print("Neo4j seeded successfully")

    finally:
        await driver.close()
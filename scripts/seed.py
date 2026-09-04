import asyncio
from seed_cassandra import seed_cassandra
from seed_neo4j import seed_neo4j
from seed_mongo import seed_mongo
from seed_postgres import seed_postgres

async def main():
    seed_cassandra()
    await seed_neo4j()
    await seed_mongo()
    await seed_postgres()

if __name__ == "__main__":
    asyncio.run(main())
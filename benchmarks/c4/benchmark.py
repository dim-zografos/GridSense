# C4 - MongoDB vs PostgreSQL JSONB Benchmark

# This benchmark compares query execution time between MongoDB
# and PostgreSQL JSONB using the same 30 equipment records.

# Three queries are tested:
# 1. firmware_version starts with "3."
# 2. SmartMeter equipment with rated_voltage greater than 230
# 3. count equipment grouped by type

# Each query is executed 10 times against each database.
# The benchmark prints the mean execution time.

# The result of each query is also checked to make sure both
# databases return the same data.

import asyncio
import os
import statistics
import time
import asyncpg
from motor.motor_asyncio import AsyncIOMotorClient

RUNS = 10

async def measure(query):
    times = []
    result = None

    for i in range(RUNS):
        start = time.perf_counter()
        result = await query()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    return statistics.mean(times), result

async def main():
    mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
    mongo_database = mongo_client[os.getenv("MONGO_DATABASE")]
    collection = mongo_database["equipment"]

    postgres = await asyncpg.connect(os.getenv("POSTGRES_DSN"))

    async def mongo_query_1():
        return await collection.find(
            {"firmware_version": {"$regex": "^3\\."}},
            {"_id": 0, "asset_id": 1}
        ).to_list(length=None)

    async def mongo_query_2():
        return await collection.find(
            {
                "type": "SmartMeter",
                "rated_voltage": {"$gt": 230}
            },
            {"_id": 0, "asset_id": 1}
        ).to_list(length=None)

    async def mongo_query_3():
        return await collection.aggregate([
            {
                "$group": {
                    "_id": "$type",
                    "count": {"$sum": 1}
                }
            }
        ]).to_list(length=None)

    async def postgres_query_1():
        return await postgres.fetch("""
            SELECT asset_id
            FROM equipment_jsonb
            WHERE metadata ? 'firmware_version'
              AND metadata->>'firmware_version' LIKE '3.%'
        """)

    async def postgres_query_2():
        return await postgres.fetch("""
            SELECT asset_id
            FROM equipment_jsonb
            WHERE metadata->>'type' = 'SmartMeter'
              AND (metadata->>'rated_voltage')::numeric > 230
        """)

    async def postgres_query_3():
        return await postgres.fetch("""
            SELECT metadata->>'type' AS type, COUNT(*) AS count
            FROM equipment_jsonb
            GROUP BY metadata->>'type'
        """)

    await mongo_database.command("ping")
    await postgres.fetchval("SELECT 1")

    await mongo_query_1()
    await postgres_query_1()
    await mongo_query_2()
    await postgres_query_2()
    await mongo_query_3()
    await postgres_query_3()

    mongo_1, mongo_result_1 = await measure(mongo_query_1)
    postgres_1, postgres_result_1 = await measure(postgres_query_1)

    mongo_2, mongo_result_2 = await measure(mongo_query_2)
    postgres_2, postgres_result_2 = await measure(postgres_query_2)

    mongo_3, mongo_result_3 = await measure(mongo_query_3)
    postgres_3, postgres_result_3 = await measure(postgres_query_3)

    mongo_ids_1 = {row["asset_id"] for row in mongo_result_1}
    postgres_ids_1 = {row["asset_id"] for row in postgres_result_1}

    mongo_ids_2 = {row["asset_id"] for row in mongo_result_2}
    postgres_ids_2 = {row["asset_id"] for row in postgres_result_2}

    mongo_groups = {
        row["_id"]: row["count"]
        for row in mongo_result_3
    }

    postgres_groups = {
        row["type"]: row["count"]
        for row in postgres_result_3
    }

    print(f"Query 1: MongoDB={mongo_1:.3f} ms, PostgreSQL={postgres_1:.3f} ms, same_results={mongo_ids_1 == postgres_ids_1}")
    print(f"Query 2: MongoDB={mongo_2:.3f} ms, PostgreSQL={postgres_2:.3f} ms, same_results={mongo_ids_2 == postgres_ids_2}")
    print(f"Query 3: MongoDB={mongo_3:.3f} ms, PostgreSQL={postgres_3:.3f} ms, same_results={mongo_groups == postgres_groups}")

    print(f"Query 1 results: {len(mongo_ids_1)}")
    print(f"Query 2 results: {len(mongo_ids_2)}")
    print(f"Query 3 results: {mongo_groups}")

    await postgres.close()
    mongo_client.close()

asyncio.run(main())
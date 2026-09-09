# C4 - PostgreSQL JSONB Equipment Seed

# This script prepares the PostgreSQL dataset required for the C4 benchmark.
# It creates the same 30 equipment records used by the MongoDB seed:
# - 10 SmartMeters
# - 10 Transformers
# - 10 Switchgear units

# The records are stored in PostgreSQL using an asset_id primary key
# and a JSONB metadata column.

# The script is idempotent. Running it again updates the existing
# records instead of creating duplicates.

import asyncio
import json
import os
import asyncpg

async def main():
    connection = await asyncpg.connect(os.getenv("POSTGRES_DSN"))

    await connection.execute("""
        CREATE TABLE IF NOT EXISTS equipment_jsonb (
            asset_id VARCHAR(50) PRIMARY KEY,
            metadata JSONB NOT NULL
        )
    """)

    equipment = []

    for i in range(1, 11):
        equipment.append({
            "asset_id": f"SM_{i:05d}",
            "equipment_type": "SmartMeter",
            "type": "SmartMeter",
            "manufacturer": "Landis+Gyr",
            "model": f"E360-{i}",
            "firmware_version": f"3.{i}.0" if i % 2 == 0 else f"2.{i}.0",
            "rated_voltage": 230 + (i % 3) * 5,
            "phase": "three" if i % 4 == 0 else "single",
            "protocol": "DLMS/COSEM",
        })

    transformer_ids = [
        f"TX_{substation:03d}_{letter}"
        for substation in range(1, 4)
        for letter in "ABCD"
    ][:10]

    for i, asset_id in enumerate(transformer_ids, start=1):
        equipment.append({
            "asset_id": asset_id,
            "equipment_type": "Transformer",
            "type": "Transformer",
            "manufacturer": "ABB",
            "model": f"ONAN-{i}",
            "rating_kVA": 400 + i * 50,
            "primary_voltage_kV": 11,
            "secondary_voltage_V": 400,
            "cooling_type": "ONAN",
            "oil_capacity_litres": 300 + i * 10,
        })

    for i in range(1, 11):
        equipment.append({
            "asset_id": f"SW_{i:03d}",
            "equipment_type": "Switchgear",
            "type": "Switchgear",
            "manufacturer": "Schneider Electric",
            "model": f"SW-{i}",
            "rated_current_A": 630 + i * 10,
            "breaking_capacity_kA": 20 + i,
            "insulation_type": "SF6" if i % 2 == 0 else "Air",
            "poles": 3,
        })

    for document in equipment:
        asset_id = document["asset_id"]

        metadata = document.copy()
        metadata.pop("asset_id")

        await connection.execute(
            """
            INSERT INTO equipment_jsonb (
                asset_id,
                metadata
            )
            VALUES ($1, $2::jsonb)
            ON CONFLICT (asset_id)
            DO UPDATE SET
                metadata = EXCLUDED.metadata
            """,
            asset_id,
            json.dumps(metadata),
        )

    count = await connection.fetchval(
        "SELECT COUNT(*) FROM equipment_jsonb"
    )

    print(f"PostgreSQL JSONB seeded successfully: {count} equipment records")

    await connection.close()

asyncio.run(main())
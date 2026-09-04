import os
from motor.motor_asyncio import AsyncIOMotorClient

async def seed_mongo():
    print("Seeding MongoDB...")

    uri = os.getenv("MONGO_URI")
    database_name = os.getenv("MONGO_DATABASE")

    if not uri or not database_name:
        raise RuntimeError("MongoDB environment variables are not configured")

    client = AsyncIOMotorClient(uri)
    database = client[database_name]
    collection = database["equipment"]

    try:
        equipment = []

        # 10 Smart Meters
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

        # 10 Transformers
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

        # 10 Switchgear units
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
            await collection.replace_one(
                {"asset_id": document["asset_id"]},
                document,
                upsert=True,
            )

        print( "MongoDB seeded successfully: 30 equipment records across 3 types")

    finally:
        client.close()
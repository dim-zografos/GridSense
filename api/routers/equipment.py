from fastapi import APIRouter, HTTPException
from db.mongo import get_database
from models.mongo import EquipmentCreate, EquipmentResponse, EquipmentPatch


router = APIRouter(prefix="/equipment")


@router.post("", response_model=EquipmentResponse, status_code=201)
async def create_equipment(equipment: EquipmentCreate):
    database = get_database()
    collection = database["equipment"]

    existing = await collection.find_one({"asset_id": equipment.asset_id})

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Equipment '{equipment.asset_id}' already exists"
        )

    document = equipment.model_dump()
    await collection.insert_one(document)
    document.pop("_id", None)
    return document

@router.get("/{asset_id}", response_model=EquipmentResponse)
async def get_equipment(asset_id: str):
    database = get_database()
    collection = database["equipment"]

    document = await collection.find_one(
        {"asset_id": asset_id},
        {"_id": 0}
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Equipment '{asset_id}' not found"
        )

    return document

@router.patch("/{asset_id}", response_model=EquipmentResponse)
async def patch_equipment(asset_id: str, equipment: EquipmentPatch):
    database = get_database()
    collection = database["equipment"]

    document = await collection.find_one(
        {"asset_id": asset_id},
        {"_id": 0}
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail=f"Equipment '{asset_id}' not found"
        )

    update_data = equipment.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields supplied for update"
        )

    if "asset_id" in update_data:
        raise HTTPException(
            status_code=400,
            detail="asset_id cannot be changed"
        )

    if "_id" in update_data:
        raise HTTPException(
            status_code=400,
            detail="_id cannot be changed"
        )

    await collection.update_one(
        {"asset_id": asset_id},
        {"$set": update_data}
    )

    updated_document = await collection.find_one(
        {"asset_id": asset_id},
        {"_id": 0}
    )

    return updated_document
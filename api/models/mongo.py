from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class EquipmentCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    asset_id: str = Field(min_length=1)
    equipment_type: str = Field(min_length=1)


class EquipmentPatch(BaseModel):
    model_config = ConfigDict(extra="allow")


class EquipmentResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    asset_id: str
    equipment_type: str
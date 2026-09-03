from typing import Annotated, ClassVar, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from datetime import date

class AffectedNode(BaseModel):
    node_id: str
    node_type: str
    name: str
    depth: int

class FaultImpactResponse(BaseModel):
    origin_id: str
    affected_nodes: list[AffectedNode]
    total_affected: int

class RestorePath(BaseModel):
    source_id: str
    path_nodes: list[str]
    hops: int
    active: bool

class RestorePathsResponse(BaseModel):
    node_id: str
    paths: list[RestorePath]
    total_paths: int

class GraphNodeBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mandatory_fields: ClassVar[tuple[str, ...]]
    requirements_message: ClassVar[str]

    node_id: str = Field(min_length=1)
    name: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def validate_mandatory_fields(cls, data):
        if not isinstance(data, dict):
            return data

        missing = [
            field
            for field in cls.mandatory_fields
            if field not in data
            or data[field] is None
            or (
                isinstance(data[field], str)
                and not data[field].strip()
            )
        ]

        if missing:
            raise ValueError(cls.requirements_message)

        return data

class GridSupplyPointCreate(GraphNodeBase):
    mandatory_fields = (
        "node_type",
        "node_id",
        "name",
        "gsp_id",
        "voltage_kV",
        "region",
    )

    node_type: Literal["GridSupplyPoint"]

    gsp_id: str = Field(min_length=1)
    voltage_kV: float = Field(gt=0)
    region: str = Field(min_length=1)
    requirements_message = (
    "Required fields for GridSupplyPoint: "
    "node_type='GridSupplyPoint', "
    "node_id=non-empty string, "
    "name=non-empty string, "
    "gsp_id=non-empty string, "
    "voltage_kV>0, "
    "region=non-empty string."
    )

class SubstationCreate(GraphNodeBase):
    mandatory_fields = (
        "node_type",
        "node_id",
        "name",
        "substation_id",
        "voltage_kV",
        "lat",
        "lon",
        "commissioned_year",
    )

    node_type: Literal["Substation"]

    substation_id: str = Field(min_length=1)
    voltage_kV: float = Field(gt=0)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    commissioned_year: int = Field(gt=0)
    requirements_message = (
    "Required fields for Substation: "
    "node_type='Substation', "
    "node_id=non-empty string, "
    "name=non-empty string, "
    "substation_id=non-empty string, "
    "voltage_kV>0, "
    "lat=-90..90, "
    "lon=-180..180, "
    "commissioned_year>0."
    )

class TransformerCreate(GraphNodeBase):
    mandatory_fields = (
        "node_type",
        "node_id",
        "name",
        "asset_id",
        "rating_kVA",
        "manufacturer",
        "model",
        "installed",
        "last_inspection",
    )

    node_type: Literal["Transformer"]

    asset_id: str = Field(min_length=1)
    rating_kVA: float = Field(gt=0)
    manufacturer: str = Field(min_length=1)
    model: str = Field(min_length=1)
    installed: date
    last_inspection: date
    requirements_message = (
    "Required fields for Transformer: "
    "node_type='Transformer', "
    "node_id=non-empty string, "
    "name=non-empty string, "
    "asset_id=non-empty string, "
    "rating_kVA>0, "
    "manufacturer=non-empty string, "
    "model=non-empty string, "
    "installed=valid date, "
    "last_inspection=valid date."
    )

class SmartMeterCreate(GraphNodeBase):
    mandatory_fields = (
        "node_type",
        "node_id",
        "name",
        "meter_id",
        "premise_id",
        "tariff_class",
        "phase",
    )

    node_type: Literal["SmartMeter"]

    meter_id: str = Field(min_length=1)
    premise_id: str = Field(min_length=1)
    tariff_class: Literal["residential", "commercial"]
    phase: Literal["single", "three"]
    requirements_message = (
    "Required fields for SmartMeter: "
    "node_type='SmartMeter', "
    "node_id=non-empty string, "
    "name=non-empty string, "
    "meter_id=non-empty string, "
    "premise_id=non-empty string, "
    "tariff_class='residential' or 'commercial', "
    "phase='single' or 'three'."
    )

NodeCreate = Annotated[
    GridSupplyPointCreate
    | SubstationCreate
    | TransformerCreate
    | SmartMeterCreate,
    Field(discriminator="node_type"),
]

class RelationshipBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_id: str = Field(min_length=1)
    to_id: str = Field(min_length=1)
    active: bool


class FeedsRelationshipCreate(RelationshipBase):
    relationship_type: Literal["FEEDS"]

    feeder_id: str = Field(min_length=1)
    voltage_kV: float = Field(gt=0)
    length_km: float = Field(gt=0)


class SuppliesRelationshipCreate(RelationshipBase):
    relationship_type: Literal["SUPPLIES"]

    cable_id: str = Field(min_length=1)
    distance_m: float = Field(gt=0)


class ConnectsToRelationshipCreate(RelationshipBase):
    relationship_type: Literal["CONNECTS_TO"]


RelationshipCreate = Annotated[
    FeedsRelationshipCreate
    | SuppliesRelationshipCreate
    | ConnectsToRelationshipCreate,
    Field(discriminator="relationship_type"),
]

class NodeCreateResponse(BaseModel):
    message: str
    node_id: str
    node_type: str

class RelationshipCreateResponse(BaseModel):
    message: str
    from_id: str
    to_id: str
    relationship_type: str
from enum import StrEnum
from pydantic import BaseModel, model_serializer
from typing import Any


class DiamondCut(StrEnum):
    Ideal = "Ideal"
    Premium = "Premium"
    Good = "Good"
    VeryGood = "Very Good"
    Fair = "Fair"


class DiamondColor(StrEnum):
    D = "D"
    E = "E"
    F = "F"
    G = "G"
    H = "H"
    I = "I"  # noqa
    J = "J"


class DiamondClarity(StrEnum):
    IF = "IF"
    VVS1 = "VVS1"
    VVS2 = "VVS2"
    VS1 = "VS1"
    VS2 = "VS2"
    SI1 = "SI1"
    SI2 = "SI2"
    I1 = "I1"


class DiamondInput(BaseModel):
    depth: float
    table: float
    x: float
    y: float
    z: float
    cut: DiamondCut
    color: DiamondColor
    clarity: DiamondClarity
    price: float | None = None

    @model_serializer(mode="wrap")
    def serialize_model(self, handler) -> dict[str, Any]:
        result = handler(self)
        features_to_omit = ["x", "y", "z", "price"]
        return {k: v for k, v in result.items() if k not in features_to_omit}

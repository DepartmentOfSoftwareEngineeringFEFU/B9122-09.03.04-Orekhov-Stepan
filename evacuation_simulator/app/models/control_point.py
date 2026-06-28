from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .enums import ControlPointPurpose


@dataclass(slots=True)
class ControlPoint:
    id: int
    label: str
    x: int | None = None
    y: int | None = None
    purpose: ControlPointPurpose = ControlPointPurpose.BOTH
    path_segment: str | None = None

    @property
    def coord(self) -> tuple[int, int] | None:
        if self.x is None or self.y is None:
            return None
        return self.x, self.y

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "purpose": self.purpose.name,
            "path_segment": self.path_segment,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ControlPoint":
        return cls(
            id=int(data["id"]),
            label=str(data["label"]),
            x=data.get("x"),
            y=data.get("y"),
            purpose=ControlPointPurpose[data.get("purpose", "BOTH")],
            path_segment=data.get("path_segment"),
        )

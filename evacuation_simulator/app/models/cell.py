from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .enums import CellType, PathType


@dataclass(slots=True)
class Cell:

    id: int
    x: int
    y: int
    cell_type: CellType = CellType.FREE
    path_type: PathType = PathType.HORIZONTAL
    smoke_level: float = 0.0
    danger_level: float = 0.0
    local_area: float = 1.0
    occupied_by: int | None = None

    @property
    def occupied(self) -> bool:
        return self.occupied_by is not None

    @property
    def passable(self) -> bool:
        return self.is_static_passable and not self.occupied

    @property
    def is_static_passable(self) -> bool:
        return self.cell_type not in {CellType.WALL, CellType.OBSTACLE}

    @property
    def coord(self) -> tuple[int, int]:
        return self.x, self.y

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "cell_type": self.cell_type.name,
            "path_type": self.path_type.name,
            "smoke_level": self.smoke_level,
            "danger_level": self.danger_level,
            "local_area": self.local_area,
            "occupied_by": self.occupied_by,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Cell":
        return cls(
            id=int(data["id"]),
            x=int(data["x"]),
            y=int(data["y"]),
            cell_type=CellType[data.get("cell_type", "FREE")],
            path_type=PathType[data.get("path_type", "HORIZONTAL")],
            smoke_level=float(data.get("smoke_level", 0.0)),
            danger_level=float(data.get("danger_level", 0.0)),
            local_area=float(data.get("local_area", 1.0)),
            occupied_by=data.get("occupied_by"),
        )

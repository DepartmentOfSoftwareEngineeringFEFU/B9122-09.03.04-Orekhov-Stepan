from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import ExitStatus


@dataclass(slots=True)
class Exit:

    id: int
    cells: set[tuple[int, int]]
    width: float
    status: ExitStatus = ExitStatus.OPEN
    capacity: int = 1
    is_doorway: bool = True
    passage_coefficient: float = 1.0

    def is_available(self) -> bool:
        return self.status == ExitStatus.OPEN

    def step_capacity(self, dt: float) -> int:
        return max(1, int(self.capacity * dt))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cells": [list(cell) for cell in sorted(self.cells)],
            "width": self.width,
            "status": self.status.name,
            "capacity": self.capacity,
            "is_doorway": self.is_doorway,
            "passage_coefficient": self.passage_coefficient,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Exit":
        return cls(
            id=int(data["id"]),
            cells={tuple(cell) for cell in data.get("cells", [])},
            width=float(data["width"]),
            status=ExitStatus[data.get("status", "OPEN")],
            capacity=int(data.get("capacity", 1)),
            is_doorway=bool(data.get("is_doorway", True)),
            passage_coefficient=float(data.get("passage_coefficient", 1.0)),
        )

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Obstacle:
    id: int
    type: str
    cells: set[tuple[int, int]]

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "type": self.type, "cells": [list(cell) for cell in sorted(self.cells)]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Obstacle":
        return cls(id=int(data["id"]), type=str(data.get("type", "препятствие")), cells={tuple(c) for c in data.get("cells", [])})

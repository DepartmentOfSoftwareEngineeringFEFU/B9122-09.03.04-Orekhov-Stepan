from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import EventType


@dataclass(slots=True)
class EnvironmentEvent:
    id: int
    type: EventType
    time: float
    area: set[tuple[int, int]] = field(default_factory=set)
    params: dict[str, Any] = field(default_factory=dict)
    applied: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not isinstance(self.type, EventType):
            errors.append("Некорректный тип события")
        if self.time < 0:
            errors.append("Время события не может быть отрицательным")
        if self.type == EventType.CHANGE_SMOKE and "smoke_level" in self.params:
            level = float(self.params["smoke_level"])
            if level < 0 or level > 1:
                errors.append("Уровень задымления должен быть в диапазоне [0, 1]")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.name,
            "time": self.time,
            "area": [list(c) for c in sorted(self.area)],
            "params": self.params,
            "applied": self.applied,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EnvironmentEvent":
        return cls(
            id=int(data["id"]),
            type=EventType[data["type"]],
            time=float(data["time"]),
            area={tuple(c) for c in data.get("area", [])},
            params=dict(data.get("params", {})),
            applied=bool(data.get("applied", False)),
        )

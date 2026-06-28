from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import AgentState, ClothesType, MobilityGroup, MobilityLevel


@dataclass(slots=True)
class Agent:

    id: int
    current_cell: tuple[int, int]
    start_cell: tuple[int, int] | None = None
    base_speed: float = 1.25
    mobility_group: MobilityGroup = MobilityGroup.M0_3
    mobility_level: MobilityLevel = MobilityLevel.HIGH
    clothes_type: ClothesType = ClothesType.SUMMER
    base_projection_area: float = 0.100
    effective_projection_area: float = 0.100
    ellipse_axis_a: float = 0.28
    ellipse_axis_c: float = 0.46
    move_budget: float = 0.0
    state: AgentState = AgentState.WAITING
    trajectory: list[tuple[int, int]] = field(default_factory=list)
    evacuation_time: float | None = None
    chosen_exit_id: int | None = None
    reason_if_not_evacuated: str = ""

    def __post_init__(self) -> None:
        if self.start_cell is None:
            self.start_cell = self.current_cell
        self.recalculate_effective_area()

    def recalculate_effective_area(self) -> None:
        factor = 1.25 if self.clothes_type == ClothesType.WINTER else 1.0
        self.effective_projection_area = self.base_projection_area * factor

    def can_move_independently(self) -> bool:
        return self.mobility_group not in {MobilityGroup.NM, MobilityGroup.NT}

    def apply_norm(self, norm: Any) -> None:
        self.base_speed = norm.free_speed_v0
        self.base_projection_area = norm.base_projection_area
        self.ellipse_axis_a = norm.ellipse_axis_a
        self.ellipse_axis_c = norm.ellipse_axis_c
        self.recalculate_effective_area()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "current_cell": list(self.current_cell),
            "start_cell": list(self.start_cell) if self.start_cell else None,
            "base_speed": self.base_speed,
            "mobility_group": self.mobility_group.name,
            "mobility_level": self.mobility_level.name,
            "clothes_type": self.clothes_type.name,
            "base_projection_area": self.base_projection_area,
            "effective_projection_area": self.effective_projection_area,
            "ellipse_axis_a": self.ellipse_axis_a,
            "ellipse_axis_c": self.ellipse_axis_c,
            "move_budget": self.move_budget,
            "state": self.state.name,
            "trajectory": [list(c) for c in self.trajectory],
            "evacuation_time": self.evacuation_time,
            "chosen_exit_id": self.chosen_exit_id,
            "reason_if_not_evacuated": self.reason_if_not_evacuated,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Agent":
        return cls(
            id=int(data["id"]),
            current_cell=tuple(data["current_cell"]),
            start_cell=tuple(data["start_cell"]) if data.get("start_cell") else None,
            base_speed=float(data.get("base_speed", 1.25)),
            mobility_group=MobilityGroup[data.get("mobility_group", "M0_3")],
            mobility_level=MobilityLevel[data.get("mobility_level", "HIGH")],
            clothes_type=ClothesType[data.get("clothes_type", "SUMMER")],
            base_projection_area=float(data.get("base_projection_area", 0.100)),
            effective_projection_area=float(data.get("effective_projection_area", 0.100)),
            ellipse_axis_a=float(data.get("ellipse_axis_a", 0.28)),
            ellipse_axis_c=float(data.get("ellipse_axis_c", 0.46)),
            move_budget=float(data.get("move_budget", 0.0)),
            state=AgentState[data.get("state", "WAITING")],
            trajectory=[tuple(c) for c in data.get("trajectory", [])],
            evacuation_time=data.get("evacuation_time"),
            chosen_exit_id=data.get("chosen_exit_id"),
            reason_if_not_evacuated=str(data.get("reason_if_not_evacuated", "")),
        )

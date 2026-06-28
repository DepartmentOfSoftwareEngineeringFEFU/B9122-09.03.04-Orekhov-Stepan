from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json

from .enums import MobilityGroup, PathType


@dataclass(frozen=True, slots=True)
class MovementNorm:
    mobility_group: MobilityGroup
    path_type: PathType
    free_speed_v0: float
    adaptation_ai: float
    density_d0: float
    base_projection_area: float
    ellipse_axis_a: float
    ellipse_axis_c: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "mobility_group": self.mobility_group.name,
            "path_type": self.path_type.name,
            "free_speed_v0": self.free_speed_v0,
            "adaptation_ai": self.adaptation_ai,
            "density_d0": self.density_d0,
            "base_projection_area": self.base_projection_area,
            "ellipse_axis_a": self.ellipse_axis_a,
            "ellipse_axis_c": self.ellipse_axis_c,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MovementNorm":
        return cls(
            mobility_group=MobilityGroup[data["mobility_group"]],
            path_type=PathType[data["path_type"]],
            free_speed_v0=float(data["free_speed_v0"]),
            adaptation_ai=float(data["adaptation_ai"]),
            density_d0=float(data["density_d0"]),
            base_projection_area=float(data["base_projection_area"]),
            ellipse_axis_a=float(data["ellipse_axis_a"]),
            ellipse_axis_c=float(data["ellipse_axis_c"]),
        )


class MovementNormTable:

    def __init__(self, norms: list[MovementNorm] | None = None) -> None:
        self._norms: dict[tuple[MobilityGroup, PathType], MovementNorm] = {}
        for norm in norms or []:
            self.add(norm)

    @classmethod
    def load_default(cls) -> "MovementNormTable":
        base_by_group: dict[MobilityGroup, tuple[float, float, float, float, float, float]] = {
            MobilityGroup.M0_1: (1.35, 0.295, 0.05, 0.075, 0.24, 0.40),
            MobilityGroup.M0_2: (1.30, 0.295, 0.05, 0.090, 0.26, 0.43),
            MobilityGroup.M0_3: (1.25, 0.295, 0.05, 0.100, 0.28, 0.46),
            MobilityGroup.M0_4: (1.15, 0.295, 0.05, 0.110, 0.30, 0.48),
            MobilityGroup.M0_5: (1.05, 0.295, 0.05, 0.125, 0.32, 0.50),
            MobilityGroup.M0_6: (0.95, 0.295, 0.05, 0.140, 0.34, 0.52),
            MobilityGroup.M0_7: (0.85, 0.295, 0.05, 0.160, 0.36, 0.55),
            MobilityGroup.M1: (0.80, 0.320, 0.05, 0.170, 0.38, 0.58),
            MobilityGroup.M2: (0.65, 0.340, 0.05, 0.220, 0.42, 0.70),
            MobilityGroup.M3: (0.50, 0.360, 0.05, 0.300, 0.50, 0.85),
            MobilityGroup.M4: (0.35, 0.380, 0.05, 0.960, 0.75, 1.20),
            MobilityGroup.NO: (0.60, 0.340, 0.05, 0.250, 0.45, 0.75),
        }
        modifiers = {
            PathType.HORIZONTAL: 1.00,
            PathType.DOORWAY: 0.95,
            PathType.STAIRS_DOWN: 0.75,
            PathType.STAIRS_UP: 0.65,
            PathType.RAMP: 0.80,
        }
        norms: list[MovementNorm] = []
        for group, values in base_by_group.items():
            v0, ai, d0, area, axis_a, axis_c = values
            for path_type, modifier in modifiers.items():
                norms.append(
                    MovementNorm(
                        mobility_group=group,
                        path_type=path_type,
                        free_speed_v0=v0 * modifier,
                        adaptation_ai=ai,
                        density_d0=d0,
                        base_projection_area=area,
                        ellipse_axis_a=axis_a,
                        ellipse_axis_c=axis_c,
                    )
                )
        return cls(norms)

    @classmethod
    def load_json(cls, path: str | Path) -> "MovementNormTable":
        items = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls([MovementNorm.from_dict(item) for item in items])

    def save_json(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_list(), ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, norm: MovementNorm) -> None:
        self._norms[(norm.mobility_group, norm.path_type)] = norm

    def get(self, group: MobilityGroup, path_type: PathType) -> MovementNorm:
        if group == MobilityGroup.M0:
            raise ValueError("Для группы М0 необходимо указать подгруппу")
        try:
            return self._norms[(group, path_type)]
        except KeyError as exc:
            raise KeyError("Нормативные параметры движения не найдены") from exc

    def validate_agent_params(self, agent: Any) -> list[str]:
        errors: list[str] = []
        if agent.mobility_group == MobilityGroup.M0:
            errors.append("Для группы М0 необходимо указать подгруппу")
        if agent.mobility_group not in {MobilityGroup.NM, MobilityGroup.NT, MobilityGroup.M0}:
            self.get(agent.mobility_group, PathType.HORIZONTAL)
        if agent.base_speed <= 0:
            errors.append("Скорость агента должна быть положительной")
        return errors

    def get_projection_area(self, group: MobilityGroup) -> float:
        return self.get(group, PathType.HORIZONTAL).base_projection_area

    def get_axes(self, group: MobilityGroup) -> tuple[float, float]:
        norm = self.get(group, PathType.HORIZONTAL)
        return norm.ellipse_axis_a, norm.ellipse_axis_c

    def to_list(self) -> list[dict[str, Any]]:
        return [norm.to_dict() for norm in self._norms.values()]

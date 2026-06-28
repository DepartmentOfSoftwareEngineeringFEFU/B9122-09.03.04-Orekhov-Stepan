from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt

from app.models import Agent, Cell, MovementNormTable, PathType


@dataclass(slots=True)
class MovementRequest:
    agent: Agent
    target: Cell
    cost: float
    step_length: float


class MovementCalculator:

    def __init__(self, norm_table: MovementNormTable) -> None:
        self.norm_table = norm_table

    @staticmethod
    def step_length(source: Cell, target: Cell, cell_size: float) -> float:
        dx = abs(source.x - target.x)
        dy = abs(source.y - target.y)
        return sqrt(2) * cell_size if dx == 1 and dy == 1 else cell_size

    @staticmethod
    def passage_coefficient(path_type: PathType, dnorm: float) -> float:
        if path_type != PathType.DOORWAY:
            return 1.0
        if dnorm < 0.5:
            return 1.0
        return max(0.0, 1.25 - 0.05 * dnorm)

    def calculate_speed(self, agent: Agent, cell: Cell, dnorm: float) -> float:
        norm = self.norm_table.get(agent.mobility_group, cell.path_type)
        if dnorm <= norm.density_d0:
            return norm.free_speed_v0
        m = self.passage_coefficient(cell.path_type, dnorm)
        speed = norm.free_speed_v0 * (1 - norm.adaptation_ai * log(max(dnorm, 1e-9) / norm.density_d0)) * m
        return max(0.0, speed)

    @staticmethod
    def transition_cost(
        cell: Cell,
        distance_to_exit: float,
        dnorm: float,
        alpha: float,
        beta: float,
        gamma: float,
    ) -> float:
        if not cell.is_static_passable:
            return float("inf")
        return distance_to_exit + alpha * cell.smoke_level + beta * dnorm + gamma * cell.danger_level

from __future__ import annotations

from app.models import Agent, AgentState, BuildingModel


class DensityAnalyzer:

    def __init__(self, building: BuildingModel, radius: int = 1) -> None:
        self.building = building
        self.radius = radius

    def local_area_cells(self, x: int, y: int) -> list[tuple[int, int]]:
        cells: list[tuple[int, int]] = []
        for yy in range(y - self.radius, y + self.radius + 1):
            for xx in range(x - self.radius, x + self.radius + 1):
                if self.building.in_bounds(xx, yy):
                    cells.append((xx, yy))
        return cells

    def calculate_cell_density(self, x: int, y: int, agents: list[Agent]) -> float:
        local_cells = set(self.local_area_cells(x, y))
        local_area = len(local_cells) * self.building.cell_size * self.building.cell_size
        if local_area <= 0:
            raise ValueError("Площадь локальной области должна быть положительной")
        projection_sum = sum(
            agent.effective_projection_area
            for agent in agents
            if agent.state == AgentState.MOVING and agent.current_cell in local_cells
        )
        return projection_sum / local_area

    def calculate_density_map(self, agents: list[Agent]) -> dict[tuple[int, int], float]:
        return {
            (cell.x, cell.y): self.calculate_cell_density(cell.x, cell.y, agents)
            for cell in self.building.iter_cells()
        }

    @staticmethod
    def normative_congestion(dnorm: float) -> bool:
        return dnorm > 0.5

    @staticmethod
    def user_congestion(dnorm: float, rho_crit: float) -> bool:
        return dnorm >= rho_crit

from __future__ import annotations

from heapq import heappop, heappush
from math import inf, sqrt

from app.models import BuildingModel, Cell, Exit


class PathFinder:

    def __init__(self, building: BuildingModel) -> None:
        self.building = building
        self._cache_key: tuple[tuple[tuple[int, str], ...], float, float] | None = None
        self._distance_map: dict[tuple[int, int], float] = {}

    def invalidate(self) -> None:
        self._cache_key = None
        self._distance_map = {}

    def distance_map(self, exits: list[Exit], alpha: float = 0.0, gamma: float = 0.0) -> dict[tuple[int, int], float]:
        key = (tuple(sorted((exit_obj.id, exit_obj.status.name) for exit_obj in exits)), alpha, gamma)
        if key == self._cache_key:
            return self._distance_map
        available = [exit_obj for exit_obj in exits if exit_obj.is_available()]
        distances = {(cell.x, cell.y): inf for cell in self.building.iter_cells()}
        queue: list[tuple[float, tuple[int, int]]] = []
        for exit_obj in available:
            for coord in exit_obj.cells:
                if self.building.in_bounds(*coord):
                    distances[coord] = 0.0
                    heappush(queue, (0.0, coord))
        while queue:
            distance, coord = heappop(queue)
            if distance > distances[coord]:
                continue
            source = self.building.get_cell(*coord)
            for neighbor in self.building.get_neighbors(source, moore=True):
                if not neighbor.is_static_passable:
                    continue
                step = sqrt(2) * self.building.cell_size if abs(source.x - neighbor.x) == 1 and abs(source.y - neighbor.y) == 1 else self.building.cell_size
                route_risk = alpha * source.smoke_level + gamma * source.danger_level
                candidate = distance + step + route_risk
                ncoord = (neighbor.x, neighbor.y)
                if candidate < distances[ncoord]:
                    distances[ncoord] = candidate
                    heappush(queue, (candidate, ncoord))
        self._cache_key = key
        self._distance_map = distances
        return distances

    def has_path(self, cell: Cell, exits: list[Exit]) -> bool:
        return self.distance_map(exits).get((cell.x, cell.y), inf) < inf

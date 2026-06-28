from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any

import numpy as np

from .cell import Cell
from .control_point import ControlPoint
from .enums import CellType, PathType
from .exit import Exit
from .obstacle import Obstacle


@dataclass
class BuildingModel:

    id: int | None
    name: str
    width: float
    height: float
    cell_size: float
    grid: np.ndarray = field(default_factory=lambda: np.empty((0, 0), dtype=object))
    exits: list[Exit] = field(default_factory=list)
    obstacles: list[Obstacle] = field(default_factory=list)
    control_points: list[ControlPoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.grid.size == 0 and self.width > 0 and self.height > 0 and self.cell_size > 0:
            self.create_grid()

    @property
    def cols(self) -> int:
        return ceil(self.width / self.cell_size)

    @property
    def rows(self) -> int:
        return ceil(self.height / self.cell_size)

    def create_grid(self) -> None:
        if not self.name.strip():
            raise ValueError("Не задано название модели")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Размеры модели должны быть положительными")
        if self.cell_size <= 0:
            raise ValueError("Шаг клеточного разбиения должен быть положительным")
        if self.cell_size > min(self.width, self.height):
            raise ValueError("Шаг клеточного разбиения превышает размер модели")
        self.grid = np.empty((self.rows, self.cols), dtype=object)
        cell_id = 1
        area = self.cell_size * self.cell_size
        for y in range(self.rows):
            for x in range(self.cols):
                self.grid[y, x] = Cell(id=cell_id, x=x, y=y, local_area=area)
                cell_id += 1

    def get_cell(self, x: int, y: int) -> Cell:
        if not self.in_bounds(x, y):
            raise ValueError("Координаты клетки вне модели")
        return self.grid[y, x]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.cols and 0 <= y < self.rows

    def set_cell_state(self, x: int, y: int, state: CellType, path_type: PathType | None = None) -> None:
        if not isinstance(state, CellType):
            raise ValueError("Некорректное состояние клетки")
        cell = self.get_cell(x, y)
        cell.cell_type = state
        if path_type is not None:
            cell.path_type = path_type
        if state in {CellType.WALL, CellType.OBSTACLE}:
            cell.occupied_by = None

    def get_neighbors(self, cell: Cell, moore: bool = True) -> list[Cell]:
        offsets = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        if moore:
            offsets += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
        result: list[Cell] = []
        for dx, dy in offsets:
            x, y = cell.x + dx, cell.y + dy
            if not self.in_bounds(x, y):
                continue
            if moore and abs(dx) == 1 and abs(dy) == 1:
                if not self.get_cell(cell.x + dx, cell.y).is_static_passable:
                    continue
                if not self.get_cell(cell.x, cell.y + dy).is_static_passable:
                    continue
            result.append(self.get_cell(x, y))
        return result

    def add_exit(self, exit_obj: Exit) -> None:
        if exit_obj.width <= 0:
            raise ValueError("Ширина выхода должна быть положительной")
        for x, y in exit_obj.cells:
            cell = self.get_cell(x, y)
            cell.cell_type = CellType.EXIT
            cell.path_type = PathType.DOORWAY
        self.exits = [item for item in self.exits if item.id != exit_obj.id]
        self.exits.append(exit_obj)

    def add_obstacle(self, obstacle: Obstacle) -> None:
        for x, y in obstacle.cells:
            self.set_cell_state(x, y, CellType.OBSTACLE)
        self.obstacles = [item for item in self.obstacles if item.id != obstacle.id]
        self.obstacles.append(obstacle)

    def has_passable_cells(self) -> bool:
        return any(cell.is_static_passable for cell in self.iter_cells())

    def has_exits(self) -> bool:
        return bool(self.exits)

    def reset_occupancy(self) -> None:
        for cell in self.iter_cells():
            cell.occupied_by = None

    def iter_cells(self) -> list[Cell]:
        return [self.grid[y, x] for y in range(self.rows) for x in range(self.cols)]

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.name.strip():
            errors.append("Не задано название модели")
        if self.width <= 0 or self.height <= 0:
            errors.append("Размеры модели должны быть положительными")
        if self.cell_size <= 0:
            errors.append("Шаг клеточного разбиения должен быть положительным")
        elif self.cell_size > min(self.width, self.height):
            errors.append("Шаг клеточного разбиения превышает размер модели")
        if self.width <= 0 or self.height <= 0 or self.cell_size <= 0:
            return errors
        if not self.has_exits():
            errors.append("В модели отсутствует эвакуационный выход")
        if not self.has_passable_cells():
            errors.append("В модели отсутствуют проходимые клетки")
        for exit_obj in self.exits:
            for x, y in exit_obj.cells:
                if not self.in_bounds(x, y):
                    errors.append("Координаты клетки вне модели")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "cell_size": self.cell_size,
            "cells": [cell.to_dict() for cell in self.iter_cells()],
            "exits": [exit_obj.to_dict() for exit_obj in self.exits],
            "obstacles": [obstacle.to_dict() for obstacle in self.obstacles],
            "control_points": [cp.to_dict() for cp in self.control_points],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildingModel":
        model = cls(
            id=data.get("id"),
            name=str(data["name"]),
            width=float(data["width"]),
            height=float(data["height"]),
            cell_size=float(data["cell_size"]),
        )
        cells = [Cell.from_dict(item) for item in data.get("cells", [])]
        if cells:
            model.grid = np.empty((model.rows, model.cols), dtype=object)
            for cell in cells:
                model.grid[cell.y, cell.x] = cell
        model.exits = [Exit.from_dict(item) for item in data.get("exits", [])]
        model.obstacles = [Obstacle.from_dict(item) for item in data.get("obstacles", [])]
        model.control_points = [ControlPoint.from_dict(item) for item in data.get("control_points", [])]
        return model

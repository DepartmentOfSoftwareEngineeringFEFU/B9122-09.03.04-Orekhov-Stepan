from __future__ import annotations

import pytest

from app.models import BuildingModel, CellType, Exit


def test_create_valid_model() -> None:
    model = BuildingModel(id=None, name="Аудитория", width=10.0, height=5.0, cell_size=0.5)
    assert model.cols == 20
    assert model.rows == 10
    assert model.get_cell(0, 0).cell_type == CellType.FREE


def test_empty_name() -> None:
    with pytest.raises(ValueError, match="Не задано название модели"):
        BuildingModel(id=None, name="", width=10.0, height=5.0, cell_size=0.5)


def test_non_positive_size_validation() -> None:
    model = BuildingModel(id=None, name="bad", width=-1.0, height=5.0, cell_size=0.5)
    assert "Размеры модели должны быть положительными" in model.validate()


def test_non_positive_cell_size_validation() -> None:
    model = BuildingModel(id=None, name="bad", width=5.0, height=5.0, cell_size=0.0)
    assert "Шаг клеточного разбиения должен быть положительным" in model.validate()


def test_cell_size_too_large() -> None:
    with pytest.raises(ValueError, match="Шаг клеточного разбиения превышает размер модели"):
        BuildingModel(id=None, name="bad", width=5.0, height=5.0, cell_size=6.0)


def test_exit_out_of_bounds() -> None:
    model = BuildingModel(id=None, name="Аудитория", width=4.0, height=4.0, cell_size=1.0)
    with pytest.raises(ValueError, match="Координаты клетки вне модели"):
        model.add_exit(Exit(id=1, cells={(10, 10)}, width=1.0))


def test_model_without_exits() -> None:
    model = BuildingModel(id=None, name="Аудитория", width=4.0, height=4.0, cell_size=1.0)
    assert "В модели отсутствует эвакуационный выход" in model.validate()


def test_model_without_passable_cells() -> None:
    model = BuildingModel(id=None, name="Аудитория", width=2.0, height=2.0, cell_size=1.0)
    for cell in model.iter_cells():
        cell.cell_type = CellType.WALL
    assert "В модели отсутствуют проходимые клетки" in model.validate()

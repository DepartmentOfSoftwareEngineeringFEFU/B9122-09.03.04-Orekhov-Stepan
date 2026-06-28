from __future__ import annotations

import pytest

from app.models import Agent, BuildingModel, EvacuationScenario, Exit
from app.reports import ReportGenerator
from app.simulation import SimulationEngine


def report_scenario() -> EvacuationScenario:
    model = BuildingModel(id=None, name="Тест", width=4.0, height=3.0, cell_size=1.0)
    model.add_exit(Exit(id=1, cells={(3, 1)}, width=1.0, capacity=1))
    return EvacuationScenario(id=None, name="s", building_model=model, agents=[Agent(id=1, current_cell=(0, 1))])


def test_report_after_simulation() -> None:
    scenario = report_scenario()
    result = SimulationEngine(scenario).run()
    text = ReportGenerator().build_text(scenario, result)
    assert "Отчёт по результатам моделирования эвакуации" in text


def test_report_without_result_forbidden() -> None:
    with pytest.raises(ValueError, match="Результаты моделирования отсутствуют"):
        ReportGenerator().build_text(report_scenario(), None)


def test_report_contains_required_data() -> None:
    scenario = report_scenario()
    result = SimulationEngine(scenario).run()
    text = ReportGenerator().build_text(scenario, result)
    assert "Tevac" in text
    assert "Таблица времени эвакуации агентов" in text
    assert "Зоны заторов" in text
    assert "Нормативные скопления" in text


def test_report_contains_incomplete_normative_warning() -> None:
    scenario = report_scenario()
    result = SimulationEngine(scenario).run()
    text = ReportGenerator().build_text(scenario, result)
    assert "без полной нормативной оценки пожарной безопасности" in text

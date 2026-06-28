from __future__ import annotations

from app.models import Agent, BuildingModel, EnvironmentEvent, EventType, EvacuationScenario, Exit, ExitStatus
from app.simulation import SimulationEngine
from app.simulation.validation import validate_event


def scenario_two_exits() -> EvacuationScenario:
    model = BuildingModel(id=None, name="Тест", width=6.0, height=3.0, cell_size=1.0)
    model.add_exit(Exit(id=1, cells={(5, 1)}, width=1.0, capacity=1))
    model.add_exit(Exit(id=2, cells={(5, 2)}, width=1.0, capacity=1))
    return EvacuationScenario(id=None, name="s", building_model=model, agents=[Agent(id=1, current_cell=(0, 1))])


def test_block_exit_event_applies_at_time() -> None:
    scenario = scenario_two_exits()
    scenario.events.append(EnvironmentEvent(id=1, type=EventType.BLOCK_EXIT, time=1.0, params={"exit_id": 1}))
    engine = SimulationEngine(scenario)
    engine.initialize()
    engine.step(1.0)
    assert scenario.exits[0].status == ExitStatus.BLOCKED


def test_agents_replan_after_block() -> None:
    scenario = scenario_two_exits()
    scenario.events.append(EnvironmentEvent(id=1, type=EventType.BLOCK_EXIT, time=0.0, params={"exit_id": 1}))
    result = SimulationEngine(scenario).run()
    assert result.evacuated_count == 1
    assert scenario.exits[0].status == ExitStatus.BLOCKED


def test_negative_event_time_forbidden() -> None:
    scenario = scenario_two_exits()
    event = EnvironmentEvent(id=1, type=EventType.BLOCK_EXIT, time=-1.0)
    assert "Время события не может быть отрицательным" in validate_event(event, scenario)


def test_invalid_event_type_forbidden() -> None:
    scenario = scenario_two_exits()
    event = EnvironmentEvent(id=1, type="bad", time=1.0)
    assert "Некорректный тип события" in validate_event(event, scenario)


def test_smoke_out_of_range_forbidden() -> None:
    scenario = scenario_two_exits()
    event = EnvironmentEvent(id=1, type=EventType.CHANGE_SMOKE, time=1.0, params={"smoke_level": 2.0})
    assert "Уровень задымления должен быть в диапазоне [0, 1]" in validate_event(event, scenario)

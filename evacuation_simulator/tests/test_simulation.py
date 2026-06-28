from __future__ import annotations

import pytest

from app.models import Agent, AgentState, BuildingModel, CellType, EvacuationScenario, Exit, ExitStatus, SimulationParameters
from app.simulation import SimulationEngine


def basic_scenario(start: tuple[int, int] = (0, 1), max_time: float = 20.0) -> EvacuationScenario:
    model = BuildingModel(id=None, name="Тест", width=5.0, height=3.0, cell_size=1.0)
    model.add_exit(Exit(id=1, cells={(4, 1)}, width=1.0, capacity=1))
    return EvacuationScenario(
        id=None,
        name="s",
        building_model=model,
        agents=[Agent(id=1, current_cell=start)],
        simulation_parameters=SimulationParameters(time_step=1.0, max_time=max_time),
    )


def test_agent_moves_to_neighbor_free_cell() -> None:
    scenario = basic_scenario()
    engine = SimulationEngine(scenario)
    engine.initialize()
    engine.step(1.0)
    assert scenario.agents[0].current_cell != (0, 1)


def test_agent_does_not_pass_wall() -> None:
    scenario = basic_scenario()
    scenario.building_model.set_cell_state(1, 1, CellType.WALL)
    result = SimulationEngine(scenario).run()
    assert (1, 1) not in result.trajectories[1]


def test_agent_does_not_move_into_occupied_cell() -> None:
    scenario = basic_scenario()
    scenario.agents.append(Agent(id=2, current_cell=(1, 1)))
    engine = SimulationEngine(scenario)
    engine.initialize()
    engine.step(1.0)
    positions = [agent.current_cell for agent in scenario.agents if agent.state != AgentState.EVACUATED]
    assert len(positions) == len(set(positions))


def test_conflict_for_one_cell_is_resolved() -> None:
    scenario = basic_scenario((1, 0))
    scenario.agents.append(Agent(id=2, current_cell=(1, 2)))
    engine = SimulationEngine(scenario)
    engine.initialize()
    engine.step(1.0)
    positions = [agent.current_cell for agent in scenario.agents if agent.state != AgentState.EVACUATED]
    assert len(positions) == len(set(positions))


def test_agent_reaches_open_exit() -> None:
    scenario = basic_scenario((3, 1))
    result = SimulationEngine(scenario).run()
    assert result.evacuated_count == 1
    assert scenario.agents[0].state == AgentState.EVACUATED


def test_agent_does_not_evacuate_through_blocked_exit() -> None:
    scenario = basic_scenario((3, 1), max_time=5.0)
    scenario.exits[0].status = ExitStatus.BLOCKED
    scenario.building_model.exits[0].status = ExitStatus.BLOCKED
    result = SimulationEngine(scenario).run()
    assert result.evacuated_count == 0


def test_finish_when_all_evacuated() -> None:
    scenario = basic_scenario((3, 1))
    result = SimulationEngine(scenario).run()
    assert result.status.value == "завершено"
    assert result.total_evacuation_time is not None


def test_finish_at_tmax() -> None:
    scenario = basic_scenario((0, 1), max_time=1.0)
    result = SimulationEngine(scenario).run()
    assert result.history[-1].time == pytest.approx(1.0)


def test_move_budget_orthogonal_and_diagonal_step() -> None:
    scenario = basic_scenario()
    engine = SimulationEngine(scenario)
    building = scenario.building_model
    assert engine.movement.step_length(building.get_cell(0, 0), building.get_cell(1, 0), 1.0) == pytest.approx(1.0)
    assert engine.movement.step_length(building.get_cell(0, 0), building.get_cell(1, 1), 1.0) == pytest.approx(2**0.5)


def test_agent_avoids_danger_zone_when_safe_route_exists() -> None:
    scenario = basic_scenario()
    danger = scenario.building_model.get_cell(2, 1)
    danger.cell_type = CellType.DANGER
    danger.danger_level = 1.0
    scenario.simulation_parameters.gamma = 20.0

    result = SimulationEngine(scenario).run()

    assert (2, 1) not in result.trajectories[1]

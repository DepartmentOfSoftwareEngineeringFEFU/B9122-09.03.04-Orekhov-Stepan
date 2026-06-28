from __future__ import annotations

from app.models import Agent, BuildingModel, CellType, ControlPoint, EvacuationScenario, Exit, MobilityGroup, MovementNormTable
from app.simulation.validation import validate_scenario


def scenario_with_agent(agent: Agent) -> EvacuationScenario:
    model = BuildingModel(id=None, name="Тест", width=4.0, height=4.0, cell_size=1.0)
    model.add_exit(Exit(id=1, cells={(3, 1)}, width=1.0))
    return EvacuationScenario(id=None, name="s", building_model=model, agents=[agent])


def test_create_agent_valid() -> None:
    agent = Agent(id=1, current_cell=(0, 0), mobility_group=MobilityGroup.M0_3)
    assert agent.effective_projection_area == agent.base_projection_area


def test_duplicate_id() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0)))
    scenario.agents.append(Agent(id=1, current_cell=(1, 0)))
    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])
    assert "Дублирование id агента" in errors


def test_agent_in_wall() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0)))
    scenario.building_model.set_cell_state(0, 0, CellType.WALL)
    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])
    assert "Агент не может быть размещён в стене" in errors


def test_agent_in_obstacle() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0)))
    scenario.building_model.set_cell_state(0, 0, CellType.OBSTACLE)
    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])
    assert "Агент не может быть размещён в препятствии" in errors


def test_agent_out_of_bounds() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(10, 10)))
    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])
    assert "Координаты клетки вне модели" in errors


def test_two_agents_in_one_cell() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0)))
    scenario.agents.append(Agent(id=2, current_cell=(0, 0)))
    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])
    assert "Клетка уже занята" in errors


def test_speed_must_be_positive() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0), base_speed=0.0))
    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])
    assert "Скорость агента должна быть положительной" in errors


def test_m0_without_subgroup() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0), mobility_group=MobilityGroup.M0))
    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])
    assert "Для группы М0 необходимо указать подгруппу" in errors


def test_nm_nt_warning() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0), mobility_group=MobilityGroup.NM))
    warnings: list[str] = []
    errors = validate_scenario(scenario, MovementNormTable.load_default(), warnings)
    assert not errors
    assert "Для групп НМ и НТ требуется отдельный расчёт спасения" in warnings


def test_control_point_far_cell_requires_group_agent() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(0, 0), mobility_group=MobilityGroup.M0_3))
    scenario.control_points = [ControlPoint(id=1, label="Cfar(M0_3)", x=2, y=2)]

    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])

    assert "Необходимо разместить агента в наиболее удалённой точке" in errors


def test_control_point_far_cell_accepts_group_agent() -> None:
    scenario = scenario_with_agent(Agent(id=1, current_cell=(2, 2), mobility_group=MobilityGroup.M0_3))
    scenario.control_points = [ControlPoint(id=1, label="Cfar(M0_3)", x=2, y=2)]

    errors = validate_scenario(scenario, MovementNormTable.load_default(), [])

    assert "Необходимо разместить агента в наиболее удалённой точке" not in errors

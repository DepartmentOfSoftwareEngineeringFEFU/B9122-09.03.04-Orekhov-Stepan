from __future__ import annotations

from collections import Counter
import re

from app.models import (
    Agent,
    CellType,
    EnvironmentEvent,
    EvacuationScenario,
    MobilityGroup,
    MovementNormTable,
)


def _mobility_group_from_text(text: str | None) -> MobilityGroup | None:
    if not text:
        return None
    normalized = text.upper().replace("-", "_").replace("М", "M")
    for group in sorted(MobilityGroup, key=lambda item: len(item.name), reverse=True):
        if group.name in normalized or group.value.upper().replace("-", "_").replace("М", "M") in normalized:
            return group
    return None


def validate_control_points(scenario: EvacuationScenario) -> list[str]:
    errors: list[str] = []
    labels = Counter(cp.label for cp in scenario.control_points)
    if any(not label.strip() or count > 1 for label, count in labels.items()):
        errors.append("Обозначение контрольной точки должно быть уникальным")

    for point in scenario.control_points:
        coord = point.coord
        if coord is None or not scenario.building_model.in_bounds(*coord):
            errors.append("Контрольная точка расположена вне модели")
            continue

        marker_text = f"{point.label} {point.path_segment or ''}"
        if not re.search(r"\b(CFAR|FAR|ДАЛЬН|УДАЛ)", marker_text.upper()):
            continue
        required_group = _mobility_group_from_text(marker_text)
        if required_group is None:
            continue
        if not any(agent.mobility_group == required_group and agent.current_cell == coord for agent in scenario.agents):
            errors.append("Необходимо разместить агента в наиболее удалённой точке")
    return errors


def validate_agent(agent: Agent, scenario: EvacuationScenario, norm_table: MovementNormTable) -> list[str]:
    errors: list[str] = []
    building = scenario.building_model
    x, y = agent.current_cell
    if not building.in_bounds(x, y):
        errors.append("Координаты клетки вне модели")
        return errors
    cell = building.get_cell(x, y)
    if cell.cell_type == CellType.WALL:
        errors.append("Агент не может быть размещён в стене")
    if cell.cell_type == CellType.OBSTACLE:
        errors.append("Агент не может быть размещён в препятствии")
    if agent.base_speed <= 0:
        errors.append("Скорость агента должна быть положительной")
    if agent.mobility_group == MobilityGroup.M0:
        errors.append("Для группы М0 необходимо указать подгруппу")
    if agent.mobility_group in {MobilityGroup.NM, MobilityGroup.NT}:
        errors.append("Для групп НМ и НТ требуется отдельный расчёт спасения")
    if agent.mobility_group not in {MobilityGroup.NM, MobilityGroup.NT, MobilityGroup.M0}:
        try:
            norm_table.validate_agent_params(agent)
        except KeyError:
            errors.append("Нормативные параметры движения не найдены")
    return errors


def validate_event(event: EnvironmentEvent, scenario: EvacuationScenario) -> list[str]:
    errors = event.validate()
    for x, y in event.area:
        if not scenario.building_model.in_bounds(x, y):
            errors.append("Координаты клетки вне модели")
    return errors


def validate_scenario(
    scenario: EvacuationScenario,
    norm_table: MovementNormTable | None = None,
    warnings: list[str] | None = None,
) -> list[str]:
    norm_table = norm_table or MovementNormTable.load_default()
    warnings = warnings if warnings is not None else []
    errors: list[str] = []
    if scenario.building_model is None:
        errors.append("Модель не найдена")
        return errors
    errors.extend(scenario.building_model.validate())
    params = scenario.simulation_parameters
    if not scenario.agents:
        errors.append("В сценарии отсутствуют агенты")
    if params.time_step <= 0:
        errors.append("Шаг моделирования должен быть положительным")
    if params.max_time <= 0:
        errors.append("Максимальное время моделирования должно быть положительным")
    if params.max_time < params.time_step:
        errors.append("Максимальное время меньше шага моделирования")
    if params.alpha < 0 or params.beta < 0 or params.gamma < 0:
        errors.append("Коэффициенты alpha, beta, gamma должны быть неотрицательными")
    if params.rho_crit < 0:
        errors.append("Порог плотности rho_crit должен быть неотрицательным")

    ids = Counter(agent.id for agent in scenario.agents)
    if any(count > 1 for count in ids.values()):
        errors.append("Дублирование id агента")
    positions = Counter(agent.current_cell for agent in scenario.agents)
    if any(count > 1 for count in positions.values()):
        errors.append("Клетка уже занята")

    for agent in scenario.agents:
        agent_errors = validate_agent(agent, scenario, norm_table)
        for item in agent_errors:
            if item == "Для групп НМ и НТ требуется отдельный расчёт спасения":
                warnings.append(item)
            else:
                errors.append(item)
    for event in scenario.events:
        errors.extend(validate_event(event, scenario))
    errors.extend(validate_control_points(scenario))
    return errors

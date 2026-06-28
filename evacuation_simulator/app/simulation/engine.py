from __future__ import annotations

from collections import defaultdict
from math import inf
from random import Random

from app.models import (
    Agent,
    AgentSnapshot,
    AgentState,
    EvacuationScenario,
    HistorySnapshot,
    MobilityGroup,
    MovementNormTable,
    SimulationResult,
    SimulationStatus,
)
from .density import DensityAnalyzer
from .events import EventProcessor
from .movement import MovementCalculator, MovementRequest
from .pathfinding import PathFinder
from .validation import validate_scenario


class SimulationError(RuntimeError):
    pass


class SimulationEngine:

    def __init__(self, scenario: EvacuationScenario, norm_table: MovementNormTable | None = None) -> None:
        self.scenario = scenario
        self.norm_table = norm_table or MovementNormTable.load_default()
        self.random = Random(scenario.simulation_parameters.random_seed)
        self.density = DensityAnalyzer(scenario.building_model)
        self.movement = MovementCalculator(self.norm_table)
        self.pathfinder = PathFinder(scenario.building_model)
        self.events = EventProcessor(scenario)
        self.history: list[HistorySnapshot] = []
        self.congestion_zones: list[dict[str, object]] = []
        self.normative_congestion_zones: list[dict[str, object]] = []
        self.warnings: list[str] = []
        self._stop_requested = False

    def validate_scenario(self) -> None:
        errors = validate_scenario(self.scenario, self.norm_table, self.warnings)
        blocking_errors = [item for item in errors if item != "Для групп НМ и НТ требуется отдельный расчёт спасения"]
        if blocking_errors:
            raise SimulationError("; ".join(dict.fromkeys(blocking_errors)))

    def initialize(self) -> None:
        self.validate_scenario()
        self.scenario.building_model.reset_occupancy()
        for event in self.scenario.events:
            event.applied = False
        for agent in sorted(self.scenario.agents, key=lambda item: item.id):
            agent.move_budget = 0.0
            agent.evacuation_time = None
            agent.trajectory = [agent.current_cell]
            agent.reason_if_not_evacuated = ""
            if agent.mobility_group in {MobilityGroup.NM, MobilityGroup.NT}:
                agent.state = AgentState.NEEDS_RESCUE
                agent.reason_if_not_evacuated = "Для групп НМ и НТ требуется отдельный расчёт спасения"
                if agent.reason_if_not_evacuated not in self.warnings:
                    self.warnings.append(agent.reason_if_not_evacuated)
                continue
            norm = self.norm_table.get(agent.mobility_group, self.scenario.building_model.get_cell(*agent.current_cell).path_type)
            agent.apply_norm(norm)
            agent.state = AgentState.MOVING
            self.scenario.building_model.get_cell(*agent.current_cell).occupied_by = agent.id

    def run(self) -> SimulationResult:
        self.initialize()
        current_time = 0.0
        self.save_history_snapshot(current_time, [])
        while current_time < self.scenario.simulation_parameters.max_time:
            if self.check_finish_condition():
                break
            if self._stop_requested:
                break
            current_time = round(current_time + self.scenario.simulation_parameters.time_step, 10)
            self.step(current_time)
        return self.finish()

    def stop(self) -> None:
        self._stop_requested = True

    def step(self, current_time: float) -> None:
        applied_events = self.events.apply_due_events(current_time)
        if self.events.environment_changed:
            self.pathfinder.invalidate()
        density_map = self.density.calculate_density_map(self.scenario.agents)
        params = self.scenario.simulation_parameters
        distance_map = self.pathfinder.distance_map(self.scenario.exits, alpha=params.alpha, gamma=params.gamma)
        requests = self._build_movement_requests(density_map, distance_map)
        accepted = self._apply_exit_capacity(requests, density_map, current_time)
        winners = self._resolve_conflicts(accepted)
        self._apply_moves(winners, current_time)
        density_map = self.density.calculate_density_map(self.scenario.agents)
        self._detect_congestion(current_time, density_map)
        self.save_history_snapshot(current_time, applied_events)

    def _build_movement_requests(
        self,
        density_map: dict[tuple[int, int], float],
        distance_map: dict[tuple[int, int], float],
    ) -> dict[int, MovementRequest]:
        params = self.scenario.simulation_parameters
        requests: dict[int, MovementRequest] = {}
        for agent in self.active_agents():
            current = self.scenario.building_model.get_cell(*agent.current_cell)
            if distance_map.get(agent.current_cell, inf) == inf:
                agent.state = AgentState.DELAYED
                agent.reason_if_not_evacuated = "Отсутствует маршрут к доступному выходу"
                continue
            speed = self.movement.calculate_speed(agent, current, density_map.get(agent.current_cell, 0.0))
            agent.move_budget += speed * params.time_step
            target_request = self._choose_target(agent, density_map, distance_map)
            if target_request is None:
                agent.state = AgentState.MOVING
                agent.reason_if_not_evacuated = "Ожидание свободной соседней клетки"
                continue
            if agent.move_budget >= target_request.step_length:
                requests[agent.id] = target_request
        return requests

    def _choose_target(
        self,
        agent: Agent,
        density_map: dict[tuple[int, int], float],
        distance_map: dict[tuple[int, int], float],
    ) -> MovementRequest | None:
        params = self.scenario.simulation_parameters
        building = self.scenario.building_model
        current = building.get_cell(*agent.current_cell)
        best: MovementRequest | None = None
        for neighbor in building.get_neighbors(current, moore=True):
            if not neighbor.is_static_passable:
                continue
            if neighbor.occupied and neighbor.occupied_by != agent.id:
                continue
            distance = distance_map.get((neighbor.x, neighbor.y), inf)
            if distance == inf:
                continue
            dnorm = density_map.get((neighbor.x, neighbor.y), 0.0)
            cost = self.movement.transition_cost(neighbor, distance, dnorm, params.alpha, params.beta, params.gamma)
            step_length = self.movement.step_length(current, neighbor, building.cell_size)
            request = MovementRequest(agent=agent, target=neighbor, cost=cost, step_length=step_length)
            if best is None or (request.cost, request.step_length, request.target.y, request.target.x) < (
                best.cost,
                best.step_length,
                best.target.y,
                best.target.x,
            ):
                best = request
        return best

    def _apply_exit_capacity(
        self,
        requests: dict[int, MovementRequest],
        density_map: dict[tuple[int, int], float],
        current_time: float,
    ) -> dict[int, MovementRequest]:
        by_exit: dict[int, list[MovementRequest]] = defaultdict(list)
        accepted = dict(requests)
        for request in requests.values():
            exit_obj = self._exit_at((request.target.x, request.target.y))
            if exit_obj:
                by_exit[exit_obj.id].append(request)
        for exit_id, exit_requests in by_exit.items():
            exit_obj = next(item for item in self.scenario.exits if item.id == exit_id)
            exit_requests.sort(key=lambda req: (req.cost, -req.agent.move_budget, req.agent.id))
            allowed = exit_requests[: exit_obj.step_capacity(self.scenario.simulation_parameters.time_step)]
            denied = exit_requests[len(allowed) :]
            for request in denied:
                accepted.pop(request.agent.id, None)
                request.agent.reason_if_not_evacuated = "Задержка перед выходом из-за ограничения пропускной способности"
                coord = request.agent.current_cell
                dnorm = density_map.get(coord, 0.0)
                if dnorm > 0.5:
                    self.normative_congestion_zones.append({"time": current_time, "coord": coord, "dnorm": dnorm})
        return accepted

    def _resolve_conflicts(self, requests: dict[int, MovementRequest]) -> dict[int, MovementRequest]:
        grouped: dict[tuple[int, int], list[MovementRequest]] = defaultdict(list)
        for request in requests.values():
            grouped[(request.target.x, request.target.y)].append(request)
        winners: dict[int, MovementRequest] = {}
        for items in grouped.values():
            items.sort(key=lambda req: (req.cost, -req.agent.move_budget, req.agent.id))
            winner = items[0]
            winners[winner.agent.id] = winner
        return winners

    def _apply_moves(self, winners: dict[int, MovementRequest], current_time: float) -> None:
        building = self.scenario.building_model
        for request in sorted(winners.values(), key=lambda item: item.agent.id):
            agent = request.agent
            source = building.get_cell(*agent.current_cell)
            if source.occupied_by == agent.id:
                source.occupied_by = None
            agent.current_cell = (request.target.x, request.target.y)
            agent.move_budget -= request.step_length
            agent.trajectory.append(agent.current_cell)
            exit_obj = self._exit_at(agent.current_cell)
            if exit_obj and exit_obj.is_available():
                agent.state = AgentState.EVACUATED
                agent.evacuation_time = current_time
                agent.reason_if_not_evacuated = ""
                continue
            agent.state = AgentState.MOVING
            request.target.occupied_by = agent.id

    def _detect_congestion(self, current_time: float, density_map: dict[tuple[int, int], float]) -> None:
        params = self.scenario.simulation_parameters
        for coord, dnorm in density_map.items():
            if dnorm >= params.rho_crit:
                self.congestion_zones.append({"time": current_time, "coord": coord, "dnorm": dnorm})
            if dnorm > 0.5:
                self.normative_congestion_zones.append({"time": current_time, "coord": coord, "dnorm": dnorm})

    def save_history_snapshot(self, current_time: float, applied_events: list[int]) -> None:
        density_map = self.density.calculate_density_map(self.scenario.agents)
        max_dnorm = max(density_map.values(), default=0.0)
        congestion = [
            {"coord": coord, "dnorm": dnorm}
            for coord, dnorm in density_map.items()
            if dnorm >= self.scenario.simulation_parameters.rho_crit
        ]
        normative = [{"coord": coord, "dnorm": dnorm} for coord, dnorm in density_map.items() if dnorm > 0.5]
        self.history.append(
            HistorySnapshot(
                time=current_time,
                agents=[
                    AgentSnapshot(
                        id=agent.id,
                        x=agent.current_cell[0],
                        y=agent.current_cell[1],
                        state=agent.state,
                        move_budget=agent.move_budget,
                    )
                    for agent in self.scenario.agents
                    if agent.state != AgentState.EVACUATED
                ],
                exits={exit_obj.id: exit_obj.status for exit_obj in self.scenario.exits},
                applied_events=applied_events,
                congestion_zones=congestion,
                normative_congestion_zones=normative,
                max_dnorm=max_dnorm,
            )
        )

    def check_finish_condition(self) -> bool:
        terminal = {AgentState.EVACUATED, AgentState.DELAYED, AgentState.NEEDS_RESCUE}
        return all(agent.state in terminal for agent in self.scenario.agents)

    def finish(self) -> SimulationResult:
        evacuated = [agent for agent in self.scenario.agents if agent.state == AgentState.EVACUATED]
        delayed = [agent for agent in self.scenario.agents if agent.state == AgentState.DELAYED]
        needs_rescue = [agent for agent in self.scenario.agents if agent.state == AgentState.NEEDS_RESCUE]
        times = {agent.id: agent.evacuation_time for agent in evacuated if agent.evacuation_time is not None}
        total = max(times.values()) if times else None
        if total is None:
            self.warnings.append("Никто из агентов не эвакуирован; Tevac не определено")
        params = self.scenario.simulation_parameters
        if params.evacuation_start_time is None or params.route_blocking_time is None:
            self.warnings.append(
                "Сформированы результаты моделирования эвакуации без полной нормативной оценки пожарной безопасности, "
                "так как не заданы время начала эвакуации и/или время блокирования путей эвакуации."
            )
        if needs_rescue:
            self.warnings.append(
                "Итоговый нормативный вывод является неполным, так как для групп НМ и НТ требуется отдельный расчёт спасения."
            )
        return SimulationResult(
            id=None,
            scenario_id=self.scenario.id,
            status=SimulationStatus.STOPPED if self._stop_requested else SimulationStatus.FINISHED,
            total_evacuation_time=total,
            evacuated_count=len(evacuated),
            blocked_count=len(self.scenario.agents) - len(evacuated),
            delayed_count=len(delayed),
            needs_rescue_count=len(needs_rescue),
            agent_evacuation_times=times,
            trajectories={agent.id: agent.trajectory for agent in self.scenario.agents},
            congestion_zones=self.congestion_zones,
            normative_congestion_zones=self.normative_congestion_zones,
            event_log=self.events.event_log,
            history=self.history,
            final_state={str(agent.id): agent.state.name for agent in self.scenario.agents},
            warnings=list(dict.fromkeys(self.warnings)),
        )

    def active_agents(self) -> list[Agent]:
        return [
            agent
            for agent in sorted(self.scenario.agents, key=lambda item: item.id)
            if agent.state in {AgentState.WAITING, AgentState.MOVING}
            and agent.can_move_independently()
            and agent.evacuation_time is None
        ]

    def _exit_at(self, coord: tuple[int, int]):
        for exit_obj in self.scenario.exits:
            if coord in exit_obj.cells:
                return exit_obj
        return None

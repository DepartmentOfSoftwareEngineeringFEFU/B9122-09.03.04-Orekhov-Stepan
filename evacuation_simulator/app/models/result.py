from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .enums import AgentState, ExitStatus, SimulationStatus


@dataclass(slots=True)
class AgentSnapshot:
    id: int
    x: int
    y: int
    state: AgentState
    move_budget: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "state": self.state.name,
            "move_budget": self.move_budget,
        }


@dataclass(slots=True)
class HistorySnapshot:
    time: float
    agents: list[AgentSnapshot]
    exits: dict[int, ExitStatus]
    applied_events: list[int] = field(default_factory=list)
    congestion_zones: list[dict[str, Any]] = field(default_factory=list)
    normative_congestion_zones: list[dict[str, Any]] = field(default_factory=list)
    max_dnorm: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "time": self.time,
            "agents": [agent.to_dict() for agent in self.agents],
            "exits": {str(k): v.name for k, v in self.exits.items()},
            "applied_events": self.applied_events,
            "congestion_zones": self.congestion_zones,
            "normative_congestion_zones": self.normative_congestion_zones,
            "max_dnorm": self.max_dnorm,
        }


@dataclass(slots=True)
class SimulationResult:
    id: int | None
    scenario_id: int | None
    status: SimulationStatus
    total_evacuation_time: float | None
    evacuated_count: int
    blocked_count: int
    delayed_count: int
    needs_rescue_count: int
    agent_evacuation_times: dict[int, float]
    trajectories: dict[int, list[tuple[int, int]]]
    congestion_zones: list[dict[str, Any]]
    normative_congestion_zones: list[dict[str, Any]]
    event_log: list[str]
    history: list[HistorySnapshot]
    final_state: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scenario_id": self.scenario_id,
            "status": self.status.name,
            "total_evacuation_time": self.total_evacuation_time,
            "evacuated_count": self.evacuated_count,
            "blocked_count": self.blocked_count,
            "delayed_count": self.delayed_count,
            "needs_rescue_count": self.needs_rescue_count,
            "agent_evacuation_times": {str(k): v for k, v in self.agent_evacuation_times.items()},
            "trajectories": {str(k): [list(c) for c in v] for k, v in self.trajectories.items()},
            "congestion_zones": self.congestion_zones,
            "normative_congestion_zones": self.normative_congestion_zones,
            "event_log": self.event_log,
            "history": [snapshot.to_dict() for snapshot in self.history],
            "final_state": self.final_state,
            "warnings": self.warnings,
        }

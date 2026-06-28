from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent import Agent
from .building import BuildingModel
from .control_point import ControlPoint
from .event import EnvironmentEvent
from .exit import Exit
from .obstacle import Obstacle


@dataclass(slots=True)
class SimulationParameters:
    time_step: float = 1.0
    max_time: float = 300.0
    alpha: float = 10.0
    beta: float = 5.0
    gamma: float = 20.0
    rho_crit: float = 0.5
    random_seed: int = 42
    evacuation_start_time: float | None = None
    route_blocking_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "time_step": self.time_step,
            "max_time": self.max_time,
            "alpha": self.alpha,
            "beta": self.beta,
            "gamma": self.gamma,
            "rho_crit": self.rho_crit,
            "random_seed": self.random_seed,
            "evacuation_start_time": self.evacuation_start_time,
            "route_blocking_time": self.route_blocking_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationParameters":
        return cls(**data)


@dataclass
class EvacuationScenario:
    id: int | None
    name: str
    building_model: BuildingModel
    agents: list[Agent] = field(default_factory=list)
    exits: list[Exit] = field(default_factory=list)
    obstacles: list[Obstacle] = field(default_factory=list)
    events: list[EnvironmentEvent] = field(default_factory=list)
    control_points: list[ControlPoint] = field(default_factory=list)
    simulation_parameters: SimulationParameters = field(default_factory=SimulationParameters)

    def __post_init__(self) -> None:
        if not self.exits:
            self.exits = self.building_model.exits
        if not self.obstacles:
            self.obstacles = self.building_model.obstacles
        if not self.control_points:
            self.control_points = self.building_model.control_points

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "building_model_id": self.building_model.id,
            "name": self.name,
            "building_model": self.building_model.to_dict(),
            "agents": [agent.to_dict() for agent in self.agents],
            "exits": [exit_obj.to_dict() for exit_obj in self.exits],
            "obstacles": [obstacle.to_dict() for obstacle in self.obstacles],
            "events": [event.to_dict() for event in self.events],
            "control_points": [cp.to_dict() for cp in self.control_points],
            "simulation_parameters": self.simulation_parameters.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvacuationScenario":
        building = BuildingModel.from_dict(data["building_model"])
        return cls(
            id=data.get("id"),
            name=str(data["name"]),
            building_model=building,
            agents=[Agent.from_dict(item) for item in data.get("agents", [])],
            exits=[Exit.from_dict(item) for item in data.get("exits", building.to_dict().get("exits", []))],
            obstacles=[Obstacle.from_dict(item) for item in data.get("obstacles", [])],
            events=[EnvironmentEvent.from_dict(item) for item in data.get("events", [])],
            control_points=[ControlPoint.from_dict(item) for item in data.get("control_points", [])],
            simulation_parameters=SimulationParameters.from_dict(data.get("simulation_parameters", {})),
        )

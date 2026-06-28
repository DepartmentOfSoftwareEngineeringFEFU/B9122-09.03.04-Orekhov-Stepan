from __future__ import annotations

import csv
from pathlib import Path

from app.models import EvacuationScenario, SimulationResult


def export_agents_csv(scenario: EvacuationScenario, result: SimulationResult, path: str | Path) -> None:
    if result is None:
        raise ValueError("Результаты моделирования отсутствуют")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file, delimiter=";")
        writer.writerow(
            [
                "agent_id",
                "mobility_group",
                "state",
                "evacuation_time",
                "trajectory_length",
                "reason_if_not_evacuated",
            ]
        )
        for agent in sorted(scenario.agents, key=lambda item: item.id):
            writer.writerow(
                [
                    agent.id,
                    agent.mobility_group.value,
                    agent.state.value,
                    result.agent_evacuation_times.get(agent.id, ""),
                    len(result.trajectories.get(agent.id, [])),
                    agent.reason_if_not_evacuated,
                ]
            )

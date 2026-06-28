from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from app.models import AgentState, SimulationResult


def plot_evacuation_over_time(result: SimulationResult, path: str | Path) -> None:
    times = [snapshot.time for snapshot in result.history]
    evacuated = []
    for snapshot in result.history:
        active_ids = {agent.id for agent in snapshot.agents}
        evacuated.append(result.evacuated_count - len([aid for aid in active_ids if aid in result.agent_evacuation_times]))
    _line_plot(times, evacuated, "Время, с", "Эвакуировано", "Количество эвакуированных агентов", path)


def plot_active_delayed_over_time(result: SimulationResult, path: str | Path) -> None:
    times = [snapshot.time for snapshot in result.history]
    active = [sum(1 for agent in snapshot.agents if agent.state == AgentState.MOVING) for snapshot in result.history]
    delayed = [sum(1 for agent in snapshot.agents if agent.state == AgentState.DELAYED) for snapshot in result.history]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    plt.figure()
    plt.plot(times, active, label="Активные")
    plt.plot(times, delayed, label="Задержанные")
    plt.xlabel("Время, с")
    plt.ylabel("Количество агентов")
    plt.title("Активные и задержанные агенты")
    plt.legend()
    plt.tight_layout()
    plt.savefig(target)
    plt.close()


def plot_evacuation_time_distribution(result: SimulationResult, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    plt.figure()
    plt.hist(list(result.agent_evacuation_times.values()), bins=10)
    plt.xlabel("Время эвакуации, с")
    plt.ylabel("Количество агентов")
    plt.title("Распределение времени эвакуации")
    plt.tight_layout()
    plt.savefig(target)
    plt.close()


def plot_max_dnorm_over_time(result: SimulationResult, path: str | Path) -> None:
    times = [snapshot.time for snapshot in result.history]
    values = [snapshot.max_dnorm for snapshot in result.history]
    _line_plot(times, values, "Время, с", "max Dnorm", "Максимальная Dnorm по времени", path)


def _line_plot(x: list[float], y: list[float], xlabel: str, ylabel: str, title: str, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    plt.figure()
    plt.plot(x, y)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(target)
    plt.close()

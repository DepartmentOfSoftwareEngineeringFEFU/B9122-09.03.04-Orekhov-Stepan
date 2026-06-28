from __future__ import annotations

import json

from app.models import BuildingModel, EvacuationScenario, SimulationResult
from .database import Database


class BuildingRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, model: BuildingModel) -> int:
        with self.db.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO building_models(name, payload) VALUES (?, ?)",
                (model.name, "{}"),
            )
            model.id = int(cursor.lastrowid)
            payload = json.dumps(model.to_dict(), ensure_ascii=False)
            conn.execute("UPDATE building_models SET payload = ? WHERE id = ?", (payload, model.id))
            return model.id

    def get(self, model_id: int) -> BuildingModel:
        with self.db.connect() as conn:
            row = conn.execute("SELECT payload FROM building_models WHERE id = ?", (model_id,)).fetchone()
        if row is None:
            raise KeyError("Модель не найдена")
        return BuildingModel.from_dict(json.loads(row["payload"]))


class ScenarioRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, scenario: EvacuationScenario) -> int:
        with self.db.connect() as conn:
            building_cursor = conn.execute(
                "INSERT INTO building_models(name, payload) VALUES (?, ?)",
                (scenario.building_model.name, "{}"),
            )
            building_model_id = int(building_cursor.lastrowid)
            scenario.building_model.id = building_model_id
            building_payload = json.dumps(scenario.building_model.to_dict(), ensure_ascii=False)
            conn.execute(
                "UPDATE building_models SET payload = ? WHERE id = ?",
                (building_payload, building_model_id),
            )

            cursor = conn.execute(
                "INSERT INTO scenarios(building_model_id, name, payload) VALUES (?, ?, ?)",
                (building_model_id, scenario.name, "{}"),
            )
            scenario_id = int(cursor.lastrowid)
            scenario.id = scenario_id
            payload = json.dumps(scenario.to_dict(), ensure_ascii=False)
            conn.execute("UPDATE scenarios SET payload = ? WHERE id = ?", (payload, scenario_id))
            for agent in scenario.agents:
                conn.execute(
                    "INSERT INTO agents(scenario_id, agent_id, payload) VALUES (?, ?, ?)",
                    (scenario_id, agent.id, json.dumps(agent.to_dict(), ensure_ascii=False)),
                )
            for exit_obj in scenario.exits:
                conn.execute(
                    "INSERT INTO exits(scenario_id, exit_id, payload) VALUES (?, ?, ?)",
                    (scenario_id, exit_obj.id, json.dumps(exit_obj.to_dict(), ensure_ascii=False)),
                )
            for obstacle in scenario.obstacles:
                conn.execute(
                    "INSERT INTO obstacles(scenario_id, obstacle_id, payload) VALUES (?, ?, ?)",
                    (scenario_id, obstacle.id, json.dumps(obstacle.to_dict(), ensure_ascii=False)),
                )
            for event in scenario.events:
                conn.execute(
                    "INSERT INTO events(scenario_id, event_id, payload) VALUES (?, ?, ?)",
                    (scenario_id, event.id, json.dumps(event.to_dict(), ensure_ascii=False)),
                )
            return scenario_id

    def get(self, scenario_id: int) -> EvacuationScenario:
        with self.db.connect() as conn:
            row = conn.execute("SELECT payload FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        if row is None:
            raise KeyError("Сценарий не найден")
        return EvacuationScenario.from_dict(json.loads(row["payload"]))

    def list(self) -> list[tuple[int, str, str]]:
        with self.db.connect() as conn:
            rows = conn.execute("SELECT id, name, created_at FROM scenarios ORDER BY id DESC").fetchall()
        return [(int(row["id"]), str(row["name"]), str(row["created_at"])) for row in rows]


class ResultRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, result: SimulationResult) -> int:
        with self.db.connect() as conn:
            cursor = conn.execute(
                "INSERT INTO simulation_results(scenario_id, status, payload) VALUES (?, ?, ?)",
                (result.scenario_id, result.status.name, "{}"),
            )
            result_id = int(cursor.lastrowid)
            result.id = result_id
            payload = json.dumps(result.to_dict(), ensure_ascii=False)
            conn.execute("UPDATE simulation_results SET payload = ? WHERE id = ?", (payload, result_id))
            for message in result.event_log:
                conn.execute("INSERT INTO event_logs(result_id, message) VALUES (?, ?)", (result_id, message))
            return result_id

    def save_report_path(self, result_id: int, path: str, report_type: str) -> None:
        with self.db.connect() as conn:
            conn.execute(
                "INSERT INTO reports(result_id, path, report_type) VALUES (?, ?, ?)",
                (result_id, path, report_type),
            )

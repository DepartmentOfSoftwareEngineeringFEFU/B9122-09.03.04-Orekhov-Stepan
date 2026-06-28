from __future__ import annotations

import sqlite3

from app.models import Agent, BuildingModel, EvacuationScenario, Exit
from app.simulation import SimulationEngine
from app.storage import Database, ResultRepository, ScenarioRepository


def _scenario() -> EvacuationScenario:
    model = BuildingModel(id=None, name="SQLite test", width=4.0, height=3.0, cell_size=1.0)
    model.add_exit(Exit(id=1, cells={(3, 1)}, width=1.0))
    return EvacuationScenario(id=None, name="SQLite scenario", building_model=model, agents=[Agent(id=1, current_cell=(1, 1))])


def test_database_creates_actual_schema(tmp_path) -> None:
    db_path = tmp_path / "evacuation.db"
    Database(db_path)
    with sqlite3.connect(db_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {
        "building_models",
        "scenarios",
        "agents",
        "exits",
        "obstacles",
        "events",
        "simulation_results",
        "event_logs",
        "reports",
    }.issubset(tables)
    columns = {row[1] for row in sqlite3.connect(db_path).execute("PRAGMA table_info(scenarios)")}
    assert "building_model_id" in columns


def test_sqlite_repositories_save_scenario_and_result(tmp_path) -> None:
    db = Database(tmp_path / "evacuation.db")
    scenario_repo = ScenarioRepository(db)
    result_repo = ResultRepository(db)
    scenario = _scenario()

    scenario_id = scenario_repo.save(scenario)
    loaded = scenario_repo.get(scenario_id)

    assert scenario_id > 0
    assert scenario.id == scenario_id
    assert loaded.id == scenario_id
    assert loaded.building_model.id == scenario.building_model.id
    assert loaded.name == scenario.name
    assert loaded.agents[0].current_cell == (1, 1)

    result = SimulationEngine(loaded).run()
    result_id = result_repo.save(result)

    assert result_id > 0
    assert result.id == result_id
    with db.connect() as conn:
        scenario_row = conn.execute("SELECT building_model_id FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
        assert scenario_row["building_model_id"] == scenario.building_model.id
        assert conn.execute("SELECT COUNT(*) FROM building_models").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM agents WHERE scenario_id = ?", (scenario_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM exits WHERE scenario_id = ?", (scenario_id,)).fetchone()[0] == 1
        assert conn.execute("SELECT status FROM simulation_results WHERE id = ?", (result_id,)).fetchone()[0] == result.status.name

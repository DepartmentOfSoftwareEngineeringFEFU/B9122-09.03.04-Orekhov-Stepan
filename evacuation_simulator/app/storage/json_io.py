from __future__ import annotations

import json
from pathlib import Path

from app.models import BuildingModel, EvacuationScenario, SimulationResult


def export_model_to_json(model: BuildingModel, path: str | Path) -> None:
    _write_json(model.to_dict(), path)


def import_model_from_json(path: str | Path) -> BuildingModel:
    return BuildingModel.from_dict(_read_json(path))


def export_scenario_to_json(scenario: EvacuationScenario, path: str | Path) -> None:
    _write_json(scenario.to_dict(), path)


def import_scenario_from_json(path: str | Path) -> EvacuationScenario:
    return EvacuationScenario.from_dict(_read_json(path))


def export_result_to_json(result: SimulationResult, path: str | Path) -> None:
    _write_json(result.to_dict(), path)


def _write_json(data: dict, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))

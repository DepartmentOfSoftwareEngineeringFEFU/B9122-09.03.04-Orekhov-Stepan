from __future__ import annotations

from app.models import CellType, EnvironmentEvent, EventType, EvacuationScenario, ExitStatus


class EventProcessor:

    def __init__(self, scenario: EvacuationScenario) -> None:
        self.scenario = scenario
        self.event_log: list[str] = []
        self.applied_on_step: list[int] = []
        self.environment_changed = False

    def apply_due_events(self, current_time: float) -> list[int]:
        self.applied_on_step = []
        self.environment_changed = False
        for event in sorted(self.scenario.events, key=lambda item: (item.time, item.id)):
            if event.applied or current_time < event.time:
                continue
            self.apply_event(event, current_time)
            event.applied = True
            self.applied_on_step.append(event.id)
        return self.applied_on_step

    def apply_event(self, event: EnvironmentEvent, current_time: float) -> None:
        building = self.scenario.building_model
        if event.type == EventType.BLOCK_EXIT:
            exit_ids = event.params.get("exit_ids", [])
            if "exit_id" in event.params:
                exit_ids.append(event.params["exit_id"])
            for exit_obj in self.scenario.exits:
                if exit_obj.id in set(int(value) for value in exit_ids):
                    exit_obj.status = ExitStatus.BLOCKED
                    for model_exit in building.exits:
                        if model_exit.id == exit_obj.id:
                            model_exit.status = ExitStatus.BLOCKED
                    self.event_log.append(f"t={current_time:.1f}: выход {exit_obj.id} заблокирован")
            self.environment_changed = True
            return
        if event.type == EventType.ADD_OBSTACLE:
            for x, y in event.area:
                building.set_cell_state(x, y, CellType.OBSTACLE)
            self.event_log.append(f"t={current_time:.1f}: добавлено препятствие, клеток: {len(event.area)}")
            self.environment_changed = True
            return
        if event.type == EventType.ADD_DANGER_ZONE:
            level = max(0.0, min(1.0, float(event.params.get("danger_level", 1.0))))
            for x, y in event.area:
                cell = building.get_cell(x, y)
                cell.cell_type = CellType.DANGER
                cell.danger_level = level
            self.event_log.append(f"t={current_time:.1f}: добавлена опасная зона, клеток: {len(event.area)}")
            self.environment_changed = True
            return
        if event.type == EventType.CHANGE_SMOKE:
            level = max(0.0, min(1.0, float(event.params.get("smoke_level", 0.0))))
            for x, y in event.area:
                building.get_cell(x, y).smoke_level = level
            self.event_log.append(f"t={current_time:.1f}: изменено задымление, клеток: {len(event.area)}")
            self.environment_changed = True
            return
        if event.type == EventType.CHANGE_PASSABILITY:
            passable = bool(event.params.get("passable", True))
            state = CellType.FREE if passable else CellType.OBSTACLE
            for x, y in event.area:
                building.set_cell_state(x, y, state)
            self.event_log.append(f"t={current_time:.1f}: изменена проходимость, клеток: {len(event.area)}")
            self.environment_changed = True

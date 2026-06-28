from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from app.models import AgentState, CellType, EvacuationScenario, ExitStatus, MobilityGroup, SimulationResult


class GridWidget(QWidget):

    cell_clicked = pyqtSignal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.scenario: EvacuationScenario | None = None
        self.result: SimulationResult | None = None
        self.history_step = 0
        self.setMinimumSize(480, 240)

    def set_scenario(self, scenario: EvacuationScenario) -> None:
        self.scenario = scenario
        self.result = None
        self.history_step = 0
        self.update()

    def set_result(self, result: SimulationResult | None) -> None:
        self.result = result
        self.history_step = 0
        self.update()

    def set_history_step(self, step: int) -> None:
        if not self.result or step < 0 or step >= len(self.result.history):
            raise ValueError("Шаг моделирования не найден")
        self.history_step = step
        self.update()

    def mousePressEvent(self, event) -> None:
        if self.scenario is None or event.button() != Qt.MouseButton.LeftButton:
            return
        coord = self._point_to_cell(event.position().x(), event.position().y())
        if coord is not None:
            self.cell_clicked.emit(coord[0], coord[1])

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#f8fbff"))
        if self.scenario is None:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Модель не загружена")
            return

        building = self.scenario.building_model
        cell_px = self._cell_px()
        ox, oy = self._offset(cell_px)
        snapshot = self._snapshot()

        normative_cells: set[tuple[int, int]] = set()
        congestion_cells: set[tuple[int, int]] = set()
        if snapshot:
            normative_cells = {tuple(item["coord"]) for item in snapshot.normative_congestion_zones}
            congestion_cells = {tuple(item["coord"]) for item in snapshot.congestion_zones}

        for cell in building.iter_cells():
            x = ox + cell.x * cell_px
            y = oy + cell.y * cell_px
            painter.fillRect(int(x), int(y), int(cell_px), int(cell_px), self._cell_color(cell.cell_type))
            if cell.cell_type == CellType.DANGER:
                painter.setPen(QPen(QColor("#f97316"), 1))
                painter.drawLine(int(x), int(y + cell_px), int(x + cell_px), int(y))
            if cell.smoke_level > 0:
                painter.fillRect(int(x), int(y), int(cell_px), int(cell_px), QColor(75, 85, 99, int(120 * cell.smoke_level)))
            if (cell.x, cell.y) in congestion_cells:
                painter.setPen(QPen(QColor("#f97316"), 2))
                painter.drawRect(int(x + 2), int(y + 2), int(cell_px - 4), int(cell_px - 4))
            if (cell.x, cell.y) in normative_cells:
                painter.setPen(QPen(QColor("#dc2626"), 2))
                painter.drawRect(int(x + 5), int(y + 5), int(cell_px - 10), int(cell_px - 10))
            painter.setPen(QPen(QColor("#d6dbe1"), 1))
            painter.drawRect(int(x), int(y), int(cell_px), int(cell_px))

        self._draw_exits(painter, cell_px, ox, oy, snapshot)
        self._draw_agents(painter, cell_px, ox, oy, snapshot)

    def _snapshot(self):
        if self.result and self.result.history:
            return self.result.history[min(self.history_step, len(self.result.history) - 1)]
        return None

    def _draw_exits(self, painter: QPainter, cell_px: float, ox: float, oy: float, snapshot) -> None:
        assert self.scenario is not None
        statuses = snapshot.exits if snapshot else {exit_obj.id: exit_obj.status for exit_obj in self.scenario.exits}
        for exit_obj in self.scenario.exits:
            status = statuses.get(exit_obj.id, exit_obj.status)
            color = QColor("#15803d" if status == ExitStatus.OPEN else "#991b1b")
            painter.setPen(QPen(color, 3))
            painter.setBrush(QColor(22, 163, 74, 75) if status == ExitStatus.OPEN else QColor(153, 27, 27, 75))
            for index, (cx, cy) in enumerate(sorted(exit_obj.cells)):
                x = ox + cx * cell_px
                y = oy + cy * cell_px
                painter.drawRect(int(x + 2), int(y + 2), int(cell_px - 4), int(cell_px - 4))
                if index == 0 and cell_px >= 16:
                    painter.drawText(int(x), int(y), int(cell_px), int(cell_px), Qt.AlignmentFlag.AlignCenter, f"E{exit_obj.id}")

    def _draw_agents(self, painter: QPainter, cell_px: float, ox: float, oy: float, snapshot) -> None:
        assert self.scenario is not None
        agents_by_id = {agent.id: agent for agent in self.scenario.agents}
        if snapshot:
            agent_rows = snapshot.agents
        else:
            agent_rows = [
                type("AgentRow", (), {"id": a.id, "x": a.current_cell[0], "y": a.current_cell[1], "state": a.state})
                for a in self.scenario.agents
            ]

        for row in agent_rows:
            if row.state == AgentState.EVACUATED:
                continue
            source_agent = agents_by_id.get(row.id)
            group = source_agent.mobility_group if source_agent else MobilityGroup.M0_3
            x = ox + row.x * cell_px
            y = oy + row.y * cell_px
            color = self._group_color(group)
            if row.state == AgentState.DELAYED:
                color = QColor("#b91c1c")
            elif row.state == AgentState.NEEDS_RESCUE:
                color = QColor("#7c3aed")

            painter.setBrush(color)
            painter.setPen(QPen(QColor("#ffffff"), 1))
            margin = max(3, int(cell_px * 0.16))
            painter.drawEllipse(int(x + margin), int(y + margin), int(cell_px - 2 * margin), int(cell_px - 2 * margin))

    def _cell_color(self, state: CellType) -> QColor:
        return {
            CellType.FREE: QColor("#ffffff"),
            CellType.OCCUPIED: QColor("#dbeafe"),
            CellType.WALL: QColor("#1f2937"),
            CellType.OBSTACLE: QColor("#6b7280"),
            CellType.EXIT: QColor("#bbf7d0"),
            CellType.DANGER: QColor("#fed7aa"),
        }.get(state, QColor("#ffffff"))

    def _group_color(self, group: MobilityGroup) -> QColor:
        palette = {
            MobilityGroup.M0: "#64748b",
            MobilityGroup.M0_1: "#0ea5e9",
            MobilityGroup.M0_2: "#0284c7",
            MobilityGroup.M0_3: "#2563eb",
            MobilityGroup.M0_4: "#4f46e5",
            MobilityGroup.M0_5: "#7c3aed",
            MobilityGroup.M0_6: "#9333ea",
            MobilityGroup.M0_7: "#c026d3",
            MobilityGroup.M1: "#059669",
            MobilityGroup.M2: "#16a34a",
            MobilityGroup.M3: "#65a30d",
            MobilityGroup.M4: "#ca8a04",
            MobilityGroup.NM: "#dc2626",
            MobilityGroup.NT: "#991b1b",
            MobilityGroup.NO: "#ea580c",
        }
        return QColor(palette.get(group, "#2563eb"))

    def _cell_px(self) -> float:
        assert self.scenario is not None
        building = self.scenario.building_model
        return max(6.0, min((self.width() - 24) / building.cols, (self.height() - 24) / building.rows))

    def _offset(self, cell_px: float) -> tuple[float, float]:
        assert self.scenario is not None
        building = self.scenario.building_model
        return (self.width() - building.cols * cell_px) / 2, (self.height() - building.rows * cell_px) / 2

    def _point_to_cell(self, px: float, py: float) -> tuple[int, int] | None:
        if self.scenario is None:
            return None
        cell_px = self._cell_px()
        ox, oy = self._offset(cell_px)
        x = int((px - ox) // cell_px)
        y = int((py - oy) // cell_px)
        return (x, y) if self.scenario.building_model.in_bounds(x, y) else None

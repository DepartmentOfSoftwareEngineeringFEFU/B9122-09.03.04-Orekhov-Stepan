from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QVector3D
from PyQt6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.models import AgentState, CellType, EvacuationScenario, ExitStatus, MobilityGroup, SimulationResult

try:
    import pyqtgraph.opengl as gl
except ImportError as exc:
    gl = None
    GL_IMPORT_ERROR = exc
else:
    GL_IMPORT_ERROR = None


Color = tuple[float, float, float, float]


@dataclass(slots=True)
class _AgentViewRow:
    id: int
    x: int
    y: int
    state: AgentState


class Visualization3DWindow(QWidget):

    def __init__(self, scenario: EvacuationScenario, result: SimulationResult | None = None) -> None:
        if gl is None:
            raise RuntimeError(
                "Для 3D-визуализации установите зависимости: pip install pyqtgraph PyOpenGL"
            ) from GL_IMPORT_ERROR
        super().__init__()
        self.setWindowTitle("3D-визуализация эвакуации")
        self.resize(1180, 760)
        self.scenario = scenario
        self.result = result
        self.static_items: list[object] = []
        self.dynamic_items: list[object] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_step)

        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor("#111827")
        self.view.opts["distance"] = max(scenario.building_model.width, scenario.building_model.height) * 1.25
        self.view.opts["elevation"] = 48
        self.view.opts["azimuth"] = -42
        self.view.setCameraPosition(
            pos=QVector3D(
                scenario.building_model.width / 2,
                scenario.building_model.height / 2,
                0.0,
            )
        )

        self.history_slider = QSlider(Qt.Orientation.Horizontal)
        max_step = max(0, len(result.history) - 1) if result else 0
        self.history_slider.setRange(0, max_step)
        self.history_slider.valueChanged.connect(self._redraw_dynamic)
        self.time_label = QLabel()

        self.show_walls = QCheckBox("Стены")
        self.show_obstacles = QCheckBox("Препятствия")
        self.show_danger = QCheckBox("Опасные зоны")
        self.show_agents = QCheckBox("Агенты")
        self.show_congestion = QCheckBox("Заторы")
        for checkbox in [self.show_walls, self.show_obstacles, self.show_danger, self.show_agents, self.show_congestion]:
            checkbox.setChecked(True)
            checkbox.toggled.connect(self._rebuild_scene)

        self._build_ui()
        self._rebuild_scene()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.addWidget(self.view, 1)

        panel = QWidget()
        panel.setFixedWidth(280)
        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("3D-просмотр"))
        panel_layout.addWidget(self.time_label)
        panel_layout.addWidget(QLabel("Шаг истории"))
        panel_layout.addWidget(self.history_slider)

        buttons = QGridLayout()
        for index, (text, handler) in enumerate(
            [
                ("Play/Pause", self._toggle_play),
                ("Сброс камеры", self._reset_camera),
                ("К началу", self._to_start),
                ("К концу", self._to_end),
            ]
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            buttons.addWidget(button, index // 2, index % 2)
        panel_layout.addLayout(buttons)

        panel_layout.addWidget(QLabel("Слои"))
        panel_layout.addWidget(self.show_walls)
        panel_layout.addWidget(self.show_obstacles)
        panel_layout.addWidget(self.show_danger)
        panel_layout.addWidget(self.show_agents)
        panel_layout.addWidget(self.show_congestion)
        panel_layout.addStretch(1)
        root.addWidget(panel)

    def _rebuild_scene(self) -> None:
        self.view.clear()
        self.static_items.clear()
        self.dynamic_items.clear()
        self._draw_floor_and_grid()
        self._draw_static_cells()
        self._redraw_dynamic()

    def _draw_floor_and_grid(self) -> None:
        building = self.scenario.building_model
        self._add_box(
            center=(building.width / 2, building.height / 2, -0.03),
            size=(building.width, building.height, 0.04),
            color=(0.78, 0.84, 0.90, 1.0),
        )
        grid = gl.GLGridItem()
        grid.setSize(x=building.width, y=building.height, z=0)
        grid.setSpacing(x=building.cell_size, y=building.cell_size, z=1)
        grid.translate(building.width / 2, building.height / 2, 0.01)
        self.view.addItem(grid)
        self.static_items.append(grid)

    def _draw_static_cells(self) -> None:
        building = self.scenario.building_model
        for cell in building.iter_cells():
            x = (cell.x + 0.5) * building.cell_size
            y = (cell.y + 0.5) * building.cell_size
            if cell.cell_type == CellType.WALL and self.show_walls.isChecked():
                self._add_box((x, y, 1.25), (building.cell_size, building.cell_size, 2.5), (0.08, 0.11, 0.18, 1.0))
            elif cell.cell_type == CellType.OBSTACLE and self.show_obstacles.isChecked():
                self._add_box((x, y, 0.45), (building.cell_size, building.cell_size, 0.9), (0.34, 0.38, 0.45, 1.0))
            elif cell.cell_type == CellType.DANGER and self.show_danger.isChecked():
                self._add_box((x, y, 0.025), (building.cell_size, building.cell_size, 0.05), (0.96, 0.45, 0.12, 0.55))

    def _redraw_dynamic(self) -> None:
        for item in self.dynamic_items:
            self.view.removeItem(item)
        self.dynamic_items.clear()
        step = self.history_slider.value()
        snapshot = self.result.history[step] if self.result and self.result.history else None
        self.time_label.setText(f"Время: {snapshot.time:.1f} с" if snapshot else "Время: исходное состояние")

        self._draw_exits()
        if self.show_congestion.isChecked() and snapshot:
            self._draw_congestion(snapshot)
        if self.show_agents.isChecked():
            self._draw_agents(snapshot)

    def _draw_exits(self) -> None:
        building = self.scenario.building_model
        for exit_obj in self.scenario.exits:
            status = self._current_exit_status(exit_obj.id)
            color = (0.08, 0.55, 0.25, 0.9) if status == ExitStatus.OPEN else (0.72, 0.10, 0.10, 0.9)
            text_color = (0.02, 0.12, 0.08, 1.0) if status == ExitStatus.OPEN else (0.45, 0.03, 0.03, 1.0)
            for cx, cy in exit_obj.cells:
                x = (cx + 0.5) * building.cell_size
                y = (cy + 0.5) * building.cell_size
                self._add_box((x, y, 0.08), (building.cell_size, building.cell_size, 0.16), color, dynamic=True)
                self._add_text((x, y, 0.35), f"E{exit_obj.id}", text_color, dynamic=True)

    def _draw_congestion(self, snapshot) -> None:
        building = self.scenario.building_model
        cells: dict[tuple[int, int], Color] = {}
        for item in snapshot.normative_congestion_zones:
            cells[tuple(item["coord"])] = (0.88, 0.09, 0.09, 0.55)
        for item in snapshot.congestion_zones:
            cells[tuple(item["coord"])] = (0.98, 0.45, 0.05, 0.55)
        for cx, cy in cells:
            self._add_box(
                center=((cx + 0.5) * building.cell_size, (cy + 0.5) * building.cell_size, 0.07),
                size=(building.cell_size, building.cell_size, 0.07),
                color=cells[(cx, cy)],
                dynamic=True,
            )

    def _draw_agents(self, snapshot) -> None:
        rows = self._agent_rows(snapshot)
        if not rows:
            return
        building = self.scenario.building_model
        agents_by_id = {agent.id: agent for agent in self.scenario.agents}
        labels: list[tuple[tuple[float, float, float], str, Color]] = []
        for row in rows:
            if row.state == AgentState.EVACUATED:
                continue
            agent = agents_by_id.get(row.id)
            group = agent.mobility_group if agent else MobilityGroup.M0_3
            color = self._group_color(group)
            if row.state == AgentState.DELAYED:
                color = (0.73, 0.11, 0.11, 1.0)
            elif row.state == AgentState.NEEDS_RESCUE:
                color = (0.49, 0.23, 0.93, 1.0)
            x = (row.x + 0.5) * building.cell_size
            y = (row.y + 0.5) * building.cell_size
            self._add_agent_body((x, y, 0.80), color)
            labels.append(((x, y, 1.55), str(row.id), (1.0, 1.0, 1.0, 1.0)))
        for pos, text, color in labels:
            self._add_text(pos, text, color, dynamic=True)

    def _agent_rows(self, snapshot) -> list[_AgentViewRow]:
        if snapshot:
            return [_AgentViewRow(row.id, row.x, row.y, row.state) for row in snapshot.agents]
        return [
            _AgentViewRow(agent.id, agent.current_cell[0], agent.current_cell[1], agent.state)
            for agent in self.scenario.agents
        ]

    def _current_exit_status(self, exit_id: int) -> ExitStatus:
        if self.result and self.result.history:
            snapshot = self.result.history[self.history_slider.value()]
            return snapshot.exits.get(exit_id, ExitStatus.OPEN)
        exit_obj = next((item for item in self.scenario.exits if item.id == exit_id), None)
        return exit_obj.status if exit_obj else ExitStatus.OPEN

    def _add_box(self, center: tuple[float, float, float], size: tuple[float, float, float], color: Color, dynamic: bool = False) -> None:
        corner = np.array([[center[0] - size[0] / 2, center[1] - size[1] / 2, center[2] - size[2] / 2]], dtype=float)
        dimensions = np.array([size], dtype=float)
        item = gl.GLBarGraphItem(pos=corner, size=dimensions)
        item.setColor(color)
        self.view.addItem(item)
        (self.dynamic_items if dynamic else self.static_items).append(item)

    def _add_agent_body(self, center: tuple[float, float, float], color: Color) -> None:
        body = gl.GLMeshItem(
            meshdata=gl.MeshData.sphere(rows=32, cols=48, radius=0.24),
            color=color,
            shader="shaded",
            smooth=True,
            drawFaces=True,
            drawEdges=False,
        )
        body.translate(*center)
        self.view.addItem(body)
        self.dynamic_items.append(body)

        base = gl.GLMeshItem(
            meshdata=gl.MeshData.cylinder(rows=24, cols=48, radius=[0.17, 0.22], length=0.55),
            color=color,
            shader="shaded",
            smooth=True,
            drawFaces=True,
            drawEdges=False,
        )
        base.translate(center[0], center[1], 0.25)
        self.view.addItem(base)
        self.dynamic_items.append(base)

    def _add_text(self, pos: tuple[float, float, float], text: str, color: Color, dynamic: bool = False) -> None:
        item = gl.GLTextItem(pos=pos, text=text, color=color)
        self.view.addItem(item)
        (self.dynamic_items if dynamic else self.static_items).append(item)

    def _toggle_play(self) -> None:
        if self.history_slider.maximum() == 0:
            return
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(220)

    def _next_step(self) -> None:
        if self.history_slider.value() >= self.history_slider.maximum():
            self.timer.stop()
            return
        self.history_slider.setValue(self.history_slider.value() + 1)

    def _to_start(self) -> None:
        self.history_slider.setValue(0)

    def _to_end(self) -> None:
        self.history_slider.setValue(self.history_slider.maximum())

    def _reset_camera(self) -> None:
        building = self.scenario.building_model
        self.view.setCameraPosition(
            pos=QVector3D(building.width / 2, building.height / 2, 0.0),
            distance=max(building.width, building.height) * 1.45,
            elevation=48,
            azimuth=-42,
        )

    def _group_color(self, group: MobilityGroup) -> Color:
        palette = {
            MobilityGroup.M0: (0.39, 0.45, 0.55, 1.0),
            MobilityGroup.M0_1: (0.05, 0.65, 0.91, 1.0),
            MobilityGroup.M0_2: (0.01, 0.52, 0.78, 1.0),
            MobilityGroup.M0_3: (0.15, 0.39, 0.92, 1.0),
            MobilityGroup.M0_4: (0.31, 0.27, 0.90, 1.0),
            MobilityGroup.M0_5: (0.49, 0.23, 0.93, 1.0),
            MobilityGroup.M0_6: (0.58, 0.20, 0.92, 1.0),
            MobilityGroup.M0_7: (0.75, 0.15, 0.83, 1.0),
            MobilityGroup.M1: (0.02, 0.59, 0.41, 1.0),
            MobilityGroup.M2: (0.09, 0.64, 0.29, 1.0),
            MobilityGroup.M3: (0.40, 0.64, 0.05, 1.0),
            MobilityGroup.M4: (0.79, 0.54, 0.02, 1.0),
            MobilityGroup.NM: (0.86, 0.15, 0.15, 1.0),
            MobilityGroup.NT: (0.60, 0.10, 0.10, 1.0),
            MobilityGroup.NO: (0.92, 0.35, 0.05, 1.0),
        }
        return palette.get(group, (0.15, 0.39, 0.92, 1.0))

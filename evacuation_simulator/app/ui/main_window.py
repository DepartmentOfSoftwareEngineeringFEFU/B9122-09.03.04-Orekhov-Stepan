from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.models import (
    Agent,
    BuildingModel,
    CellType,
    ClothesType,
    EnvironmentEvent,
    EventType,
    EvacuationScenario,
    Exit,
    ExitStatus,
    MobilityGroup,
    MobilityLevel,
    Obstacle,
    SimulationParameters,
)
from app.reports import ReportGenerator, export_agents_csv
from app.simulation import SimulationEngine, SimulationError
from app.storage import Database, ResultRepository, ScenarioRepository, export_scenario_to_json, import_scenario_from_json
from app.visualization import Visualization3DWindow
from .dialogs import BlockExitDialog
from .grid_widget import GridWidget
from .icons import line_icon
from .panels import LogPanel, double_spin


class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Моделирование эвакуации людей")
        self.resize(1440, 900)
        self.project_root = Path(__file__).resolve().parents[2]
        self.scenario = self._demo_scenario()
        self.run_scenario: EvacuationScenario | None = None
        self.result = None
        self.view3d_window: Visualization3DWindow | None = None
        self.report_generator = ReportGenerator()
        self.database = Database()
        self.scenario_repository = ScenarioRepository(self.database)
        self.result_repository = ResultRepository(self.database)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_animation_step)

        self.grid = GridWidget()
        self.grid.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.grid.cell_clicked.connect(self._cell_clicked)
        self.log = LogPanel()
        self.result_table = self._table(["ID", "Группа", "Состояние", "t эвак., с", "Длина пути", "Причина"])
        self.agent_table = self._table(["ID", "X", "Y", "Группа", "Одежда", "Скорость"])
        self.events_table = self._table(["ID", "Тип", "Время", "Параметры"])

        self._build_ui()
        self._build_menu()
        self._load_scenario_into_controls()
        self.grid.set_scenario(self.scenario)
        self._refresh_scenario_list()
        self._refresh_object_lists()
        self._log("Загружен демонстрационный сценарий. Разделы доступны через верхнее меню.")

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stage_buttons: dict[str, QPushButton] = {}
        self.pages = QStackedWidget()
        self.scenario_page = self._scenario_page()
        self.model_page = self._context_page(self._model_page())
        self.agents_page = self._context_page(self._agents_page())
        self.events_page = self._events_page()
        self.simulation_page = self._context_page(self._simulation_page())
        self.reports_page = self._reports_page()
        for page in [self.scenario_page, self.model_page, self.agents_page, self.events_page, self.simulation_page, self.reports_page]:
            page.setMinimumHeight(80)
            page.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
            self.pages.addWidget(page)
        self.pages.setMinimumHeight(80)
        self.pages.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)

        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_panel.setMinimumSize(300, 140)
        right_panel.setMaximumWidth(380)
        right_panel.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)
        self.section_label = QLabel()
        self.section_label.setObjectName("sectionTitle")
        right_layout.addWidget(self.section_label)
        right_layout.addWidget(self.pages, 1)
        right_layout.addWidget(self._quick_stats_panel())
        right_layout.addWidget(self._status_panel())

        map_panel = QFrame()
        map_panel.setObjectName("mapPanel")
        map_layout = QVBoxLayout(map_panel)
        map_layout.setContentsMargins(12, 10, 12, 8)
        map_layout.setSpacing(6)
        map_header = QHBoxLayout()
        map_title = QLabel("Модель помещения")
        map_title.setObjectName("mapTitle")
        self.map_meta = QLabel()
        self.map_meta.setObjectName("mutedLabel")
        map_header.addWidget(map_title)
        map_header.addStretch(1)
        map_header.addWidget(self.map_meta)
        map_layout.addLayout(map_header)
        map_layout.addWidget(self.grid, 1)
        self.legend_label = QLabel()
        self.legend_label.setObjectName("legend")
        self.legend_label.setWordWrap(True)
        map_layout.addWidget(self.legend_label)

        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setMinimumHeight(300)
        self.top_splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Ignored)
        self.top_splitter.addWidget(map_panel)
        self.top_splitter.addWidget(right_panel)
        self.top_splitter.setSizes([1050, 340])
        self.top_splitter.setStretchFactor(0, 1)
        self.top_splitter.setStretchFactor(1, 0)

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.agent_table, "Агенты")
        self.bottom_tabs.addTab(self.events_table, "События")
        self.bottom_tabs.addTab(self.result_table, "Результаты")
        self.bottom_tabs.addTab(self.log, "Журнал")
        self.bottom_tabs.setMinimumHeight(80)
        self.bottom_tabs.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.bottom_panel = QFrame()
        self.bottom_panel.setObjectName("bottomPanel")
        self.bottom_panel.setMinimumHeight(150)
        self.bottom_panel.setMaximumHeight(480)
        self.bottom_panel.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        bottom_layout = QVBoxLayout(self.bottom_panel)
        bottom_layout.setContentsMargins(10, 6, 10, 8)
        bottom_layout.setSpacing(4)
        bottom_header = QHBoxLayout()
        bottom_title = QLabel("Данные сценария")
        bottom_title.setObjectName("bottomTitle")
        bottom_header.addWidget(bottom_title)
        bottom_header.addStretch(1)
        expand_button = QPushButton("Развернуть панель")
        expand_button.setIcon(line_icon("up"))
        expand_button.setToolTip("Увеличить нижнюю панель результатов и журнала.")
        expand_button.clicked.connect(self._expand_bottom_panel)
        collapse_button = QPushButton("Свернуть панель")
        collapse_button.setIcon(line_icon("down"))
        collapse_button.setToolTip("Уменьшить нижнюю панель.")
        collapse_button.clicked.connect(self._collapse_bottom_panel)
        bottom_header.addWidget(expand_button)
        bottom_header.addWidget(collapse_button)
        bottom_layout.addLayout(bottom_header)
        bottom_layout.addWidget(self.bottom_tabs, 1)
        self.bottom_panel_expanded = False

        self.main_vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_vertical_splitter.addWidget(self.top_splitter)
        self.main_vertical_splitter.addWidget(self.bottom_panel)
        self.main_vertical_splitter.setHandleWidth(12)
        self.main_vertical_splitter.setSizes([620, 260])
        self.main_vertical_splitter.setStretchFactor(0, 3)
        self.main_vertical_splitter.setStretchFactor(1, 2)
        self.main_vertical_splitter.setCollapsible(0, False)
        self.main_vertical_splitter.setCollapsible(1, False)
        self.main_vertical_splitter.setStyleSheet(
            """
            QSplitter::handle:vertical {
                background: #64748b;
                min-height: 12px;
                border-top: 4px solid #e2e8f0;
                border-bottom: 4px solid #334155;
            }
            """
        )

        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(8, 8, 8, 8)
        workspace_layout.setSpacing(8)
        workspace_layout.addWidget(self._side_bar())
        workspace_layout.addWidget(self.main_vertical_splitter, 1)
        root_layout.addWidget(workspace, 1)
        self.setCentralWidget(root)
        self._apply_theme()
        self._show_stage("model_page")

    def _context_page(self, content: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setObjectName("contextPageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content)
        return scroll

    def _side_bar(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("sideRail")
        self.side_rail = rail
        self.side_collapsed = True
        rail.setFixedWidth(48)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(5, 8, 5, 8)
        layout.setSpacing(6)
        toggle_button = QToolButton()
        toggle_button.setIcon(line_icon("right"))
        toggle_button.setToolTip("Развернуть левую панель навигации.")
        toggle_button.clicked.connect(self._toggle_side_bar)
        toggle_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        layout.addWidget(toggle_button)
        self.side_toggle_button = toggle_button
        group = QButtonGroup(self)
        group.setExclusive(True)
        items = [
            ("folder", "Сценарии", "scenario_page", "Сценарии: открыть или сохранить файл сценария"),
            ("grid", "Помещение", "model_page", "Помещение: размеры модели и редактирование клеток"),
            ("users", "Агенты", "agents_page", "Агенты: параметры и размещение людей"),
            ("warning", "События", "events_page", "События: блокировки выходов и изменения среды"),
            ("play", "Расчёт", "simulation_page", "Расчёт: параметры моделирования и просмотр истории"),
            ("file", "Отчёт", "reports_page", "Отчёт: экспорт результатов в DOCX или CSV"),
        ]
        self.side_buttons: list[QToolButton] = []
        for icon_name, full_text, page_attr, tooltip in items:
            button = QToolButton()
            button.setIcon(line_icon(icon_name))
            button.setText(full_text)
            button.setCheckable(True)
            button.setToolTip(tooltip)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.clicked.connect(lambda checked=False, name=page_attr: self._show_stage(name))
            layout.addWidget(button)
            group.addButton(button)
            self.stage_buttons[page_attr] = button
            self.side_buttons.append(button)
        layout.addStretch(1)
        view3d_button = QToolButton()
        view3d_button.setIcon(line_icon("cube"))
        view3d_button.setText("3D-визуализация")
        view3d_button.setToolTip("Открыть интерактивную 3D-визуализацию текущей модели.")
        view3d_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        view3d_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        view3d_button.clicked.connect(self._open_3d_view)
        layout.addWidget(view3d_button)
        self.side_3d_button = view3d_button
        return rail

    def _toggle_side_bar(self) -> None:
        self.side_collapsed = not self.side_collapsed
        self.side_rail.setFixedWidth(48 if self.side_collapsed else 174)
        self.side_toggle_button.setIcon(line_icon("right" if self.side_collapsed else "left"))
        self.side_toggle_button.setToolTip(
            "Развернуть левую панель навигации." if self.side_collapsed else "Свернуть левую панель навигации."
        )
        style = Qt.ToolButtonStyle.ToolButtonIconOnly if self.side_collapsed else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        for button in self.side_buttons:
            button.setToolButtonStyle(style)
        self.side_3d_button.setToolButtonStyle(style)

    def _quick_stats_panel(self) -> QWidget:
        panel = QGroupBox("Быстрые показатели")
        layout = QGridLayout(panel)
        self.stat_agents = QLabel()
        self.stat_exits = QLabel()
        self.stat_events = QLabel()
        self.stat_cell = QLabel()
        for row, (title, value) in enumerate(
            [
                ("Агенты", self.stat_agents),
                ("Выходы", self.stat_exits),
                ("События", self.stat_events),
                ("Шаг сетки", self.stat_cell),
            ]
        ):
            layout.addWidget(QLabel(title), row, 0)
            value.setAlignment(Qt.AlignmentFlag.AlignRight)
            value.setObjectName("statValue")
            layout.addWidget(value, row, 1)
        return panel

    def _status_panel(self) -> QWidget:
        panel = QGroupBox("Состояние модели")
        layout = QVBoxLayout(panel)
        self.model_status = QLabel()
        self.model_status.setWordWrap(True)
        layout.addWidget(self.model_status)
        return panel

    def _show_calculation(self) -> None:
        self._show_stage("simulation_page")

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f3f6fa;
                color: #172033;
                font-family: "Segoe UI";
                font-size: 12px;
            }
            QFrame#mapPanel, QFrame#rightPanel, QFrame#bottomPanel {
                background: #ffffff;
                border: 1px solid #d9e1ec;
            }
            QFrame#sideRail {
                background: #ffffff;
                border: 1px solid #d9e1ec;
                border-radius: 6px;
            }
            QLabel#appTitle, QLabel#mapTitle, QLabel#sectionTitle, QLabel#bottomTitle {
                font-weight: 700;
                color: #172033;
            }
            QLabel#appTitle { font-size: 14px; }
            QLabel#mapTitle, QLabel#sectionTitle { font-size: 13px; }
            QLabel#mutedLabel { color: #64748b; }
            QLabel#legend {
                color: #475569;
                padding: 3px 0 0 0;
            }
            QLabel#statValue { font-weight: 700; color: #2563eb; }
            QPushButton, QToolButton {
                background: #ffffff;
                border: 1px solid #d6deea;
                border-radius: 5px;
                padding: 6px 10px;
            }
            QPushButton:hover, QToolButton:hover {
                background: #eff6ff;
                border-color: #93c5fd;
            }
            QPushButton#primaryButton {
                background: #2563eb;
                color: white;
                border-color: #2563eb;
                font-weight: 600;
                min-width: 74px;
            }
            QPushButton#successButton {
                background: #16a34a;
                color: white;
                border-color: #16a34a;
                font-weight: 600;
                min-width: 74px;
            }
            QToolButton {
                min-width: 26px;
                min-height: 26px;
                padding: 3px;
                font-weight: 700;
            }
            QToolButton:checked {
                background: #dbeafe;
                color: #1d4ed8;
                border-color: #93c5fd;
            }
            QGroupBox {
                background: #ffffff;
                border: 1px solid #d9e1ec;
                border-radius: 6px;
                margin-top: 10px;
                padding: 9px 6px 6px 6px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 3px;
            }
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: #ffffff;
                border: 1px solid #d6deea;
                border-radius: 4px;
                padding: 4px;
                min-height: 20px;
            }
            QTabWidget::pane {
                background: #ffffff;
                border: 1px solid #d9e1ec;
            }
            QTabBar::tab {
                background: #f8fafc;
                border: 1px solid #d9e1ec;
                padding: 6px 12px;
            }
            QTabBar::tab:selected {
                background: #dbeafe;
                color: #1d4ed8;
            }
            QTableWidget {
                background: #ffffff;
                alternate-background-color: #f8fafc;
                gridline-color: #e2e8f0;
            }
            QHeaderView::section {
                background: #eef3f8;
                border: none;
                border-right: 1px solid #d9e1ec;
                padding: 5px;
                font-weight: 600;
            }
            QSplitter::handle:horizontal {
                background: #d9e1ec;
                width: 5px;
            }
            QSplitter::handle:vertical {
                background: #b8c5d6;
            }
            QScrollArea#contextPageScroll {
                background: transparent;
                border: none;
            }
            """
        )

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("Файл")
        file_menu.addAction("Загрузить сценарий...", self._load_json)
        file_menu.addAction("Сохранить сценарий...", self._save_json)
        file_menu.addAction("Сохранить сценарий в БД", self._save_scenario_to_database)
        file_menu.addAction("Загрузить последний из БД", self._load_latest_scenario_from_database)
        file_menu.addSeparator()
        file_menu.addAction("Выход", self.close)

        scenario_menu = menu.addMenu("Сценарий")
        scenario_menu.addAction("Список сценариев", lambda: self._show_stage("scenario_page"))
        scenario_menu.addAction("Создать модель", lambda: self._show_stage("model_page"))

        view_menu = menu.addMenu("Вид")
        view_menu.addAction("Помещение", lambda: self._show_stage("model_page"))
        view_menu.addAction("Агенты", lambda: self._show_stage("agents_page"))
        view_menu.addAction("События", lambda: self._show_stage("events_page"))
        view_menu.addAction("Расчет", lambda: self._show_stage("simulation_page"))
        view_menu.addSeparator()
        view_menu.addAction("3D-визуализация", self._open_3d_view)

        report_menu = menu.addMenu("Отчеты")
        report_menu.addAction("Открыть панель отчетов", lambda: self._show_stage("reports_page"))
        report_menu.addAction("Сформировать DOCX", self._save_docx)
        report_menu.addAction("Сформировать CSV", self._save_csv)

    def _show_stage(self, page_attr: str) -> None:
        if getattr(self, "bottom_panel_expanded", False):
            self._collapse_bottom_panel()
        page = getattr(self, page_attr)
        self.pages.setCurrentWidget(page)
        titles = {
            "scenario_page": "Параметры сценария",
            "model_page": "Параметры помещения",
            "agents_page": "Параметры агента",
            "events_page": "Параметры события",
            "simulation_page": "Параметры расчёта",
            "reports_page": "Параметры отчёта",
        }
        self.section_label.setText(titles.get(page_attr, "Параметры"))
        for attr, button in self.stage_buttons.items():
            button.setChecked(attr == page_attr)

    def _expand_bottom_panel(self) -> None:
        self.bottom_panel_expanded = True
        self.top_splitter.hide()
        self.bottom_panel.setMaximumHeight(16777215)
        self.main_vertical_splitter.setSizes([0, self.main_vertical_splitter.height()])

    def _collapse_bottom_panel(self) -> None:
        self.bottom_panel_expanded = False
        self.top_splitter.show()
        self.bottom_panel.setMaximumHeight(480)
        self.main_vertical_splitter.setSizes([690, 150])

    def _scenario_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._intro("Стартовая панель: выберите демонстрационный сценарий, загрузите JSON или сохраните текущую работу."))
        self.scenario_list = QComboBox()
        layout.addWidget(QLabel("Сценарии"))
        self.scenario_list.setToolTip("Выберите один из сохранённых JSON-сценариев.")
        layout.addWidget(self.scenario_list)
        self._button(layout, "Загрузить выбранный", self._load_selected_scenario)
        self._button(layout, "Загрузить из файла...", self._load_json)
        self._button(layout, "Сохранить текущий сценарий", self._save_json)
        self._button(layout, "Сохранить сценарий в БД", self._save_scenario_to_database)
        self._button(layout, "Загрузить последний из БД", self._load_latest_scenario_from_database)
        self._button(layout, "Обновить список", self._refresh_scenario_list)
        layout.addStretch(1)
        return page

    def _model_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._intro("Геометрия помещения. Выберите объект и кликом по карте изменяйте клетки."))

        model_group = QGroupBox("Помещение")
        form = QFormLayout(model_group)
        self.model_name = QLineEdit()
        self.model_width = double_spin(0.1, 500.0, 20.0)
        self.model_height = double_spin(0.1, 500.0, 10.0)
        self.model_cell_size = double_spin(0.1, 10.0, 0.5, 0.1)
        self._add_row(form, "Название", self.model_name, "Имя помещения или сценария для отображения в отчетах.")
        self._add_row(form, "Ширина, м", self.model_width, "Реальный горизонтальный размер помещения в метрах.")
        self._add_row(form, "Высота, м", self.model_height, "Реальный вертикальный размер помещения в метрах.")
        self._add_row(form, "Клетка, м", self.model_cell_size, "Сторона одной клетки сетки. Меньше значение - выше детализация.")
        layout.addWidget(model_group)

        edit_group = QGroupBox("Редактирование карты")
        edit_form = QFormLayout(edit_group)
        self.tool = QComboBox()
        self.tool.addItems(["Свободная клетка", "Стена", "Препятствие", "Выход", "Опасная зона", "Агент", "Выбор агента"])
        self.exit_width = double_spin(0.1, 10.0, 1.0, 0.1)
        self.exit_capacity = QSpinBox()
        self.exit_capacity.setRange(1, 100)
        self.exit_capacity.setValue(1)
        self._add_row(edit_form, "Инструмент", self.tool, "Что будет сделано при клике по клетке карты.")
        self._add_row(edit_form, "Ширина выхода, м", self.exit_width, "Физическая ширина нового выхода.")
        self._add_row(edit_form, "Пропуск, чел/с", self.exit_capacity, "Сколько агентов может пройти через новый выход за секунду.")
        layout.addWidget(edit_group)

        self._button(layout, "Создать новую модель", self._new_model)
        layout.addStretch(1)
        return page

    def _agents_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._intro("Добавляйте агентов инструментом «Агент» или выбирайте существующего агента на карте для редактирования."))

        add_group = QGroupBox("Новый агент")
        add_form = QFormLayout(add_group)
        self.agent_group = QComboBox()
        self.agent_group.addItems([group.name for group in MobilityGroup])
        self.agent_group.setCurrentText("M0_3")
        self.agent_clothes = QComboBox()
        self.agent_clothes.addItems([item.name for item in ClothesType])
        self.agent_speed = double_spin(0.01, 5.0, 1.25, 0.05)
        self._add_row(add_form, "Группа", self.agent_group, "Группа мобильности для новых агентов.")
        self._add_row(add_form, "Одежда", self.agent_clothes, "Зимняя одежда увеличивает эффективную площадь проекции на 25%.")
        self._add_row(add_form, "Скорость, м/с", self.agent_speed, "Базовая скорость нового агента.")
        layout.addWidget(add_group)

        editor = QGroupBox("Выбранный агент")
        editor_form = QFormLayout(editor)
        self.edit_agent_id = QSpinBox()
        self.edit_agent_id.setRange(1, 1)
        self.edit_agent_id.valueChanged.connect(self._load_agent_to_editor)
        self.edit_agent_group = QComboBox()
        self.edit_agent_group.addItems([group.name for group in MobilityGroup])
        self.edit_agent_clothes = QComboBox()
        self.edit_agent_clothes.addItems([item.name for item in ClothesType])
        self.edit_agent_speed = double_spin(0.01, 5.0, 1.25, 0.05)
        self._add_row(editor_form, "ID", self.edit_agent_id, "Номер редактируемого агента. Его можно выбрать кликом по агенту на карте.")
        self._add_row(editor_form, "Группа", self.edit_agent_group, "Группа мобильности выбранного агента.")
        self._add_row(editor_form, "Одежда", self.edit_agent_clothes, "Тип одежды выбранного агента.")
        self._add_row(editor_form, "Скорость, м/с", self.edit_agent_speed, "Базовая скорость выбранного агента.")
        layout.addWidget(editor)
        self._button(layout, "Применить изменения", self._apply_agent_changes)
        self._button(layout, "Режим выбора на карте", self._select_agent_pick_tool)
        self._button(layout, "Режим добавления на карте", self._select_agent_tool)
        self._button(layout, "Очистить агентов", self._clear_agents)
        layout.addStretch(1)
        return page

    def _events_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._intro("События меняют среду во время расчета. Например, блокируют выход в заданный момент времени."))
        self._button(layout, "Добавить блокировку выхода", self._add_block_exit_event)
        self._button(layout, "Очистить события", self._clear_events)
        layout.addStretch(1)
        return page

    def _simulation_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._intro("Запуск расчета и просмотр истории движения."))
        layout.addWidget(self._simulation_controls())
        layout.addStretch(1)
        return page

    def _simulation_controls(self) -> QWidget:
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        run_group = QGroupBox("Расчет")
        run_layout = QGridLayout(run_group)
        for index, (text, handler) in enumerate(
            [
                ("Запустить", self._run),
                ("Пауза", self._toggle_animation),
                ("Шаг вперед", self._step_forward),
                ("Сброс", self._reset_view),
            ]
        ):
            button = QPushButton(text)
            button.clicked.connect(handler)
            run_layout.addWidget(button, index // 2, index % 2)
        controls_layout.addWidget(run_group)

        basic_group = QGroupBox("Основные параметры")
        basic_form = QFormLayout(basic_group)
        self.dt = double_spin(0.1, 60.0, 1.0, 0.1)
        self.tmax = double_spin(1.0, 36000.0, 300.0, 10.0)
        self.rho = double_spin(0.0, 5.0, 0.5, 0.05)
        self._add_row(basic_form, "Шаг, с", self.dt, "Длительность одного шага симуляции.")
        self._add_row(basic_form, "Предел, с", self.tmax, "Максимальная длительность расчета.")
        self._add_row(basic_form, "Порог затора", self.rho, "Порог Dnorm для пользовательской зоны высокой плотности.")
        controls_layout.addWidget(basic_group)

        advanced = QGroupBox("Экспертные веса маршрута")
        advanced.setCheckable(True)
        advanced.setChecked(False)
        advanced_form = QFormLayout(advanced)
        self.alpha = double_spin(0.0, 1000.0, 10.0)
        self.beta = double_spin(0.0, 1000.0, 5.0)
        self.gamma = double_spin(0.0, 1000.0, 20.0)
        self._add_row(advanced_form, "Дым", self.alpha, "Насколько сильно дым повышает стоимость клетки.")
        self._add_row(advanced_form, "Плотность", self.beta, "Насколько сильно Dnorm влияет на выбор маршрута.")
        self._add_row(advanced_form, "Опасность", self.gamma, "Насколько сильно опасные зоны повышают стоимость клетки.")
        controls_layout.addWidget(advanced)

        self.history_slider = QSlider(Qt.Orientation.Horizontal)
        self.history_slider.valueChanged.connect(self._history_changed)
        controls_layout.addWidget(QLabel("История"))
        controls_layout.addWidget(self.history_slider)
        return controls

    def _reports_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(self._intro("Отчеты формируются по последнему завершенному расчету. Таблица результатов находится снизу."))
        self._button(layout, "Сформировать DOCX", self._save_docx)
        self._button(layout, "Сформировать CSV", self._save_csv)
        self._button(layout, "Показать результаты", lambda: self.bottom_tabs.setCurrentWidget(self.result_table))
        self._button(layout, "Показать журнал", lambda: self.bottom_tabs.setCurrentWidget(self.log))
        layout.addStretch(1)
        return page

    def _table(self, headers: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        return table

    def _intro(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #475569; padding: 4px 0 10px 0;")
        return label

    def _set_tip(self, widget: QWidget, text: str) -> None:
        widget.setToolTip(text)
        widget.setStatusTip(text)

    def _add_row(self, form: QFormLayout, label_text: str, widget: QWidget, tooltip: str) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)
        label = QLabel(label_text)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        help_button = QLabel("i")
        help_button.setFixedSize(22, 22)
        help_button.setAlignment(Qt.AlignmentFlag.AlignCenter)
        help_button.setToolTip(tooltip)
        help_button.setStatusTip(tooltip)
        help_button.setCursor(Qt.CursorShape.PointingHandCursor)
        help_button.setStyleSheet(
            """
            QLabel {
                border: 1px solid #94a3b8;
                border-radius: 11px;
                font-weight: 700;
                font-style: italic;
                padding: 0;
                background: #f8fafc;
                color: #0f172a;
            }
            """
        )
        row_layout.addWidget(label)
        row_layout.addWidget(help_button)
        label.setToolTip(tooltip)
        widget.setToolTip(tooltip)
        widget.setStatusTip(tooltip)
        form.addRow(row, widget)

    def _button(self, layout: QVBoxLayout, text: str, handler) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(handler)
        layout.addWidget(button)
        return button

    def _select_agent_tool(self) -> None:
        self.tool.setCurrentText("Агент")
        self._show_stage("agents_page")

    def _select_agent_pick_tool(self) -> None:
        self.tool.setCurrentText("Выбор агента")
        self._show_stage("agents_page")

    def _new_model(self) -> None:
        try:
            building = BuildingModel(
                id=None,
                name=self.model_name.text(),
                width=self.model_width.value(),
                height=self.model_height.value(),
                cell_size=self.model_cell_size.value(),
            )
            self.scenario = EvacuationScenario(id=None, name=building.name, building_model=building)
            self._clear_run_state()
            self.grid.set_scenario(self.scenario)
            self._refresh_object_lists()
            self._log("Создана новая модель. Добавьте выходы и агентов перед запуском.")
        except ValueError as exc:
            self._error(str(exc))

    def _cell_clicked(self, x: int, y: int) -> None:
        try:
            mode = self.tool.currentText()
            building = self.scenario.building_model
            if mode == "Свободная клетка":
                building.set_cell_state(x, y, CellType.FREE)
            elif mode == "Стена":
                building.set_cell_state(x, y, CellType.WALL)
                self._remove_agents_at({(x, y)})
            elif mode == "Препятствие":
                obstacle = Obstacle(id=len(building.obstacles) + 1, type="препятствие", cells={(x, y)})
                building.add_obstacle(obstacle)
                self.scenario.obstacles = building.obstacles
                self._remove_agents_at({(x, y)})
            elif mode == "Выход":
                exit_obj = Exit(
                    id=len(self.scenario.exits) + 1,
                    cells={(x, y)},
                    width=self.exit_width.value(),
                    capacity=self.exit_capacity.value(),
                )
                building.add_exit(exit_obj)
                self.scenario.exits = building.exits
            elif mode == "Опасная зона":
                cell = building.get_cell(x, y)
                cell.cell_type = CellType.DANGER
                cell.danger_level = 1.0
            elif mode == "Агент":
                self._add_agent_at(x, y)
                self._log(f"Добавлен агент в клетку ({x}, {y}).")
            elif mode == "Выбор агента":
                self._select_agent_at(x, y)
                self._refresh_object_lists()
                return
            self._clear_run_state(keep_log=True)
            self.grid.update()
            self._refresh_object_lists()
        except ValueError as exc:
            self._error(str(exc))

    def _add_agent_at(self, x: int, y: int) -> None:
        coord = (x, y)
        cell = self.scenario.building_model.get_cell(x, y)
        if not cell.is_static_passable:
            raise ValueError("Агент не может быть размещен в стене или препятствии")
        if any(agent.current_cell == coord for agent in self.scenario.agents):
            raise ValueError("Клетка уже занята")
        next_id = max([agent.id for agent in self.scenario.agents], default=0) + 1
        self.scenario.agents.append(
            Agent(
                id=next_id,
                current_cell=coord,
                base_speed=self.agent_speed.value(),
                mobility_group=MobilityGroup[self.agent_group.currentText()],
                mobility_level=MobilityLevel.HIGH,
                clothes_type=ClothesType[self.agent_clothes.currentText()],
            )
        )

    def _find_agent(self, agent_id: int) -> Agent | None:
        return next((agent for agent in self.scenario.agents if agent.id == agent_id), None)

    def _select_agent_at(self, x: int, y: int) -> None:
        agent = next((item for item in self.scenario.agents if item.current_cell == (x, y)), None)
        if agent is None:
            raise ValueError("В выбранной клетке нет агента")
        self.edit_agent_id.setValue(agent.id)
        self._load_agent_to_editor()
        self._show_stage("agents_page")
        self.bottom_tabs.setCurrentWidget(self.agent_table)
        self._log(f"Выбран агент {agent.id}.")

    def _load_agent_to_editor(self) -> None:
        if not hasattr(self, "edit_agent_id"):
            return
        agent = self._find_agent(self.edit_agent_id.value())
        if agent is None:
            return
        self.edit_agent_group.setCurrentText(agent.mobility_group.name)
        self.edit_agent_clothes.setCurrentText(agent.clothes_type.name)
        self.edit_agent_speed.setValue(agent.base_speed)

    def _apply_agent_changes(self) -> None:
        agent = self._find_agent(self.edit_agent_id.value())
        if agent is None:
            self._error("Агент с выбранным ID не найден")
            return
        agent.mobility_group = MobilityGroup[self.edit_agent_group.currentText()]
        agent.clothes_type = ClothesType[self.edit_agent_clothes.currentText()]
        agent.base_speed = self.edit_agent_speed.value()
        agent.recalculate_effective_area()
        self._clear_run_state(keep_log=True)
        self.grid.update()
        self._refresh_object_lists()
        self._log(f"Параметры агента {agent.id} обновлены.")

    def _remove_agents_at(self, cells: set[tuple[int, int]]) -> None:
        self.scenario.agents = [agent for agent in self.scenario.agents if agent.current_cell not in cells]

    def _clear_agents(self) -> None:
        self.scenario.agents.clear()
        self._clear_run_state()
        self.grid.update()
        self._refresh_object_lists()
        self._log("Агенты удалены.")

    def _clear_events(self) -> None:
        self.scenario.events.clear()
        self._clear_run_state()
        self._refresh_object_lists()
        self._log("События удалены.")

    def _apply_parameters(self) -> None:
        self.scenario.simulation_parameters = SimulationParameters(
            time_step=self.dt.value(),
            max_time=self.tmax.value(),
            alpha=self.alpha.value(),
            beta=self.beta.value(),
            gamma=self.gamma.value(),
            rho_crit=self.rho.value(),
        )

    def _run(self) -> None:
        self._apply_parameters()
        try:
            self.run_scenario = deepcopy(self.scenario)
            if self.run_scenario.id is None:
                self.scenario_repository.save(self.run_scenario)
            engine = SimulationEngine(self.run_scenario)
            self.result = engine.run()
            result_id = self.result_repository.save(self.result)
            self.grid.scenario = self.run_scenario
            self.grid.set_result(self.result)
            self.history_slider.setMaximum(max(0, len(self.result.history) - 1))
            self.history_slider.setValue(0)
            self._fill_results_table()
            self._refresh_object_lists(use_run_scenario=True)
            self._log(self.report_generator.build_text(self.run_scenario, self.result) + f"\n\nРезультат сохранен в SQLite, id={result_id}.")
            self.bottom_tabs.setCurrentWidget(self.result_table)
        except (SimulationError, ValueError, KeyError) as exc:
            self._error(str(exc))

    def _fill_results_table(self) -> None:
        if not self.result or not self.run_scenario:
            self.result_table.setRowCount(0)
            return
        self.result_table.setRowCount(len(self.run_scenario.agents))
        for row, agent in enumerate(sorted(self.run_scenario.agents, key=lambda item: item.id)):
            values = [
                agent.id,
                agent.mobility_group.value,
                agent.state.value,
                self.result.agent_evacuation_times.get(agent.id, ""),
                len(self.result.trajectories.get(agent.id, [])),
                agent.reason_if_not_evacuated,
            ]
            for col, value in enumerate(values):
                self.result_table.setItem(row, col, QTableWidgetItem(str(value)))
        self.result_table.resizeColumnsToContents()

    def _refresh_object_lists(self, use_run_scenario: bool = False) -> None:
        scenario = self.run_scenario if use_run_scenario and self.run_scenario else self.scenario
        self.agent_table.setRowCount(len(scenario.agents))
        for row, agent in enumerate(sorted(scenario.agents, key=lambda item: item.id)):
            values = [agent.id, agent.current_cell[0], agent.current_cell[1], agent.mobility_group.value, agent.clothes_type.value, agent.base_speed]
            for col, value in enumerate(values):
                self.agent_table.setItem(row, col, QTableWidgetItem(str(value)))
        self.agent_table.resizeColumnsToContents()
        if hasattr(self, "edit_agent_id"):
            if scenario.agents:
                ids = [agent.id for agent in scenario.agents]
                current = self.edit_agent_id.value()
                self.edit_agent_id.setRange(min(ids), max(ids))
                if current not in ids:
                    self.edit_agent_id.setValue(ids[0])
                self._load_agent_to_editor()
                self.edit_agent_id.setEnabled(True)
            else:
                self.edit_agent_id.setRange(1, 1)
                self.edit_agent_id.setEnabled(False)

        self.events_table.setRowCount(len(scenario.events))
        for row, event in enumerate(sorted(scenario.events, key=lambda item: item.id)):
            values = [event.id, event.type.value, event.time, event.params]
            for col, value in enumerate(values):
                self.events_table.setItem(row, col, QTableWidgetItem(str(value)))
        self.events_table.resizeColumnsToContents()
        self._refresh_dashboard(scenario)

    def _refresh_dashboard(self, scenario: EvacuationScenario | None = None) -> None:
        if not hasattr(self, "stat_agents"):
            return
        scenario = scenario or self.scenario
        building = scenario.building_model
        self.stat_agents.setText(str(len(scenario.agents)))
        self.stat_exits.setText(str(len(scenario.exits)))
        self.stat_events.setText(str(len(scenario.events)))
        self.stat_cell.setText(f"{building.cell_size:.2f} м")
        self.map_meta.setText(f"2D-редактор · шаг {building.cell_size:.2f} м")
        self.legend_label.setText(self._legend_html(scenario))

        checks = [
            ("Модель загружена", bool(building.grid.size)),
            ("Присутствуют выходы", bool(scenario.exits)),
            ("Добавлены агенты", bool(scenario.agents)),
            ("Отчёт готов к формированию", self.result is not None),
        ]
        self.model_status.setText(
            "<br>".join(
                f'<span style="color: {"#16a34a" if ok else "#94a3b8"};">●</span> {text}'
                for text, ok in checks
            )
        )

    def _legend_html(self, scenario: EvacuationScenario) -> str:
        colors = {
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
        groups = sorted({agent.mobility_group for agent in scenario.agents}, key=lambda item: item.name)
        parts = [
            "<b>Условные обозначения:</b>",
            '<span style="color:#1f2937;">■</span> стена',
            '<span style="color:#6b7280;">■</span> препятствие',
            '<span style="color:#16a34a;">■</span> выход',
            '<span style="color:#fb923c;">▨</span> опасная зона (проходимая)',
            '<span style="color:#f97316;">■</span> затор',
            '<span style="color:#dc2626;">■</span> Dnorm',
        ]
        parts.extend(f'<span style="color:{colors[group]};">●</span> агент {group.value}' for group in groups)
        return " &nbsp; ".join(parts)

    def _history_changed(self, value: int) -> None:
        if not self.result:
            return
        try:
            self.grid.set_history_step(value)
        except ValueError as exc:
            self._error(str(exc))

    def _toggle_animation(self) -> None:
        if not self.result:
            self._error("Результаты моделирования отсутствуют")
            return
        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start(180)

    def _step_forward(self) -> None:
        self.history_slider.setValue(min(self.history_slider.value() + 1, self.history_slider.maximum()))

    def _next_animation_step(self) -> None:
        if self.history_slider.value() >= self.history_slider.maximum():
            self.timer.stop()
            return
        self._step_forward()

    def _reset_view(self) -> None:
        self.timer.stop()
        self.history_slider.setValue(0)
        self.grid.set_scenario(self.scenario)
        self.result = None
        self.run_scenario = None
        self.result_table.setRowCount(0)
        self._refresh_object_lists()

    def _add_block_exit_event(self) -> None:
        default_exit_id = self.scenario.exits[0].id if self.scenario.exits else 1
        dialog = BlockExitDialog(default_exit_id)
        if dialog.exec():
            self.scenario.events.append(
                EnvironmentEvent(
                    id=len(self.scenario.events) + 1,
                    type=EventType.BLOCK_EXIT,
                    time=float(dialog.time.value()),
                    params={"exit_id": dialog.exit_id.value()},
                )
            )
            self._clear_run_state(keep_log=True)
            self._refresh_object_lists()
            self._log("Добавлено событие блокировки выхода.")

    def _refresh_scenario_list(self) -> None:
        self.scenario_list.clear()
        paths = sorted((self.project_root / "examples").glob("*.json"))
        paths += sorted((self.project_root / "data").glob("*.json")) if (self.project_root / "data").exists() else []
        for path in paths:
            self.scenario_list.addItem(str(path.relative_to(self.project_root)))

    def _load_selected_scenario(self) -> None:
        scenario_path = self.scenario_list.currentText()
        if not scenario_path:
            self._error("Сценарий не выбран")
            return
        self._load_scenario_path(self.project_root / scenario_path)

    def _save_scenario_to_database(self) -> None:
        try:
            scenario_id = self.scenario_repository.save(self.scenario)
            self._log(f"Сценарий сохранен в SQLite: {self.database.path}, id={scenario_id}.")
        except Exception as exc:
            self._error(str(exc))

    def _load_latest_scenario_from_database(self) -> None:
        try:
            rows = self.scenario_repository.list()
            if not rows:
                self._error("В базе данных нет сохраненных сценариев")
                return
            scenario_id = rows[0][0]
            self.scenario = self.scenario_repository.get(scenario_id)
            self._clear_run_state()
            self._load_scenario_into_controls()
            self.grid.set_scenario(self.scenario)
            self._refresh_object_lists()
            self._log(f"Сценарий загружен из SQLite: {self.database.path}, id={scenario_id}.")
        except Exception as exc:
            self._error(str(exc))

    def _save_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить сценарий",
            str(self.project_root / "examples" / "scenario.json"),
            "JSON (*.json)",
        )
        if path:
            export_scenario_to_json(self.scenario, path)
            self._refresh_scenario_list()
            self._log(f"Сценарий сохранен: {path}")

    def _load_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить сценарий", str(self.project_root / "examples"), "JSON (*.json)")
        if path:
            self._load_scenario_path(Path(path))

    def _load_scenario_path(self, path: Path) -> None:
        try:
            self.scenario = import_scenario_from_json(path)
            self._clear_run_state()
            self._load_scenario_into_controls()
            self.grid.set_scenario(self.scenario)
            self._refresh_object_lists()
            self._log(f"Сценарий загружен: {path}")
        except Exception as exc:
            self._error(str(exc))

    def _save_docx(self) -> None:
        if not self.result or not self.run_scenario:
            self._error("Результаты моделирования отсутствуют")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить DOCX", str(self.project_root / "reports" / "report.docx"), "DOCX (*.docx)")
        if path:
            self.report_generator.save_docx(self.run_scenario, self.result, path)
            if self.result.id is not None:
                self.result_repository.save_report_path(self.result.id, path, "DOCX")
            self._log(f"Отчет сохранен: {path}")

    def _save_csv(self) -> None:
        if not self.result or not self.run_scenario:
            self._error("Результаты моделирования отсутствуют")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", str(self.project_root / "reports" / "report.csv"), "CSV (*.csv)")
        if path:
            export_agents_csv(self.run_scenario, self.result, path)
            if self.result.id is not None:
                self.result_repository.save_report_path(self.result.id, path, "CSV")
            self._log(f"CSV сохранен: {path}")

    def _open_3d_view(self) -> None:
        try:
            scenario = self.run_scenario if self.run_scenario else self.scenario
            self.view3d_window = Visualization3DWindow(scenario, self.result)
            self.view3d_window.show()
        except RuntimeError as exc:
            self._error(str(exc))

    def _load_scenario_into_controls(self) -> None:
        building = self.scenario.building_model
        params = self.scenario.simulation_parameters
        self.model_name.setText(building.name)
        self.model_width.setValue(building.width)
        self.model_height.setValue(building.height)
        self.model_cell_size.setValue(building.cell_size)
        self.dt.setValue(params.time_step)
        self.tmax.setValue(params.max_time)
        self.alpha.setValue(params.alpha)
        self.beta.setValue(params.beta)
        self.gamma.setValue(params.gamma)
        self.rho.setValue(params.rho_crit)

    def _clear_run_state(self, keep_log: bool = False) -> None:
        self.timer.stop()
        self.result = None
        self.run_scenario = None
        self.history_slider.setMaximum(0)
        self.history_slider.setValue(0)
        self.result_table.setRowCount(0)
        self.grid.set_scenario(self.scenario)
        if not keep_log:
            self.log.clear()

    def _demo_scenario(self) -> EvacuationScenario:
        building = BuildingModel(id=None, name="Учебная аудитория 312", width=24.0, height=14.0, cell_size=0.5)
        for x in range(building.cols):
            building.set_cell_state(x, 0, CellType.WALL)
            building.set_cell_state(x, building.rows - 1, CellType.WALL)
        for y in range(building.rows):
            building.set_cell_state(0, y, CellType.WALL)
            building.set_cell_state(building.cols - 1, y, CellType.WALL)

        main_exit_cells = {(building.cols - 1, building.rows // 2 - 1), (building.cols - 1, building.rows // 2)}
        reserve_exit_cells = {(building.cols // 2, building.rows - 1), (building.cols // 2 + 1, building.rows - 1)}
        building.add_exit(Exit(id=1, cells=main_exit_cells, width=1.2, capacity=1, status=ExitStatus.OPEN))
        building.add_exit(Exit(id=2, cells=reserve_exit_cells, width=1.0, capacity=1, status=ExitStatus.OPEN))

        def add_obstacle(kind: str, cells: set[tuple[int, int]]) -> None:
            cells = {cell for cell in cells if building.in_bounds(*cell)}
            if cells:
                building.add_obstacle(Obstacle(id=len(building.obstacles) + 1, type=kind, cells=cells))

        add_obstacle("стол преподавателя", {(5, 5), (6, 5), (7, 5), (8, 5)})
        add_obstacle("демонстрационный стол", {(18, 5), (19, 5), (20, 5), (21, 5)})
        add_obstacle("шкафы", {(2, y) for y in range(18, 25)})
        add_obstacle("шкафы", {(building.cols - 3, y) for y in range(3, 8)})

        for desk_y in (8, 11, 14, 17, 20):
            for desk_x in (6, 12, 18, 28, 34, 40):
                add_obstacle("парта", {(desk_x, desk_y), (desk_x + 1, desk_y), (desk_x + 2, desk_y)})

        for x in range(35, 44):
            for y in range(4, 9):
                cell = building.get_cell(x, y)
                if cell.cell_type == CellType.FREE:
                    cell.cell_type = CellType.DANGER
                    cell.danger_level = 0.45
                    cell.smoke_level = 0.25

        agents: list[Agent] = []
        seat_cells: list[tuple[int, int]] = []
        for seat_y in (9, 12, 15, 18, 21):
            for seat_x in (6, 8, 12, 14, 18, 20, 28, 30, 34, 36, 40, 42):
                if building.get_cell(seat_x, seat_y).is_static_passable:
                    seat_cells.append((seat_x, seat_y))

        for index, cell in enumerate(seat_cells[:36], start=1):
            if index in {9, 22}:
                group = MobilityGroup.M1
                speed = 0.80
            elif index == 31:
                group = MobilityGroup.M2
                speed = 0.65
            else:
                group = MobilityGroup.M0_3
                speed = 1.25
            clothes = ClothesType.WINTER if index % 7 == 0 else ClothesType.SUMMER
            agents.append(Agent(id=index, current_cell=cell, base_speed=speed, mobility_group=group, clothes_type=clothes))
        agents.append(Agent(id=len(agents) + 1, current_cell=(5, 6), base_speed=1.30, mobility_group=MobilityGroup.M0_2))

        smoke_area = {(x, y) for x in range(35, 44) for y in range(4, 9)}
        danger_area = set(smoke_area)
        events = [
            EnvironmentEvent(id=1, type=EventType.CHANGE_SMOKE, time=8.0, area=smoke_area, params={"smoke_level": 0.55}),
            EnvironmentEvent(id=2, type=EventType.ADD_DANGER_ZONE, time=15.0, area=danger_area, params={"danger_level": 0.75}),
            EnvironmentEvent(id=3, type=EventType.BLOCK_EXIT, time=22.0, params={"exit_id": 1}),
        ]
        params = SimulationParameters(
            time_step=1.0,
            max_time=420.0,
            alpha=12.0,
            beta=6.0,
            gamma=25.0,
            rho_crit=0.5,
            random_seed=7,
            evacuation_start_time=0.0,
            route_blocking_time=22.0,
        )
        return EvacuationScenario(
            id=None,
            name="Реалистичная эвакуация из аудитории",
            building_model=building,
            agents=agents,
            events=events,
            simulation_parameters=params,
        )

    def _log(self, text: str) -> None:
        self.log.write(text)

    def _error(self, text: str) -> None:
        self.log.write(text)
        QMessageBox.warning(self, "Ошибка", text)

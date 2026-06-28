from __future__ import annotations

from enum import Enum


class RussianEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class CellType(RussianEnum):
    FREE = "свободная"
    OCCUPIED = "занятая"
    WALL = "стена"
    OBSTACLE = "препятствие"
    EXIT = "выход"
    DANGER = "опасная зона"


class PathType(RussianEnum):
    HORIZONTAL = "горизонтальный"
    DOORWAY = "проём"
    STAIRS_DOWN = "лестница вниз"
    STAIRS_UP = "лестница вверх"
    RAMP = "пандус"


class AgentState(RussianEnum):
    WAITING = "ожидает"
    MOVING = "движется"
    DELAYED = "задержан"
    EVACUATED = "эвакуирован"
    NEEDS_RESCUE = "требуется спасение"


class MobilityGroup(RussianEnum):
    M0 = "М0"
    M0_1 = "М0-1"
    M0_2 = "М0-2"
    M0_3 = "М0-3"
    M0_4 = "М0-4"
    M0_5 = "М0-5"
    M0_6 = "М0-6"
    M0_7 = "М0-7"
    M1 = "М1"
    M2 = "М2"
    M3 = "М3"
    M4 = "М4"
    NM = "НМ"
    NT = "НТ"
    NO = "НО"


class MobilityLevel(RussianEnum):
    HIGH = "высокий"
    MEDIUM = "средний"
    LOW = "низкий"
    LIMITED = "ограниченный"


class ClothesType(RussianEnum):
    SUMMER = "летняя"
    WINTER = "зимняя"


class ExitStatus(RussianEnum):
    OPEN = "открыт"
    CLOSED = "закрыт"
    BLOCKED = "заблокирован"


class EventType(RussianEnum):
    BLOCK_EXIT = "блокировка выхода"
    ADD_OBSTACLE = "появление препятствия"
    ADD_DANGER_ZONE = "появление опасной зоны"
    CHANGE_SMOKE = "изменение задымления"
    CHANGE_PASSABILITY = "изменение проходимости"


class ControlPointPurpose(RussianEnum):
    EVACUATION_TIME = "расчётное время эвакуации"
    BLOCKING_TIME = "время блокирования пути"
    BOTH = "оба назначения"


class SimulationStatus(RussianEnum):
    NOT_STARTED = "не запущено"
    RUNNING = "выполняется"
    FINISHED = "завершено"
    STOPPED = "остановлено"
    ERROR = "ошибка"

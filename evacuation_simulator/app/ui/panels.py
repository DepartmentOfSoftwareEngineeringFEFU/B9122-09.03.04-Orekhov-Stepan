from __future__ import annotations

from PyQt6.QtWidgets import QDoubleSpinBox, QTextEdit


def double_spin(minimum: float, maximum: float, value: float, step: float = 0.5) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.setSingleStep(step)
    spin.setDecimals(3)
    return spin


class LogPanel(QTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setReadOnly(True)

    def write(self, text: str) -> None:
        self.setPlainText(text)

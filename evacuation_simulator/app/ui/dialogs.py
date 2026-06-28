from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QSpinBox


class BlockExitDialog(QDialog):
    def __init__(self, default_exit_id: int = 1, default_time: int = 10) -> None:
        super().__init__()
        self.setWindowTitle("Событие блокировки выхода")
        self.exit_id = QSpinBox()
        self.exit_id.setRange(1, 9999)
        self.exit_id.setValue(default_exit_id)
        self.time = QSpinBox()
        self.time.setRange(0, 36000)
        self.time.setValue(default_time)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QFormLayout(self)
        layout.addRow("ID выхода", self.exit_id)
        layout.addRow("Время, с", self.time)
        layout.addRow(buttons)

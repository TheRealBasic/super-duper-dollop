from __future__ import annotations

from datetime import time

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from where_did_my_time_go.rules import DEFAULT_CATEGORIES
from where_did_my_time_go.settings import SettingsStore


class SettingsWidget(QWidget):
    def __init__(self, settings: SettingsStore) -> None:
        super().__init__()
        self._settings = settings

        self.sampling_interval = QLineEdit()
        self.idle_threshold = QLineEdit()
        self.retention_days = QLineEdit()
        self.close_to_tray = QCheckBox("Close to tray")

        self.focus_start = QTimeEdit()
        self.focus_end = QTimeEdit()
        self.prompts_enabled = QCheckBox("Enable prompts")
        self.category_checks = []

        self.save_button = QPushButton("Save Settings")

        tracking_group = QGroupBox("Tracking")
        tracking_layout = QFormLayout(tracking_group)
        tracking_layout.addRow("Sampling interval (sec)", self.sampling_interval)
        tracking_layout.addRow("Idle threshold (min)", self.idle_threshold)
        tracking_layout.addRow("Retention days (0=keep)", self.retention_days)
        tracking_layout.addRow("", self.close_to_tray)

        focus_group = QGroupBox("Focus Mode")
        focus_layout = QFormLayout(focus_group)
        focus_layout.addRow("Start", self.focus_start)
        focus_layout.addRow("End", self.focus_end)
        focus_layout.addRow("", self.prompts_enabled)

        categories_group = QGroupBox("Distraction Categories")
        categories_layout = QVBoxLayout(categories_group)
        for category in DEFAULT_CATEGORIES:
            if category == "Idle":
                continue
            check = QCheckBox(category)
            self.category_checks.append(check)
            categories_layout.addWidget(check)

        layout = QVBoxLayout(self)
        layout.addWidget(tracking_group)
        layout.addWidget(focus_group)
        layout.addWidget(categories_group)
        layout.addWidget(self.save_button)

        self.save_button.clicked.connect(self.save_settings)
        self.load_settings()

    def load_settings(self) -> None:
        data = self._settings.current
        self.sampling_interval.setText(str(data.sampling_interval_sec))
        self.idle_threshold.setText(str(data.idle_threshold_min))
        self.retention_days.setText(str(data.retention_days))
        self.close_to_tray.setChecked(data.close_to_tray)
        self.focus_start.setTime(data.focus_start)
        self.focus_end.setTime(data.focus_end)
        self.prompts_enabled.setChecked(data.prompts_enabled)
        for check in self.category_checks:
            check.setChecked(check.text() in data.distraction_categories)

    def save_settings(self) -> None:
        self._settings.update(
            sampling_interval_sec=int(self.sampling_interval.text() or "1"),
            idle_threshold_min=int(self.idle_threshold.text() or "3"),
            retention_days=int(self.retention_days.text() or "0"),
            close_to_tray=self.close_to_tray.isChecked(),
            focus_start=self.focus_start.time().toPython(),
            focus_end=self.focus_end.time().toPython(),
            prompts_enabled=self.prompts_enabled.isChecked(),
            distraction_categories=[
                check.text() for check in self.category_checks if check.isChecked()
            ],
        )

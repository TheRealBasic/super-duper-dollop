from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from where_did_my_time_go.dashboard import DashboardWidget
from where_did_my_time_go.reports import ReportsWidget
from where_did_my_time_go.rules_ui import RulesWidget
from where_did_my_time_go.settings import SettingsStore
from where_did_my_time_go.settings_ui import SettingsWidget
from where_did_my_time_go.storage import Database
from where_did_my_time_go.utils import optional_icon


class IntentDialog(QDialog):
    def __init__(self, category: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Quick check")
        self.intent = ""
        label = QLabel("Quick check: what are you here for?")
        intentional = QPushButton("Intentional")
        bored = QPushButton("Bored / autopilot")
        unsure = QPushButton("Not sure")

        layout = QVBoxLayout(self)
        layout.addWidget(label)
        layout.addWidget(intentional)
        layout.addWidget(bored)
        layout.addWidget(unsure)

        intentional.clicked.connect(lambda: self._select("Intentional"))
        bored.clicked.connect(lambda: self._select("Bored / autopilot"))
        unsure.clicked.connect(lambda: self._select("Not sure"))

    def _select(self, value: str) -> None:
        self.intent = value
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, settings: SettingsStore) -> None:
        super().__init__()
        self._settings = settings
        self._db = Database()
        self._db.initialize()
        self._allow_close = False
        self.setWindowTitle("Where Did My Time Go?")
        icon_path = optional_icon("icon.ico")
        if icon_path:
            self.setWindowIcon(QIcon(icon_path))

        self.tabs = QTabWidget()
        self.dashboard = DashboardWidget()
        self.reports = ReportsWidget()
        self.rules = RulesWidget()
        self.settings_widget = SettingsWidget(settings)

        self.tabs.addTab(self.dashboard, "Dashboard")
        self.tabs.addTab(self.reports, "Reports")
        self.tabs.addTab(self.rules, "Rules")
        self.tabs.addTab(self.settings_widget, "Settings")

        self.setCentralWidget(self.tabs)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(5000)
        self.refresh_timer.timeout.connect(self.refresh_views)
        self.refresh_timer.start()

    def refresh_views(self) -> None:
        self.dashboard.refresh()
        self.reports.refresh()
        self.rules.refresh()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._settings.current.close_to_tray and not self._allow_close:
            event.ignore()
            self.hide()
        else:
            super().closeEvent(event)

    def force_quit(self) -> None:
        self._allow_close = True
        self.close()

    def handle_prompt(self, session_id: int, category: str, on_save: callable) -> None:
        dialog = IntentDialog(category, self)
        if dialog.exec() == QDialog.Accepted:
            on_save(session_id, dialog.intent)

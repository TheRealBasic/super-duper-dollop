from __future__ import annotations

from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from where_did_my_time_go.settings import SettingsStore
from where_did_my_time_go.tracker import TrackerController
from where_did_my_time_go.utils import optional_icon


class TrayController:
    def __init__(
        self,
        app,
        main_window,
        tracker: TrackerController,
        settings: SettingsStore,
    ) -> None:
        self._main_window = main_window
        self._tracker = tracker
        self._settings = settings

        icon_path = optional_icon("icon.ico")
        self.tray = QSystemTrayIcon(QIcon(icon_path) if icon_path else QIcon(), app)
        menu = QMenu()
        open_action = QAction("Open")
        pause_action = QAction("Pause Tracking")
        resume_action = QAction("Resume Tracking")
        quit_action = QAction("Quit")

        open_action.triggered.connect(self.show_main)
        pause_action.triggered.connect(self._tracker.pause)
        resume_action.triggered.connect(self._tracker.resume)
        quit_action.triggered.connect(self.quit)

        menu.addAction(open_action)
        menu.addAction(pause_action)
        menu.addAction(resume_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)

        tracker.worker.prompt_needed.connect(self._handle_prompt)

    def show(self) -> None:
        self.tray.show()

    def show_main(self) -> None:
        self._main_window.show()
        self._main_window.activateWindow()

    def _handle_prompt(self, session_id: int, category: str) -> None:
        self._main_window.handle_prompt(session_id, category, self._tracker.worker.set_intent_tag)

    def quit(self) -> None:
        self._tracker.stop()
        self.tray.hide()
        self._main_window.force_quit()

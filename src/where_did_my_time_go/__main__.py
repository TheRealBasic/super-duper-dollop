import sys

from PySide6.QtWidgets import QApplication

from where_did_my_time_go.app import MainWindow
from where_did_my_time_go.settings import SettingsStore
from where_did_my_time_go.tracker import TrackerController
from where_did_my_time_go.tray import TrayController


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Where Did My Time Go?")

    settings = SettingsStore()
    settings.load()

    main_window = MainWindow(settings)
    tracker = TrackerController(settings)
    tray = TrayController(app, main_window, tracker, settings)

    tracker.worker.session_updated.connect(main_window.refresh_views)

    tracker.start()
    main_window.show()
    tray.show()

    exit_code = app.exec()
    tracker.stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

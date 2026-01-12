from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import QObject, QThread, Signal

from where_did_my_time_go.idle import get_idle_status
from where_did_my_time_go.rules import AppContext, Rule, apply_rules
from where_did_my_time_go.settings import SettingsStore
from where_did_my_time_go.storage import Database, SessionRecord, utc_now_iso
from where_did_my_time_go.win_api import ForegroundApp, get_foreground_app, get_idle_seconds


@dataclass
class ActiveSession:
    session_id: int
    start_ts: str
    process_name: str
    window_title: str
    exe_path: str
    category: str


class TrackerWorker(QObject):
    session_updated = Signal()
    prompt_needed = Signal(int, str)
    tracking_status = Signal(str)

    def __init__(self, settings: SettingsStore) -> None:
        super().__init__()
        self._settings = settings
        self._db = Database()
        self._db.initialize()
        self._db.ensure_default_rules()
        self._running = threading.Event()
        self._running.set()
        self._paused = threading.Event()
        self._paused.clear()
        self._active_session: ActiveSession | None = None
        self._last_tick = time.monotonic()

    def stop(self) -> None:
        self._running.clear()

    def pause(self) -> None:
        self._paused.set()
        self._close_active_session()
        self.tracking_status.emit("Paused")

    def resume(self) -> None:
        self._paused.clear()
        self.tracking_status.emit("Running")

    def run(self) -> None:
        self.tracking_status.emit("Running")
        while self._running.is_set():
            if self._paused.is_set():
                time.sleep(0.5)
                continue
            interval = max(1, self._settings.current.sampling_interval_sec)
            now = time.monotonic()
            gap = now - self._last_tick
            self._last_tick = now

            idle_threshold = self._settings.current.idle_threshold_min * 60
            idle_status = get_idle_status(get_idle_seconds, idle_threshold)
            if idle_status.is_idle:
                self._handle_idle_gap(int(gap))
            else:
                if gap > interval * 3:
                    self._close_session_with_gap(int(gap))
                self._track_foreground()

            time.sleep(interval)

    def _handle_idle_gap(self, gap: int) -> None:
        self._close_active_session()
        if gap > 0:
            self._create_idle_session(gap)

    def _close_session_with_gap(self, gap: int) -> None:
        self._close_active_session()
        self._create_idle_session(gap)

    def _create_idle_session(self, duration: int) -> None:
        end = datetime.now(timezone.utc)
        start = end - timedelta(seconds=duration)
        start_ts = start.isoformat()
        end_ts = end.isoformat()
        record = SessionRecord(
            start_ts=start_ts,
            end_ts=end_ts,
            duration_sec=duration,
            process_name="Idle",
            exe_path="",
            window_title="",
            category="Idle",
            intent_tag=None,
        )
        self._db.add_session(record)
        self.session_updated.emit()

    def _track_foreground(self) -> None:
        app = get_foreground_app()
        app_context = AppContext(app.process_name, app.window_title)
        rules = [Rule(**dict(row)) for row in self._db.list_rules()]
        category = apply_rules(rules, app_context)

        if self._active_session is None:
            self._start_session(app, category)
            return
        if (
            app.process_name != self._active_session.process_name
            or app.window_title != self._active_session.window_title
        ):
            self._close_active_session()
            self._start_session(app, category)
        else:
            self._refresh_active_session()

    def _refresh_active_session(self) -> None:
        if not self._active_session:
            return
        end_ts = utc_now_iso()
        start_dt = datetime.fromisoformat(self._active_session.start_ts)
        end_dt = datetime.fromisoformat(end_ts)
        duration = max(0, int((end_dt - start_dt).total_seconds()))
        self._db.update_session_end(self._active_session.session_id, end_ts, duration)
        self.session_updated.emit()

    def _start_session(self, app: ForegroundApp, category: str) -> None:
        start_ts = utc_now_iso()
        record = SessionRecord(
            start_ts=start_ts,
            end_ts=start_ts,
            duration_sec=0,
            process_name=app.process_name or "Unknown",
            exe_path=app.exe_path or "",
            window_title=app.window_title or "",
            category=category,
            intent_tag=None,
        )
        session_id = self._db.add_session(record)
        self._active_session = ActiveSession(
            session_id=session_id,
            start_ts=start_ts,
            process_name=record.process_name,
            window_title=record.window_title,
            exe_path=record.exe_path,
            category=record.category,
        )
        self.session_updated.emit()
        if self._should_prompt(category):
            self.prompt_needed.emit(session_id, category)

    def _close_active_session(self) -> None:
        if not self._active_session:
            return
        end_ts = utc_now_iso()
        start_dt = datetime.fromisoformat(self._active_session.start_ts)
        end_dt = datetime.fromisoformat(end_ts)
        duration = max(0, int((end_dt - start_dt).total_seconds()))
        self._db.update_session_end(self._active_session.session_id, end_ts, duration)
        self._active_session = None
        self.session_updated.emit()

    def _should_prompt(self, category: str) -> bool:
        settings = self._settings.current
        if not settings.prompts_enabled:
            return False
        if category not in settings.distraction_categories:
            return False
        now = datetime.now().time()
        if settings.focus_start <= settings.focus_end:
            return settings.focus_start <= now <= settings.focus_end
        return now >= settings.focus_start or now <= settings.focus_end

    def set_intent_tag(self, session_id: int, intent: str) -> None:
        self._db.update_session_intent(session_id, intent)


class TrackerController:
    def __init__(self, settings: SettingsStore) -> None:
        self._thread = QThread()
        self._worker = TrackerWorker(settings)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)

    @property
    def worker(self) -> TrackerWorker:
        return self._worker

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._worker.stop()
        self._thread.quit()
        self._thread.wait()

    def pause(self) -> None:
        self._worker.pause()

    def resume(self) -> None:
        self._worker.resume()

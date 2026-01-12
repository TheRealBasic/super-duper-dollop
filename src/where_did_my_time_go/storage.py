from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

APP_DIR = Path.home() / "AppData" / "Roaming" / "WhereDidMyTimeGo"
DB_PATH = APP_DIR / "data.db"
SCHEMA_VERSION = 1


@dataclass
class SessionRecord:
    start_ts: str
    end_ts: str
    duration_sec: int
    process_name: str
    exe_path: str
    window_title: str
    category: str
    intent_tag: str | None


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        path = db_path or DB_PATH
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    def initialize(self) -> None:
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_ts TEXT NOT NULL,
                end_ts TEXT NOT NULL,
                duration_sec INTEGER NOT NULL,
                process_name TEXT NOT NULL,
                exe_path TEXT NOT NULL,
                window_title TEXT NOT NULL,
                category TEXT NOT NULL,
                intent_tag TEXT
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                enabled INTEGER NOT NULL,
                match_type TEXT NOT NULL,
                process_pattern TEXT,
                title_pattern TEXT,
                category TEXT NOT NULL,
                priority INTEGER NOT NULL
            )
            """
        )
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        current_version = self.get_meta("schema_version")
        if current_version is None:
            self.set_meta("schema_version", str(SCHEMA_VERSION))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    def get_meta(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self._conn.commit()

    def get_setting(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def add_session(self, record: SessionRecord) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO sessions (
                start_ts, end_ts, duration_sec, process_name, exe_path,
                window_title, category, intent_tag
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.start_ts,
                record.end_ts,
                record.duration_sec,
                record.process_name,
                record.exe_path,
                record.window_title,
                record.category,
                record.intent_tag,
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def update_session_intent(self, session_id: int, intent_tag: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET intent_tag=? WHERE session_id=?",
            (intent_tag, session_id),
        )
        self._conn.commit()

    def update_session_end(self, session_id: int, end_ts: str, duration_sec: int) -> None:
        self._conn.execute(
            "UPDATE sessions SET end_ts=?, duration_sec=? WHERE session_id=?",
            (end_ts, duration_sec, session_id),
        )
        self._conn.commit()

    def add_rule(
        self,
        enabled: bool,
        match_type: str,
        process_pattern: str | None,
        title_pattern: str | None,
        category: str,
        priority: int,
    ) -> int:
        cursor = self._conn.execute(
            """
            INSERT INTO rules (enabled, match_type, process_pattern, title_pattern, category, priority)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(enabled), match_type, process_pattern, title_pattern, category, priority),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def update_rule(
        self,
        rule_id: int,
        enabled: bool,
        match_type: str,
        process_pattern: str | None,
        title_pattern: str | None,
        category: str,
        priority: int,
    ) -> None:
        self._conn.execute(
            """
            UPDATE rules
            SET enabled=?, match_type=?, process_pattern=?, title_pattern=?, category=?, priority=?
            WHERE rule_id=?
            """,
            (int(enabled), match_type, process_pattern, title_pattern, category, priority, rule_id),
        )
        self._conn.commit()

    def delete_rule(self, rule_id: int) -> None:
        self._conn.execute("DELETE FROM rules WHERE rule_id=?", (rule_id,))
        self._conn.commit()

    def list_rules(self) -> list[sqlite3.Row]:
        rows = self._conn.execute(
            "SELECT * FROM rules ORDER BY priority ASC, rule_id ASC"
        ).fetchall()
        return list(rows)

    def fetch_sessions(self, start_ts: str, end_ts: str) -> list[sqlite3.Row]:
        rows = self._conn.execute(
            """
            SELECT * FROM sessions
            WHERE start_ts >= ? AND end_ts <= ?
            ORDER BY start_ts ASC
            """,
            (start_ts, end_ts),
        ).fetchall()
        return list(rows)

    def summarize_today(self, day_start: str, day_end: str) -> list[sqlite3.Row]:
        rows = self._conn.execute(
            """
            SELECT category, SUM(duration_sec) AS total
            FROM sessions
            WHERE start_ts >= ? AND end_ts <= ?
            GROUP BY category
            """,
            (day_start, day_end),
        ).fetchall()
        return list(rows)

    def top_apps(self, start_ts: str, end_ts: str, limit: int = 10) -> list[sqlite3.Row]:
        rows = self._conn.execute(
            """
            SELECT process_name, SUM(duration_sec) AS total
            FROM sessions
            WHERE start_ts >= ? AND end_ts <= ?
            GROUP BY process_name
            ORDER BY total DESC
            LIMIT ?
            """,
            (start_ts, end_ts, limit),
        ).fetchall()
        return list(rows)

    def total_idle(self, start_ts: str, end_ts: str) -> int:
        row = self._conn.execute(
            """
            SELECT COALESCE(SUM(duration_sec), 0) AS total
            FROM sessions
            WHERE start_ts >= ? AND end_ts <= ? AND category = 'Idle'
            """,
            (start_ts, end_ts),
        ).fetchone()
        return int(row["total"]) if row else 0

    def total_active(self, start_ts: str, end_ts: str) -> int:
        row = self._conn.execute(
            """
            SELECT COALESCE(SUM(duration_sec), 0) AS total
            FROM sessions
            WHERE start_ts >= ? AND end_ts <= ? AND category != 'Idle'
            """,
            (start_ts, end_ts),
        ).fetchone()
        return int(row["total"]) if row else 0

    def cleanup_retention(self, days: int) -> int:
        if days <= 0:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_ts = cutoff.isoformat()
        cursor = self._conn.execute(
            "DELETE FROM sessions WHERE end_ts < ?",
            (cutoff_ts,),
        )
        self._conn.commit()
        return cursor.rowcount

    def ensure_default_rules(self) -> None:
        if self.list_rules():
            return
        default_rules = [
            (True, "substring", "chrome.exe", "YouTube", "Video", 1),
            (True, "substring", "spotify.exe", None, "Social", 2),
        ]
        for enabled, match_type, proc, title, category, priority in default_rules:
            self.add_rule(enabled, match_type, proc, title, category, priority)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def iso_to_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def date_range_for_day(day: datetime) -> tuple[str, str]:
    start = day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()


def date_range_for_days(days: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)
    return start.isoformat(), now.isoformat()


def to_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

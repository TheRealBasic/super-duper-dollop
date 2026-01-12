from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import time
from typing import Iterable

from where_did_my_time_go.storage import Database


DEFAULT_SETTINGS = {
    "sampling_interval_sec": 1,
    "idle_threshold_min": 3,
    "retention_days": 0,
    "close_to_tray": True,
    "focus_start": "09:00",
    "focus_end": "17:00",
    "prompts_enabled": True,
    "distraction_categories": json.dumps(["Social", "Video", "Gaming"]),
}


@dataclass
class Settings:
    sampling_interval_sec: int
    idle_threshold_min: int
    retention_days: int
    close_to_tray: bool
    focus_start: time
    focus_end: time
    prompts_enabled: bool
    distraction_categories: list[str]


class SettingsStore:
    def __init__(self) -> None:
        self._db = Database()
        self._settings = Settings(
            sampling_interval_sec=1,
            idle_threshold_min=3,
            retention_days=0,
            close_to_tray=True,
            focus_start=time(9, 0),
            focus_end=time(17, 0),
            prompts_enabled=True,
            distraction_categories=["Social", "Video", "Gaming"],
        )

    @property
    def current(self) -> Settings:
        return self._settings

    def load(self) -> None:
        self._db.initialize()
        for key, value in DEFAULT_SETTINGS.items():
            stored = self._db.get_setting(key)
            if stored is None:
                self._db.set_setting(key, str(value))
                stored = str(value)
            self._apply_setting(key, stored)
        self._db.cleanup_retention(self._settings.retention_days)

    def save(self) -> None:
        data = {
            "sampling_interval_sec": self._settings.sampling_interval_sec,
            "idle_threshold_min": self._settings.idle_threshold_min,
            "retention_days": self._settings.retention_days,
            "close_to_tray": int(self._settings.close_to_tray),
            "focus_start": self._settings.focus_start.strftime("%H:%M"),
            "focus_end": self._settings.focus_end.strftime("%H:%M"),
            "prompts_enabled": int(self._settings.prompts_enabled),
            "distraction_categories": json.dumps(self._settings.distraction_categories),
        }
        for key, value in data.items():
            self._db.set_setting(key, str(value))

    def update(
        self,
        sampling_interval_sec: int,
        idle_threshold_min: int,
        retention_days: int,
        close_to_tray: bool,
        focus_start: time,
        focus_end: time,
        prompts_enabled: bool,
        distraction_categories: Iterable[str],
    ) -> None:
        self._settings = Settings(
            sampling_interval_sec=sampling_interval_sec,
            idle_threshold_min=idle_threshold_min,
            retention_days=retention_days,
            close_to_tray=close_to_tray,
            focus_start=focus_start,
            focus_end=focus_end,
            prompts_enabled=prompts_enabled,
            distraction_categories=list(distraction_categories),
        )
        self.save()

    def _parse_bool(self, value: str) -> bool:
        normalized = value.strip().lower()
        if normalized in {"true", "false"}:
            return normalized == "true"
        return bool(int(value))

    def _apply_setting(self, key: str, value: str) -> None:
        if key == "sampling_interval_sec":
            self._settings.sampling_interval_sec = int(value)
        elif key == "idle_threshold_min":
            self._settings.idle_threshold_min = int(value)
        elif key == "retention_days":
            self._settings.retention_days = int(value)
        elif key == "close_to_tray":
            self._settings.close_to_tray = self._parse_bool(value)
        elif key == "focus_start":
            hour, minute = [int(part) for part in value.split(":")]
            self._settings.focus_start = time(hour, minute)
        elif key == "focus_end":
            hour, minute = [int(part) for part in value.split(":")]
            self._settings.focus_end = time(hour, minute)
        elif key == "prompts_enabled":
            self._settings.prompts_enabled = self._parse_bool(value)
        elif key == "distraction_categories":
            self._settings.distraction_categories = json.loads(value)

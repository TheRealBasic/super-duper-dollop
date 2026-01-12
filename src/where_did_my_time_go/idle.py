from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class IdleStatus:
    idle_seconds: int
    is_idle: bool


def get_idle_status(idle_func: Callable[[], int], threshold_seconds: int) -> IdleStatus:
    idle_seconds = max(0, int(idle_func()))
    return IdleStatus(idle_seconds=idle_seconds, is_idle=idle_seconds >= threshold_seconds)


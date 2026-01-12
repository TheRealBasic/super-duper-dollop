from __future__ import annotations

from pathlib import Path
import sys


def asset_path(name: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
    else:
        base = Path(__file__).resolve().parent.parent.parent
    return str(base / "assets" / name)


def optional_icon(name: str) -> str | None:
    path = Path(asset_path(name))
    return str(path) if path.exists() else None

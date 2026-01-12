from __future__ import annotations

import sys
from pathlib import Path

root = Path(__file__).resolve().parent
src = root / "src"
if src.exists():
    sys.path.insert(0, str(src))

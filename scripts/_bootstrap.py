from __future__ import annotations

from pathlib import Path
import sys


def setup_script() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

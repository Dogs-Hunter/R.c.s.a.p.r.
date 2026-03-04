"""Resource path helpers for packaged and source runs."""
from __future__ import annotations

from pathlib import Path
import sys


def _base_resource_path() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
    return Path(__file__).resolve().parent.parent


def resolve_resource_path(path: str) -> str:
    if not path:
        return path
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    return str(_base_resource_path() / candidate)

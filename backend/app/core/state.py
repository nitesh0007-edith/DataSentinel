"""JSON-file backed state store (hackathon-grade persistence, no database)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

from app.core.logging import get_logger
from app.core.models import DemoState

log = get_logger("state")


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()

    def load(self) -> DemoState:
        with self._lock:
            if not self.path.exists():
                return DemoState()
            try:
                return DemoState.model_validate_json(self.path.read_text(encoding="utf-8"))
            except (ValueError, OSError) as exc:
                log.warning("State file unreadable (%s); starting fresh", exc)
                return DemoState()

    def save(self, state: DemoState) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = state.model_dump_json(indent=2)
            write_text_atomic(self.path, payload)

    def clear(self) -> None:
        with self._lock:
            if self.path.exists():
                self.path.unlink()


def write_text_atomic(path: Path, text: str) -> None:
    """Write via a temp file + rename so readers never see a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_json(path: Path, data: object) -> None:
    write_text_atomic(path, json.dumps(data, indent=2, default=str))

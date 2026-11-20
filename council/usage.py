"""Usage log: what the memory handed out, and to which session.

Diagnostics only. It lives beside the vault, never inside it, so it is neither searched nor backed up.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

KEEP_DAYS = 90
# Which per-note counter an event kind feeds.
COUNTS = {"inject": "injected", "read": "read", "search": "found"}


class Usage:
    def __init__(self, path: Path):
        self._lock = threading.Lock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS events(ts REAL, kind TEXT, session TEXT, query TEXT, "
                            "chars INTEGER, top REAL, hits TEXT)")
            self.db.execute("DELETE FROM events WHERE ts < ?", (time.time() - KEEP_DAYS * 86400,))

    def record(self, kind: str, session: str = "", query: str = "", chars: int = 0, top: float | None = None,
               hits=(), ts: float | None = None) -> None:
        """Log one event. ``hits`` are the note sections involved; ``top`` the best match score seen."""
        rows = [{k: h[k] for k in ("path", "heading", "score") if k in h} for h in hits]
        try:
            with self._lock, self.db:
                self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)",
                                (ts or time.time(), kind, session[:16], query[:200], chars, top, json.dumps(rows)))
        except sqlite3.Error:
            pass  # the log must never break serving memory

    def summary(self, days: float = 7) -> dict:
        with self._lock:
            rows = self.db.execute("SELECT kind, chars, hits FROM events WHERE ts >= ?",
                                   (time.time() - days * 86400,)).fetchall()
        events: dict[str, int] = {}
        notes: dict[str, dict[str, int]] = {}
        injected = []
        for kind, chars, hits in rows:
            events[kind] = events.get(kind, 0) + 1
            if kind == "inject":
                injected.append(chars)
            if kind in COUNTS:
                for path in {h["path"] for h in json.loads(hits)}:
                    notes.setdefault(path, {"injected": 0, "read": 0, "found": 0})[COUNTS[kind]] += 1
        with_notes = [c for c in injected if c]
        return {
            "events": events,
            "inject": {"messages": len(injected), "with_notes": len(with_notes),
                       "chars_mean": round(sum(with_notes) / len(with_notes)) if with_notes else 0},
            "notes": notes,
        }

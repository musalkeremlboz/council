"""Sign-in door of the panel: owner password, sessions and a lockout that survives restarts."""
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from council.oauth import FAILURE_WINDOW, MAX_FAILURES, check_password

SESSION_TTL = 12 * 3600


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Gate:
    def __init__(self, data_dir: Path):
        self.data = Path(data_dir)
        self._lock = threading.Lock()
        self.db = sqlite3.connect(self.data / "panel.sqlite3", check_same_thread=False, timeout=10)
        with self._lock, self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS sessions (hash TEXT PRIMARY KEY, expires REAL)")
            self.db.execute("CREATE TABLE IF NOT EXISTS failures (ts REAL)")

    def configured(self) -> bool:
        return (self.data / "owner.json").exists()

    def _prune(self, now: float) -> None:
        self.db.execute("DELETE FROM sessions WHERE expires <= ?", (now,))
        self.db.execute("DELETE FROM failures WHERE ts <= ?", (now - FAILURE_WINDOW,))

    def _locked(self) -> bool:
        return self.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0] >= MAX_FAILURES

    def locked(self, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        with self._lock, self.db:
            self._prune(now)
            return self._locked()

    def sign_in(self, password: str, now: float | None = None) -> str | None:
        now = time.time() if now is None else now
        with self._lock, self.db:
            self._prune(now)
            if not self.configured() or self._locked():
                return None
            try:
                record = json.loads((self.data / "owner.json").read_text())
                ok = check_password(password, record)
            except (OSError, ValueError, KeyError, TypeError):
                ok = False
            if not ok:
                self.db.execute("INSERT INTO failures (ts) VALUES (?)", (now,))
                return None
            token = secrets.token_urlsafe(32)
            self.db.execute("INSERT INTO sessions (hash, expires) VALUES (?, ?)", (_hash(token), now + SESSION_TTL))
            return token

    def valid(self, token: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        if not token:
            return False
        with self._lock, self.db:
            self._prune(now)
            rows = self.db.execute("SELECT hash FROM sessions").fetchall()
        digest = _hash(token)
        found = False
        for (stored,) in rows:                       # compare every hash in constant time
            found |= secrets.compare_digest(stored, digest)
        return found

    def sign_out(self, token: str) -> None:
        with self._lock, self.db:
            self.db.execute("DELETE FROM sessions WHERE hash = ?", (_hash(token),))

    def close(self) -> None:
        with self._lock:
            self.db.close()

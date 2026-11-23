"""Sign-in door of the panel: owner password, sessions and a lockout that survives restarts. The door can also
change the owner password (the one write the panel makes outside panel.sqlite3) and close the other sessions."""
import hashlib
import json
import secrets
import sqlite3
import threading
import time
from pathlib import Path

from council import oauth
from council.oauth import FAILURE_WINDOW, MAX_FAILURES, check_password

SESSION_TTL = 12 * 3600


def _utf8(text) -> bool:
    if not isinstance(text, str):
        return False
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Outcome(str):
    """The result of a password change ("ok", "wrong", ...), carrying how many other sessions it closed."""
    closed = 0


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

    def _check(self, password: str, now: float) -> bool:
        """The owner password against owner.json; a miss is a failure towards the lock. Sign-in and the password
        change both ask through here, so a wrong current password counts exactly like a wrong sign-in."""
        try:
            record = json.loads((self.data / "owner.json").read_text())
            ok = _utf8(password) and check_password(password, record)
        except (OSError, ValueError, KeyError, TypeError):  # never logged: a password cannot leak from here
            ok = False
        if not ok:
            self.db.execute("INSERT INTO failures (ts) VALUES (?)", (now,))
        return ok

    def _expires(self, token: str) -> float | None:
        """When the token's session ends, None for no live session. Every stored hash is compared in constant time;
        call with the lock held and after _prune."""
        if not token or not _utf8(token):
            return None
        digest = _hash(token)
        found = None
        for stored, expires in self.db.execute("SELECT hash, expires FROM sessions").fetchall():
            if secrets.compare_digest(stored, digest):
                found = expires
        return found

    def sign_in(self, password: str, now: float | None = None) -> str | None:
        now = time.time() if now is None else now
        with self._lock, self.db:
            self._prune(now)
            if not self.configured() or self._locked():
                return None
            if not self._check(password, now):
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
            return self._expires(token) is not None

    def sign_out(self, token: str) -> None:
        with self._lock, self.db:
            self.db.execute("DELETE FROM sessions WHERE hash = ?", (_hash(token),))

    def change_password(self, token: str, current: str, new: str, now: float | None = None) -> str:
        """"ok", "signed_out", "locked", "weak", "wrong" or "same", checked in that order: a caller without a session
        learns nothing; a locked door answers before any password is looked at; a new password that could never be
        accepted is refused before the current one is tried, so a slip in the new one costs no attempt; the current
        one is tried (a miss counts towards the lock) before it is compared with the new one. On "ok" owner.json is
        replaced whole and every other session is closed; the result's .closed says how many."""
        now = time.time() if now is None else now
        with self._lock, self.db:
            self._prune(now)
            if self._expires(token) is None:
                return Outcome("signed_out")
            if self._locked():
                return Outcome("locked")
            if not _utf8(new) or not oauth.MIN_PASSWORD <= len(new) <= oauth.MAX_PASSWORD:
                return Outcome("weak")
            if not self._check(current, now):
                return Outcome("wrong")
            if secrets.compare_digest(new.encode(), current.encode()):
                return Outcome("same")
            oauth.write_owner(self.data, new)  # raises before the sessions go if the file cannot be written
            done = Outcome("ok")
            done.closed = self._close_others(token)
            return done

    def _close_others(self, token: str) -> int:
        return self.db.execute("DELETE FROM sessions WHERE hash != ?", (_hash(token),)).rowcount

    def sign_out_others(self, token: str, now: float | None = None) -> int:
        """Close every session but the caller's; how many were closed (0 when the caller has no session)."""
        now = time.time() if now is None else now
        with self._lock, self.db:
            self._prune(now)
            if self._expires(token) is None:
                return 0
            return self._close_others(token)

    def session_info(self, token: str, now: float | None = None) -> dict | None:
        """How many sessions are open and when the caller's ends; None without a live session."""
        now = time.time() if now is None else now
        with self._lock, self.db:
            self._prune(now)
            expires = self._expires(token)
            if expires is None:
                return None
            return {"sessions": self.db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], "expires": expires}

    def close(self) -> None:
        with self._lock:
            self.db.close()

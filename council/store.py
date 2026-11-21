"""Markdown vault: the single source of truth.

Every note is a UTF-8 Markdown file under ``<data>/vault``. Writes are guarded by
a file lock and optimistic concurrency (sha of the version the writer read), and
each change is committed to a git repository inside the vault for history.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .index import Index

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
    import msvcrt

CORE = "core.md"
RULES = "rules.md"
THREADS = "threads.md"
SESSIONS = "sessions.md"
LOG_DIR = "log"
SESSION_ARCHIVE = "sessions"
BACKUP_REMOTE = "backup"  # git remote of the vault that `backup()` pushes to
BACKUP_GRACE = 2 * 86400  # a backup that has not succeeded for this long is reported at session start
KEEP_CARDS = 10  # sessions.md holds this many cards; older ones move to sessions/<YYYY-MM>.md

SEED = {
    CORE: "# Core\n\nWho the user is, how we work together, lasting preferences.\n",
    RULES: "# Rules\n\nUser corrections that apply to every task, one dated line each.\n"
    "Project-specific rules live in `projects/<name>/rules.md`.\n",
    THREADS: "# Threads\n\n## Active\n\n## Closed\n",
    SESSIONS: "# Sessions\n\nNewest card first. Each agent session owns exactly one card.\n",
}


class StoreError(Exception):
    """A request the store refuses; the message is safe to show to the agent."""


class Conflict(StoreError):
    """The note changed since the caller read it."""


@dataclass
class Note:
    path: str
    text: str
    sha: str


def sha_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


class Store:
    def __init__(self, data_dir: str | os.PathLike, readonly: bool = False):
        """``readonly`` opens the notes as they are on disk: nothing is seeded and nothing is committed (the
        search index, a cache outside the vault, is still brought in line with the files)."""
        self.data = Path(data_dir).expanduser().resolve()
        self.vault = self.data / "vault"
        self.vault.mkdir(parents=True, exist_ok=True)
        self._lock_path = self.data / ".write.lock"
        self.index = Index(self.data / "index.sqlite3")
        if readonly:
            self.index.sync(self.vault)
            return
        self._ensure_git()
        for name, text in SEED.items():
            if not (self.vault / name).exists():
                (self.vault / name).write_text(text, encoding="utf-8")
        self.index.sync(self.vault)
        self._commit("seed")

    # ---------- paths ----------
    def resolve(self, path: str) -> tuple[str, Path]:
        raw = (path or "").strip().replace("\\", "/").lstrip("/")
        p = PurePosixPath(raw)
        if not raw or any(part in ("", ".", "..") or part.startswith(".") for part in p.parts):
            raise StoreError(f"invalid note path: {path!r}")
        if p.suffix != ".md":
            raise StoreError("only .md notes are allowed")
        full = (self.vault / p).resolve()
        if self.vault not in full.parents:
            raise StoreError(f"path escapes the vault: {path!r}")
        return str(p), full

    # ---------- locking / git ----------
    @contextlib.contextmanager
    def _locked(self):
        with open(self._lock_path, "a+") as fh:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_EX)
            else:
                fh.seek(0)
                while True:
                    try:
                        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)  # waits ten seconds, then raises
                        break
                    except OSError:
                        continue
            try:
                yield
            finally:
                if fcntl:
                    fcntl.flock(fh, fcntl.LOCK_UN)
                else:
                    fh.seek(0)
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        # git writes UTF-8; without an explicit encoding Windows decodes it with the system code page
        return subprocess.run(["git", "-C", str(self.vault), *args], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")

    def _ensure_git(self) -> None:
        if not (self.vault / ".git").exists():
            self._git("init", "-q")
            self._git("config", "user.name", "council")
            self._git("config", "user.email", "council@localhost")

    def _commit(self, message: str) -> None:
        self._git("add", "-A")
        if self._git("diff", "--cached", "--quiet").returncode != 0:
            self._git("commit", "-q", "-m", message)

    # ---------- reads ----------
    def exists(self, path: str) -> bool:
        return self.resolve(path)[1].is_file()

    def read(self, path: str) -> Note:
        rel, full = self.resolve(path)
        if not full.is_file():
            raise StoreError(f"note not found: {rel}")
        text = full.read_text(encoding="utf-8")
        return Note(rel, text, sha_of(text))

    def list(self, prefix: str = "") -> list[str]:
        prefix = prefix.strip().lstrip("/")
        out = []
        for f in sorted(self.vault.rglob("*.md")):
            rel = f.relative_to(self.vault).as_posix()
            if rel.startswith(".") or "/." in rel:
                continue
            if rel.startswith(prefix):
                out.append(rel)
        return out

    # ---------- writes ----------
    def write(self, path: str, content: str, expected_sha: str = "", reason: str = "") -> Note:
        """Create a note, or replace it when ``expected_sha`` matches the current version."""
        rel, full = self.resolve(path)
        with self._locked():
            if full.exists():
                current = sha_of(full.read_text(encoding="utf-8"))
                if not expected_sha:
                    raise Conflict(f"{rel} exists; read it and pass its sha to replace it (sha={current})")
                if expected_sha != current:
                    raise Conflict(f"{rel} changed since you read it (now sha={current}); read it again")
            elif expected_sha:
                raise Conflict(f"{rel} does not exist; omit expected_sha to create it")
            self._save(rel, full, content, reason or f"write {rel}")
        return Note(rel, content, sha_of(content))

    def edit(self, path: str, edits: list[dict], expected_sha: str = "", reason: str = "") -> Note:
        """Apply exact-match replacements. Each ``old`` must occur exactly once."""
        rel, full = self.resolve(path)
        if not edits:
            raise StoreError("no edits given")
        with self._locked():
            if not full.is_file():
                raise StoreError(f"note not found: {rel}")
            text = full.read_text(encoding="utf-8")
            if expected_sha and expected_sha != sha_of(text):
                raise Conflict(f"{rel} changed since you read it (now sha={sha_of(text)}); read it again")
            for i, e in enumerate(edits, 1):
                old, new = e.get("old", ""), e.get("new", "")
                if not old:
                    raise StoreError(f"edit {i}: 'old' is empty")
                n = text.count(old)
                if n != 1:
                    raise StoreError(f"edit {i}: 'old' occurs {n} times in {rel}; it must occur exactly once")
                text = text.replace(old, new, 1)
            self._save(rel, full, text, reason or f"edit {rel}")
        return Note(rel, text, sha_of(text))

    def remove(self, path: str, reason: str = "") -> None:
        """Delete a note; git keeps its history."""
        rel, full = self.resolve(path)
        with self._locked():
            if not full.is_file():
                raise StoreError(f"note not found: {rel}")
            full.unlink()
            self.index.remove_file(rel)
            self._commit(reason or f"remove {rel}")

    def move(self, src: str, dst: str, reason: str = "") -> Note:
        """Rename a note without changing its text; refuses to overwrite an existing note."""
        src_rel, src_full = self.resolve(src)
        dst_rel, dst_full = self.resolve(dst)
        with self._locked():
            if not src_full.is_file():
                raise StoreError(f"note not found: {src_rel}")
            if dst_full.exists():
                raise Conflict(f"{dst_rel} already exists; pick another destination")
            text = src_full.read_text(encoding="utf-8")
            dst_full.parent.mkdir(parents=True, exist_ok=True)
            os.replace(src_full, dst_full)
            self.index.remove_file(src_rel)
            self.index.update_file(dst_rel, text)
            self._commit(reason or f"move {src_rel} to {dst_rel}")
        return Note(dst_rel, text, sha_of(text))

    def _save(self, rel: str, full: Path, content: str, message: str) -> None:
        full.parent.mkdir(parents=True, exist_ok=True)
        tmp = full.with_name(f".{full.name}.tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, full)
        self.index.update_file(rel, content)
        self._commit(message)

    # ---------- structured writes ----------
    def upsert_session(self, session_id: str, label: str, body: str) -> Note:
        """Write this session's card at the top of sessions.md, replacing only its own card."""
        sid = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")[:8]
        if not sid:
            raise StoreError("session_id is required")
        label = " ".join((label or "session").split())[:80]
        rel, full = self.resolve(SESSIONS)
        with self._locked():
            text = full.read_text(encoding="utf-8") if full.exists() else SEED[SESSIONS]
            pattern = re.compile(rf"^## [^\n]* · {re.escape(sid)}\n.*?(?=^## |\Z)", re.M | re.S)
            m = pattern.search(text)
            stamp = (m.group(0).split(" · ")[0][3:] if m else now_local().strftime("%Y-%m-%d %H:%M"))
            card = f"## {stamp} · {label} · {sid}\n\n{body.strip()}\n\n"
            if m:
                text = text[: m.start()] + card + text[m.end():]
            else:
                first = re.search(r"^## ", text, re.M)
                if first:
                    text = text[: first.start()] + card + text[first.start():]
                else:
                    text = text.rstrip("\n") + "\n\n" + card
            text = self._archive_old_cards(text)
            self._save(rel, full, text, f"session {sid}: {label}")
        return Note(rel, text, sha_of(text))

    def _archive_old_cards(self, text: str) -> str:
        """Keep the newest KEEP_CARDS cards; append the rest to the archive of the month they were opened."""
        starts = [m.start() for m in re.finditer(r"^## ", text, re.M)]
        if len(starts) <= KEEP_CARDS:
            return text
        cut = starts[KEEP_CARDS]
        for a, b in zip(starts[KEEP_CARDS:], starts[KEEP_CARDS + 1:] + [len(text)]):
            card = text[a:b].strip()
            m = re.match(r"## (\d{4}-\d{2})-", card)
            month = m.group(1) if m else f"{now_local():%Y-%m}"
            rel, full = self.resolve(f"{SESSION_ARCHIVE}/{month}.md")
            old = full.read_text(encoding="utf-8") if full.exists() else f"# Sessions {month}\n"
            self._save(rel, full, old.rstrip("\n") + "\n\n" + card + "\n", f"archive session card to {rel}")
        return text[:cut].rstrip("\n") + "\n"

    def append_log(self, summary: str, refs: list[str], session_id: str = "", agent: str = "") -> str:
        """Record what a session did, with links to the notes it changed."""
        summary = (summary or "").strip()
        if not summary:
            raise StoreError("summary is required")
        clean_refs = []
        for r in refs or []:
            rel, full = self.resolve(r)
            if not full.is_file():
                raise StoreError(f"ref does not exist: {rel}")
            clean_refs.append(rel)
        t = now_local()
        rel, full = self.resolve(f"{LOG_DIR}/{t:%Y-%m}.md")
        with self._locked():
            text = full.read_text(encoding="utf-8") if full.exists() else f"# Log {t:%Y-%m}\n\n"
            who = " · ".join(x for x in (agent, (session_id or "")[:8]) if x)
            entry = f"## {t:%Y-%m-%d %H:%M}{' · ' + who if who else ''}\n\n{summary}\n"
            if clean_refs:
                entry += "\nRefs: " + ", ".join(f"[[{r}]]" for r in clean_refs) + "\n"
            self._save(rel, full, text.rstrip("\n") + "\n\n" + entry, f"log {session_id[:8]}".strip())
            if session_id:
                marks = self.session_logs()
                marks[session_id[:8]] = t.timestamp()
                tmp = self.data / ".session-logs.json.tmp"
                tmp.write_text(json.dumps(marks))
                os.replace(tmp, self.data / "session-logs.json")
        return rel

    def open_thread(self, entry: str, reason: str) -> None:
        """Put ``entry`` (a `### ` block) at the top of the active threads."""
        note = self.read(THREADS)
        marker = "## Active\n"
        text = note.text
        text = text.replace(marker, marker + "\n" + entry, 1) if marker in text else text.rstrip("\n") + "\n\n" + entry
        self.write(THREADS, text, expected_sha=note.sha, reason=reason)

    # ---------- off-site backup ----------
    def backup(self) -> dict:
        """Push the vault history to the ``backup`` git remote and remember how it went."""
        if BACKUP_REMOTE not in self._git("remote").stdout.split():
            return {"ok": False, "error": f"no `{BACKUP_REMOTE}` git remote in the vault"}
        try:
            r = subprocess.run(["git", "-C", str(self.vault), "push", "-q", BACKUP_REMOTE, "HEAD:refs/heads/main"],
                               capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=120, env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
            error = "" if r.returncode == 0 else (r.stderr.strip().splitlines() or ["push failed"])[-1][:200]
        except subprocess.TimeoutExpired:
            error = "push timed out"
        status = self._backup_status() or {"first_run": time.time(), "last_ok": None}
        status["error"] = error
        if not error:
            status["last_ok"] = time.time()
        tmp = self.data / ".backup.json.tmp"
        tmp.write_text(json.dumps(status))
        os.replace(tmp, self.data / "backup.json")
        return {"ok": not error, "error": error}

    def _backup_status(self) -> dict | None:
        try:
            return json.loads((self.data / "backup.json").read_text())
        except (OSError, ValueError):
            return None

    def backup_problem(self) -> str | None:
        """A sentence for the agent when a configured backup has not succeeded for BACKUP_GRACE; else None."""
        status = self._backup_status()
        if not status:
            return None
        since = status.get("last_ok") or status.get("first_run") or 0
        if time.time() - since <= BACKUP_GRACE:
            return None
        when = dt.datetime.fromtimestamp(status["last_ok"]).strftime("%Y-%m-%d") if status.get("last_ok") else "never"
        return (f"The off-site backup of the memory last succeeded: {when} "
                f"({status.get('error') or 'no backup run since'}).")

    def session_logs(self) -> dict[str, float]:
        """Exact time of each session's latest council_log, keyed by the first 8 chars of its id."""
        f = self.data / "session-logs.json"
        try:
            return json.loads(f.read_text())
        except (OSError, ValueError):
            return self._backfill_session_logs()

    def _backfill_session_logs(self) -> dict[str, float]:
        """Rebuild marks from log headers (minute precision, so count to the end of that minute)."""
        marks: dict[str, float] = {}
        tz = now_local().tzinfo
        for f in sorted((self.vault / LOG_DIR).glob("*.md")):
            for m in re.finditer(r"^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})(?: · [^\n]*)? · ([A-Za-z0-9_-]{1,8})\s*$",
                                 f.read_text(encoding="utf-8"), re.M):
                t = dt.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=tz).timestamp() + 59
                marks[m.group(2)] = max(marks.get(m.group(2), 0.0), t)
        return marks

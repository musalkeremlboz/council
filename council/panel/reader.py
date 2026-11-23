"""The one place the panel reads the memory. It hands out paths, counts and times, and nothing else.

No function here returns a note's body, a section heading, the text of a user message, the text of a rule,
a commit message or the text of a check question: those are read, if at all, only to be counted or dropped.
Every function but ``open_memory`` returns an empty result when its file is missing, unreadable or busy,
and never raises to its caller. Nothing here writes to the memory.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
import subprocess
from pathlib import Path

from .. import check
from ..learn import is_skill
from ..store import Store
from ..usage import COUNTS, Usage

_SECTION = re.compile(r"^#{1,3}(?:\s|$)", re.M)
_STATUS = re.compile(r"^([A-Z])\d*\t(.+)$")
_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}
_LEDGER_KINDS = {"rule": "rule", "skill_new": "skill", "skill_edit": "skill"}
GIT_TIMEOUT = 30


def open_memory(data_dir) -> Store:
    return Store(data_dir, frozen=True)


def note_list(store: Store) -> list[dict]:
    """Every note as ``{"path", "sections", "chars", "skill"}``, sorted by path."""
    out = []
    try:
        paths = sorted(store.list())
    except OSError:
        return []
    for path in paths:
        try:
            text = store.read(path).text
        except Exception:  # gone meanwhile, or not UTF-8
            continue
        out.append({"path": path, "sections": len(_SECTION.findall(text)), "chars": len(text),
                    "skill": is_skill(path)})
    return out


def note_links(store: Store) -> dict[str, list[str]]:
    try:
        return check.note_links(store)
    except Exception:
        return {}


def _usage(data_dir):
    try:
        return Usage(Path(data_dir) / "usage.sqlite3", readonly=True)
    except (OSError, sqlite3.Error):
        return None


def _paths(hits: str | None) -> list[str]:
    try:
        rows = json.loads(hits or "[]")
        return list(dict.fromkeys(h["path"] for h in rows if isinstance(h.get("path"), str)))
    except (ValueError, TypeError, AttributeError, KeyError):
        return []


def events(data_dir, since: float, limit: int = 500, kind: str | None = None) -> list[dict]:
    """Usage events since ``since``, newest first: ``{"ts", "kind", "chars", "paths"}``. With ``kind``, only
    events of that kind; the limit applies after that filter."""
    usage = _usage(data_dir)
    if usage is None:
        return []
    try:
        where, args = ("ts >= ?", [since]) if kind is None else ("ts >= ? AND kind = ?", [since, kind])
        rows = usage.db.execute(f"SELECT ts, kind, chars, hits FROM events WHERE {where} ORDER BY ts DESC LIMIT ?",
                                (*args, limit)).fetchall()
        return [{"ts": ts, "kind": kind, "chars": chars or 0, "paths": _paths(hits)} for ts, kind, chars, hits in rows]
    except sqlite3.Error:
        return []
    finally:
        usage.db.close()


def event_totals(data_dir, kind: str, since: float) -> dict[str, int]:
    """Events of ``kind`` since ``since`` counted by the log itself, so no limit applies: ``{"count", "given",
    "chars"}``, where ``given`` counts the events that carried characters and ``chars`` adds them up."""
    zero = {"count": 0, "given": 0, "chars": 0}
    usage = _usage(data_dir)
    if usage is None:
        return zero
    try:
        count, given, chars = usage.db.execute("SELECT COUNT(*), SUM(chars > 0), SUM(chars) FROM events "
                                               "WHERE kind = ? AND ts >= ?", (kind, since)).fetchone()
    except sqlite3.Error:
        return zero
    finally:
        usage.db.close()
    return {"count": count or 0, "given": given or 0, "chars": chars or 0}


def pointed(data_dir, since: float) -> int:
    """Skills pointed at since ``since``: one per entry of each pointer event, as the service counts them."""
    usage = _usage(data_dir)
    if usage is None:
        return 0
    try:
        n = usage.db.execute("SELECT SUM(CASE WHEN json_valid(hits) AND json_type(hits) = 'array' "
                             "THEN json_array_length(hits) ELSE 0 END) FROM events WHERE kind = 'pointer' AND ts >= ?",
                             (since,)).fetchone()[0]
    except sqlite3.Error:
        return 0
    finally:
        usage.db.close()
    return n or 0


def usage_mark(data_dir) -> tuple | None:
    """A cheap mark that changes whenever a row is added to or dropped from the log; None without a log."""
    usage = _usage(data_dir)
    if usage is None:
        return None
    try:
        return tuple(usage.db.execute("SELECT MIN(rowid), MAX(rowid), COUNT(*) FROM events").fetchone())
    except sqlite3.Error:
        return None
    finally:
        usage.db.close()


def note_count(store: Store) -> int:
    """How many notes there are, from the listing alone: no note is opened."""
    try:
        return len(store.list())
    except OSError:
        return 0


def note_usage(data_dir) -> dict[str, dict[str, int]]:
    """Per note, how often it was injected, read and found by search over the whole log."""
    usage = _usage(data_dir)
    if usage is None:
        return {}
    try:
        marks = ",".join("?" * len(COUNTS))
        rows = usage.db.execute(f"SELECT kind, hits FROM events WHERE kind IN ({marks})", tuple(COUNTS)).fetchall()
    except sqlite3.Error:
        return {}
    finally:
        usage.db.close()
    out: dict[str, dict[str, int]] = {}
    for kind, hits in rows:
        for path in _paths(hits):
            out.setdefault(path, {"injected": 0, "read": 0, "found": 0})[COUNTS[kind]] += 1
    return out


def usage_since(data_dir) -> float | None:
    usage = _usage(data_dir)
    if usage is None:
        return None
    try:
        return usage.db.execute("SELECT MIN(ts) FROM events").fetchone()[0]
    except sqlite3.Error:
        return None
    finally:
        usage.db.close()


def _unquote(name: str) -> str:
    """A path as git prints it: plain, or in double quotes with C escapes and octal bytes."""
    if len(name) < 2 or not (name.startswith('"') and name.endswith('"')):
        return name
    raw, body, i = bytearray(), name[1:-1], 0
    while i < len(body):
        ch = body[i]
        if ch != "\\" or i + 1 >= len(body):
            raw += ch.encode("utf-8")
            i += 1
        elif body[i + 1] in "01234567":
            j = i + 1
            while j < min(i + 4, len(body)) and body[j] in "01234567":
                j += 1
            raw.append(int(body[i + 1:j], 8) & 255)
            i = j
        else:
            raw.append(_ESCAPES.get(body[i + 1], ord(body[i + 1]) if ord(body[i + 1]) < 128 else 63))
            i += 2
    return raw.decode("utf-8", errors="replace")


def changes(store: Store, since: float) -> list[dict]:
    """Commits touching notes since ``since``, newest first: ``{"ts", "paths", "added"}``. Only the time of a
    commit and the status and path of each file are asked of git; a commit's subject is never requested."""
    stamp = dt.datetime.fromtimestamp(max(since, 0), dt.timezone.utc).isoformat()
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(store.vault.parent), "GIT_TERMINAL_PROMPT": "0"}
    try:
        r = subprocess.run(["git", "-C", str(store.vault), "log", f"--since={stamp}", "--format=@%at",
                            "--name-status", "--", "*.md"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=GIT_TIMEOUT, env=env)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    out: list[dict] = []
    for line in r.stdout.splitlines():
        if line.startswith("@") and line[1:].isdigit():
            out.append({"ts": float(line[1:]), "paths": [], "added": []})
            continue
        m = _STATUS.match(line)
        if m and out:
            paths = [_unquote(p) for p in m.group(2).split("\t")]
            for p in paths:
                if p not in out[-1]["paths"]:
                    out[-1]["paths"].append(p)
            if m.group(1) == "A":
                out[-1]["added"].append(paths[0])
    return [c for c in out if c["paths"]]


def first_change(store: Store) -> float | None:
    """The time of the vault's first commit, or None when it has none. Only the root commits are listed, so
    the lookup stays one short git call however long the history is."""
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(store.vault.parent), "GIT_TERMINAL_PROMPT": "0"}
    try:
        r = subprocess.run(["git", "-C", str(store.vault), "log", "--max-parents=0", "--format=%at", "HEAD", "--"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT,
                           env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    times = [float(x) for x in r.stdout.split() if x.isdigit()] if r.returncode == 0 else []
    return min(times) if times else None


def vault_head(store: Store) -> str | None:
    """The commit the vault's HEAD names, or None when there is none. git is asked for the commit id only."""
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(store.vault.parent), "GIT_TERMINAL_PROMPT": "0"}
    try:
        r = subprocess.run(["git", "-C", str(store.vault), "rev-parse", "--verify", "-q", "HEAD"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=GIT_TIMEOUT, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    head = r.stdout.strip()
    return head if r.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", head) else None


def learnings(data_dir, since: float) -> list[dict]:
    """Rules and skills learned since ``since``, newest first: ``{"ts", "kind", "path", "undone"}``."""
    try:
        state = json.loads((Path(data_dir) / "learning.json").read_text(encoding="utf-8"))
        ledger = state["ledger"]
        assert isinstance(ledger, list)
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        return []
    out = []
    for e in ledger:
        try:
            kind = _LEDGER_KINDS[e["kind"]]
            ts = dt.datetime.fromisoformat(e["ts"]).timestamp()
            path = e["path"]
        except (KeyError, TypeError, ValueError):
            continue
        if ts >= since and isinstance(path, str):
            out.append({"ts": ts, "kind": kind, "path": path, "undone": bool(e.get("undone"))})
    return sorted(out, key=lambda x: x["ts"], reverse=True)


def backup_state(data_dir) -> dict | None:
    """``{"last_ok", "failing"}`` from backup.json; None when no backup has ever run."""
    try:
        status = json.loads((Path(data_dir) / "backup.json").read_text(encoding="utf-8"))
        ok = status.get("last_ok")
        return {"last_ok": float(ok) if isinstance(ok, (int, float)) and not isinstance(ok, bool) else None,
                "failing": bool(status.get("error"))}
    except (OSError, ValueError, AttributeError):
        return None

"""Self-improvement: skill notes the agent writes after solving something worth repeating.

Why a module of its own: the store stays a plain note vault, while this layer knows the
skill format, refuses secrets, and keeps ``learning.json`` (ledger, later rules and feedback).
``learning.json`` is never cached: the server and the CLI are separate processes, so every
operation reads it from disk and every change is saved under the store's write lock.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import PurePosixPath

from .index import fold
from .store import Store, StoreError, now_local

MAX_SKILL_CHARS = 4000
MAX_WHEN_CHARS = 200
STATE_FILE = "learning.json"
SESSION_KEY = 16  # sessions are keyed by this many leading characters of the session id
SESSION_SHORT = 8  # and shown in notes by this many

# ---------- paths and names ----------


def _parts(path: str) -> tuple[str, ...]:
    return PurePosixPath(path.replace("\\", "/")).parts


def _skill_dir_depth(parts: tuple[str, ...]) -> int | None:
    """Index of the 'skills' folder in a skill path, or None when the path is not under one."""
    if parts[:1] == ("skills",):
        return 0
    if len(parts) > 2 and parts[0] == "projects" and parts[2] == "skills":
        return 2
    return None


def is_skill(path: str) -> bool:
    """A live skill: skills/<name>.md or projects/<p>/skills/<name>.md (not the retired folder)."""
    parts = _parts(path)
    i = _skill_dir_depth(parts)
    return i is not None and len(parts) == i + 2 and parts[-1].endswith(".md")


def is_retired(path: str) -> bool:
    parts = _parts(path)
    i = _skill_dir_depth(parts)
    return i is not None and len(parts) == i + 3 and parts[i + 1] == "retired" and parts[-1].endswith(".md")


def slug(text: str) -> str:
    """Safe file-name part: folded ASCII words joined by '-', so it can never climb out of a folder."""
    out = "-".join(re.findall(r"[a-z0-9]+", fold(text)))[:60].strip("-")
    if not out or out == "retired":
        raise StoreError(f"cannot make a safe name from {text!r}; use letters or digits (and not 'retired')")
    return out


def skill_path(title: str, project: str = "", retired: bool = False) -> str:
    base = f"projects/{slug(project)}/skills" if project.strip() else "skills"
    return f"{base}/{'retired/' if retired else ''}{slug(title)}.md"


# ---------- secret check ----------

_KEYWORDS = r"password|passwd|parola|şifre|sifre|secret|token|api_key|api-key|apikey"
_SECRETS = [
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("API token", re.compile(r"(?<![\w-])sk-[A-Za-z0-9_-]{20,}")),
    ("GitHub token", re.compile(r"(?<![\w-])gh[pousr]_[A-Za-z0-9]{20,}")),
    ("Slack token", re.compile(r"(?<![\w-])xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("AWS key", re.compile(r"(?<![\w-])AKIA[0-9A-Z]{16}")),
    ("bearer token", re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{20,}")),
    ("password or key assignment", re.compile(rf"(?:{_KEYWORDS})\s*[:=]\s*\S{{6,}}", re.IGNORECASE)),
]


def find_secret(text: str) -> str | None:
    """Short label of the first secret-looking thing in ``text``, else None."""
    for label, pattern in _SECRETS:
        if pattern.search(text):
            return label
    return None


# ---------- skill note format ----------


def render_skill(title: str, when: str, steps: str, learned_from: str, pitfalls: str = "",
                 status: str = "candidate", source: str = "", revised: str = "") -> str:
    lines = [f"# {title}", "", f"- **When:** {when}", f"- **Status:** {status}"]
    if source:
        lines.append(f"- **Source:** {source}")
    if revised:
        lines.append(f"- **Revised:** {revised}")
    lines += ["", "## Steps", steps.strip()]
    if pitfalls.strip():
        lines += ["", "## Pitfalls", pitfalls.strip()]
    lines += ["", "## Learned from", learned_from.strip(), ""]
    return "\n".join(lines)


_FIELD = re.compile(r"^- \*\*(When|Status|Source|Revised):\*\* ?(.*)$", re.MULTILINE)
_SECTION = re.compile(r"^## (Steps|Pitfalls|Learned from)[ \t]*$", re.MULTILINE)


def parse_skill(text: str) -> dict:
    """Read a skill note back into fields; anything missing comes back as an empty string."""
    head = re.match(r"# (.*)", text)
    out = {"title": head.group(1).strip() if head else "", "when": "", "status": "", "source": "",
           "revised": "", "steps": "", "pitfalls": "", "learned_from": ""}
    marks = list(_SECTION.finditer(text))
    first = marks[0].start() if marks else len(text)
    for m in _FIELD.finditer(text[:first]):
        out[m.group(1).lower()] = m.group(2).strip()
    keys = {"Steps": "steps", "Pitfalls": "pitfalls", "Learned from": "learned_from"}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[keys[m.group(1)]] = text[m.end():end].strip()
    return out


def _stamp(session: str) -> str:
    day = now_local().date().isoformat()
    return f"{day}, session {session[:SESSION_SHORT]}" if session else day


# ---------- the learning layer ----------


class Learning:
    def __init__(self, store: Store):
        self.store = store
        self.state_path = store.data / STATE_FILE

    # state: always read from disk, always saved under the store's write lock
    def _load(self) -> dict:
        try:
            state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return state if isinstance(state, dict) else {}

    def _save(self, state: dict) -> None:
        tmp = self.state_path.with_name(f".{STATE_FILE}.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def _record(self, entry: dict) -> None:
        with self.store._locked():
            state = self._load()
            ledger = state.get("ledger")
            if not isinstance(ledger, list):
                ledger = state["ledger"] = []
            ledger.append(entry)
            self._save(state)

    def write_skill(self, title: str, when: str, steps: str, learned_from: str, pitfalls: str = "",
                    project: str = "", expected_sha: str = "", session: str = "") -> dict:
        """Create a candidate skill, or revise one (status and source stay) when ``expected_sha`` matches."""
        if "\n" in when.strip() or "\r" in when.strip():
            raise StoreError("When must be a single line")
        title, when = " ".join(title.split()), " ".join(when.split())
        path = skill_path(title, project)
        if not when:
            raise StoreError("When is required: one line saying when this skill applies")
        if len(when) > MAX_WHEN_CHARS:
            raise StoreError(f"When is too long ({len(when)} characters); keep it to {MAX_WHEN_CHARS}")
        for name, value in (("steps", steps), ("learned_from", learned_from)):
            if not value.strip():
                raise StoreError(f"{name} is required")
        for name, value in (("steps", steps), ("pitfalls", pitfalls), ("learned_from", learned_from)):
            if any(line.startswith(("# ", "## ")) for line in value.splitlines()):
                raise StoreError(f"{name} has a line starting with a level 1 or 2 heading; it would break the note's "
                                 "structure (level 3 and deeper are fine)")
        if len(steps) + len(pitfalls) + len(learned_from) > MAX_SKILL_CHARS:
            raise StoreError(f"skill is too long; steps, pitfalls and learned_from together may use {MAX_SKILL_CHARS} characters")
        secret = find_secret("\n".join((title, when, steps, pitfalls, learned_from)))
        if secret:
            raise StoreError(f"refused: looks like a secret ({secret})")

        stamp, retired_path = _stamp(session), skill_path(title, project, retired=True)
        before: str | None = None  # text an undo restores: the old version, or the retired note of a comeback
        status, source, revised = "candidate", stamp, ""
        if expected_sha:
            before = self.store.read(path).text  # missing note -> StoreError
            old = parse_skill(before)
            status, source, revised = old["status"] or "candidate", old["source"] or stamp, stamp
        text = render_skill(title, when, steps, learned_from, pitfalls, status, source, revised)
        # Comeback: move the retired note to its live path first, then write over it, so a note exists throughout.
        retired_path_used: str | None = None
        if expected_sha:
            note = self.store.write(path, text, expected_sha, f"skill edit: {path}")
        elif not self.store.exists(path) and self.store.exists(retired_path):
            before, retired_path_used = self.store.read(retired_path).text, retired_path
            moved = self.store.move(retired_path, path, f"skill {path} rewritten; back from retired")
            note = self.store.write(path, text, moved.sha, f"skill new: {path}")
        else:
            note = self.store.write(path, text, "", f"skill new: {path}")
        edited = bool(expected_sha)
        self._record({"id": uuid.uuid4().hex[:8], "ts": now_local().isoformat(timespec="seconds"),
                      "kind": "skill_edit" if edited else "skill_new", "path": path,
                      "session": session[:SESSION_KEY], "before": before, "retired_path": retired_path_used,
                      "undone": False})
        verb = "Revised" if edited else "Learned"
        notice = (f"{verb} skill '{title}' ({status}) and saved it as {path}; tell the user in one line, "
                  "in their language, what you learned, and that they can ask you to undo it.")
        return {"path": path, "sha": note.sha, "status": status, "notice": notice}

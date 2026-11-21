"""Self-improvement: skill notes the agent writes after solving something worth repeating.

Why a module of its own: the store stays a plain note vault, while this layer knows the
skill format, refuses secrets, and keeps ``learning.json`` (ledger, later rules and feedback).
``learning.json`` is never cached: the server and the CLI are separate processes, so every
operation reads it from disk and every change is saved under the store's write lock.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import uuid
from pathlib import PurePosixPath

from .index import build_query, fold
from .store import RULES, Store, StoreError, now_local, sha_of

MAX_SKILL_CHARS = 4000
MAX_WHEN_CHARS = 200
STATE_FILE = "learning.json"
SESSION_KEY = 16  # sessions are keyed by this many leading characters of the session id
SESSION_SHORT = 8  # and shown in notes by this many
REPEAT_SHARE = 0.6  # a new rule is a possible repeat when it shares this share of its stems with a rule...
REPEAT_MIN = 3  # ...and at least this many stems
PROMOTE_AFTER = 3  # a candidate becomes established after 'helped' feedback in this many different sessions
RETIRE_WRONG = 2  # a skill retires after this many 'wrong' feedbacks...
RETIRE_SHOWN = 5  # ...or after being shown in this many different sessions with no 'helped' at all
OUTCOMES = ("helped", "not_helped", "wrong")

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
    ("password or key assignment", re.compile(rf"(?:{_KEYWORDS})[ \t]*[:=][ \t]*\S{{6,}}", re.IGNORECASE)),
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


_DATED = re.compile(r"^- \d{4}-\d{2}-\d{2}")
_STEM = re.compile(r'"([^"]+)"\*')


def _stems(text: str) -> set[str]:
    """The content stems search would use for ``text`` (filler words dropped)."""
    return set(_STEM.findall(build_query(text, content_only=True)))


def _closest_rule(text: str, lines: list[str]) -> str | None:
    """The dated rule line most like ``text`` when it is similar enough to be a possible repeat."""
    mine = _stems(text)
    best, best_common = None, 0
    for line in lines:
        common = len(mine & _stems(line.split(": ", 1)[-1]))
        if common > best_common:
            best, best_common = line, common
    if best is not None and best_common >= REPEAT_MIN and best_common >= REPEAT_SHARE * len(mine):
        return best
    return None


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
        self._keep_bad_copy()
        tmp = self.state_path.with_name(f".{STATE_FILE}.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.state_path)

    def _keep_bad_copy(self) -> None:
        """An unreadable state file is about to be replaced: keep it as learning.json.bad so history is not lost."""
        try:
            ok = isinstance(json.loads(self.state_path.read_text(encoding="utf-8")), dict)
        except FileNotFoundError:
            return
        except (OSError, ValueError):
            ok = False
        if not ok:
            shutil.copyfile(self.state_path, self.state_path.with_name(f"{STATE_FILE}.bad"))

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
                      "after": note.sha, "undone": False})
        verb = "Revised" if edited else "Learned"
        notice = (f"{verb} skill '{title}' ({status}) and saved it as {path}; tell the user in one line, "
                  "in their language, what you learned, and that they can ask you to undo it.")
        return {"path": path, "sha": note.sha, "status": status, "notice": notice}

    def add_rule(self, text: str, project: str = "", session: str = "") -> dict:
        """Append a dated rule line to the rules note; a rule on a subject already covered is flagged, not refused."""
        if "\n" in text.strip() or "\r" in text.strip():
            raise StoreError("a rule must be a single line")
        text = " ".join(text.split())
        if not text:
            raise StoreError("rule text is required")
        secret = find_secret(text)
        if secret:
            raise StoreError(f"refused: looks like a secret ({secret})")
        path = f"projects/{slug(project)}/rules.md" if project.strip() else RULES
        exists = self.store.exists(path)
        old = self.store.read(path).text if exists else f"# Rules: {' '.join(project.split())}\n\n"
        existing = [ln for ln in old.splitlines() if _DATED.match(ln)]
        repeat = _closest_rule(text, existing)

        line = f"- {now_local().date().isoformat()}: {text}"
        rows = old.split("\n")
        at = max((i for i, ln in enumerate(rows) if _DATED.match(ln)), default=None)
        if at is None:
            new = old + ("" if old.endswith("\n") else "\n") + line + "\n"
        else:
            rows.insert(at + 1, line)
            new = "\n".join(rows)
        # The sha of what we read makes a concurrent change a Conflict instead of a lost line.
        note = self.store.write(path, new, sha_of(old) if exists else "", f"rule: {path}")
        self._record({"id": uuid.uuid4().hex[:8], "ts": now_local().isoformat(timespec="seconds"), "kind": "rule",
                      "path": path, "line": line, "repeat_of": repeat, "session": session[:SESSION_KEY],
                      "undone": False})
        notice = (f"Added a rule to {path}; tell the user in one line, in their language, what rule you saved, "
                  "and that they can ask you to undo it.")
        if repeat:
            notice += f" It may repeat an existing rule ({repeat}); mention that and ask whether to keep both."
        return {"path": path, "sha": note.sha, "notice": notice, "possible_repeat": repeat}

    # ---------- undo ----------

    def unlearn(self, session: str = "") -> dict:
        """Undo the latest learning not yet undone (of ``session`` when given); refuses when its note changed since."""
        key = session[:SESSION_KEY]
        ledger = self._load().get("ledger")
        entry = next((e for e in reversed(ledger if isinstance(ledger, list) else [])
                      if isinstance(e, dict) and not e.get("undone") and (not key or e.get("session") == key)), None)
        if entry is None:
            raise StoreError("nothing to undo" + (" in this session" if key else ""))
        path, kind = entry["path"], entry["kind"]

        def changed() -> StoreError:
            return StoreError(f"{path} changed since it was learned; not undoing it. Look at the note and fix it by hand")

        if kind == "rule":
            note = self.store.read(path) if self.store.exists(path) else None
            rows = note.text.split("\n") if note else []
            if rows.count(entry["line"]) != 1:
                raise changed()
            rows.remove(entry["line"])
            self.store.write(path, "\n".join(rows), note.sha, f"undo rule: {path}")
        else:
            note = self.store.read(path) if self.store.exists(path) else None
            if note is None or (entry.get("after") and note.sha != entry["after"]):
                raise changed()
            if kind == "skill_edit":
                self.store.write(path, entry["before"], note.sha, f"undo skill edit: {path}")
            else:
                if entry.get("retired_path"):  # a comeback: the retired note returns first, so nothing is ever lost
                    self.store.write(entry["retired_path"], entry["before"], "", f"undo comeback: {entry['retired_path']}")
                self.store.remove(path, f"undo skill new: {path}")
        with self.store._locked():
            state = self._load()
            for e in state.get("ledger", []):
                if isinstance(e, dict) and e.get("id") == entry["id"]:
                    e["undone"] = True
            self._save(state)
        return {"undone": kind, "path": path,
                "notice": f"Undone ({kind.replace('_', ' ')}) in {path}; tell the user in one line, in their language."}

    # ---------- shown, feedback, promotion and retirement ----------

    @staticmethod
    def _skill_state(state: dict, path: str) -> dict:
        skills = state.get("skills")
        if not isinstance(skills, dict):
            skills = state["skills"] = {}
        entry = skills.get(path)
        if not isinstance(entry, dict):
            entry = skills[path] = {}
        if not isinstance(entry.get("shown"), list):
            entry["shown"] = []
        if not isinstance(entry.get("helped"), list):
            entry["helped"] = []
        if not isinstance(entry.get("wrong"), int):
            entry["wrong"] = 0
        return entry

    @staticmethod
    def _verdict(entry: dict) -> str:
        """What the counters say about a skill: 'retire', 'promote' or 'keep'."""
        if entry["wrong"] >= RETIRE_WRONG or (len(entry["shown"]) >= RETIRE_SHOWN and not entry["helped"]):
            return "retire"
        return "promote" if len(entry["helped"]) >= PROMOTE_AFTER else "keep"

    def _settle(self, path: str, verdict: str) -> dict:
        """Carry out a verdict on the note itself; returns the skill's resulting path and status.

        Called after the counters are saved and the lock released: the store takes the same
        lock for each note change, and the lock is not re-entrant.
        """
        text = self.store.read(path).text
        status = parse_skill(text)["status"] or "candidate"
        if verdict == "keep" or (verdict == "promote" and status != "candidate"):
            return {"path": path, "status": status}
        new = "retired" if verdict == "retire" else "established"
        if status != new:
            self.store.edit(path, [{"old": f"- **Status:** {status}", "new": f"- **Status:** {new}"}],
                            reason=f"skill {new}: {path}")
        if verdict == "promote":
            return {"path": path, "status": new}
        parts = list(_parts(path))
        parts.insert(-1, "retired")
        retired = "/".join(parts)
        self.store.move(path, retired, f"skill retired: {path}")
        with self.store._locked():  # a comeback under the same name must start with fresh counters
            state = self._load()
            if isinstance(state.get("skills"), dict) and state["skills"].pop(path, None) is not None:
                self._save(state)
        return {"path": retired, "status": "retired"}

    @staticmethod
    def _evidence_key(session: str) -> str:
        """Key a session's evidence is counted under; without a session id the day stands in for it."""
        return session[:SESSION_KEY] or f"day:{now_local().date().isoformat()}"

    def record_shown(self, path: str, session: str) -> None:
        """Note that a skill was shown to a session (counted once per session or, with none, per day); may retire it."""
        key = self._evidence_key(session)
        if not is_skill(path) or not self.store.exists(path):
            return
        with self.store._locked():
            state = self._load()
            entry = self._skill_state(state, path)
            if key not in entry["shown"]:
                entry["shown"].append(key)
                self._save(state)
            verdict = self._verdict(entry)
        if verdict == "retire":
            self._settle(path, verdict)

    def shown_in(self, session: str) -> list[str]:
        """Skills already shown to this session, so they are not shown again."""
        key = session[:SESSION_KEY]
        skills = self._load().get("skills")
        if not key or not isinstance(skills, dict):
            return []
        return [p for p, e in skills.items() if isinstance(e, dict) and key in (e.get("shown") or [])]

    def feedback(self, name: str, outcome: str, session: str = "", project: str = "") -> dict:
        """Record whether a skill helped; may promote it to established or retire it."""
        if outcome not in OUTCOMES:
            raise StoreError(f"outcome must be one of {', '.join(OUTCOMES)}")
        path = skill_path(name, project)
        if not self.store.exists(path):
            raise StoreError(f"no live skill named {name!r} at {path}")
        key = session[:SESSION_KEY]
        with self.store._locked():
            state = self._load()
            entry = self._skill_state(state, path)
            if outcome == "helped" and self._evidence_key(session) not in entry["helped"]:
                entry["helped"].append(self._evidence_key(session))
            elif outcome == "wrong":
                entry["wrong"] += 1
            events = state.get("feedback")
            if not isinstance(events, list):
                events = state["feedback"] = []
            events.append({"ts": now_local().isoformat(timespec="seconds"), "path": path,
                           "outcome": outcome, "session": key})
            self._save(state)
            verdict = self._verdict(entry)
        return self._settle(path, verdict)

    def note_review_asked(self) -> None:
        """Count one time the agent asked the user to review what it learned."""
        with self.store._locked():
            state = self._load()
            asked = state.get("reviews")
            if not isinstance(asked, list):
                asked = state["reviews"] = []
            asked.append(now_local().isoformat(timespec="seconds"))
            self._save(state)

    def summary(self, days: int = 7) -> dict:
        """Counts of what was learned in the last ``days``; the keys a later task completes are empty for now."""
        state = self._load()
        cutoff = now_local() - dt.timedelta(days=days)

        def recent(ts) -> bool:
            try:
                return dt.datetime.fromisoformat(ts) >= cutoff
            except (TypeError, ValueError):
                return False

        ledger = state.get("ledger") if isinstance(state.get("ledger"), list) else []
        reviews = state.get("reviews") if isinstance(state.get("reviews"), list) else []
        return {
            "reviews_asked": sum(1 for ts in reviews if recent(ts)),
            "skills_new": sum(1 for e in ledger if isinstance(e, dict) and e.get("kind") == "skill_new"
                              and recent(e.get("ts"))),
            "skills_revised": 0, "rules": 0, "undone": 0, "established": 0, "retired": 0,
            "helped_rate": None, "possible_repeats": [],
        }

"""Self-improvement: skill notes the agent writes after solving something worth repeating.

Why a module of its own: the store stays a plain note vault, while this layer knows the
skill format, refuses secrets, and keeps ``learning.json`` (ledger, later rules and feedback).
``learning.json`` is never cached: the server and the CLI are separate processes, so every
operation reads it from disk and every change is saved under the store's write lock.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import re
import shutil
import uuid
from pathlib import PurePosixPath

from .index import build_query, fold
from .store import RULES, Store, StoreError, now_local, sha_of

MAX_SKILL_CHARS = 4000
MAX_WHEN_CHARS = 200
MAX_TITLE_CHARS = 80
MAX_RULE_CHARS = 300
STATE_FILE = "learning.json"
SESSION_KEY = 16  # sessions are keyed by this many leading characters of the session id
SESSION_SHORT = 8  # and shown in notes by this many
REPEAT_SHARE = 0.6  # a new rule is a possible repeat when it shares this share of its stems with a rule...
REPEAT_MIN = 3  # ...and at least this many stems
PROMOTE_AFTER = 3  # a candidate becomes established after 'helped' feedback in this many different sessions
RETIRE_WRONG = 2  # a skill retires after this many 'wrong' feedbacks...
RETIRE_NOT_HELPED = 5  # ...or after 'not_helped' from this many different sessions and 'helped' from none
OUTCOMES = ("helped", "not_helped", "wrong")
HEAD_WEIGHT = 4.0  # a message word in a skill's title or When line counts this many times its rarity
MIN_HEAD_WORDS = 2  # a skill is offered only when this many different message words are in its title or When line...
MIN_SCORE = 6.0  # ...and its score, divided by the square root of the message's word count, reaches this
SKILL_LIMIT = 2  # skills offered for one message
SKILL_BUDGET = 1500  # characters of context the offered skills may take together, apart from the notes' budget
RARITY_LIBRARY = 10  # rarity counts the library as at least this big, so scores do not depend on how many skills exist
STEM_PREFIX_MIN = 4  # a stem matches a longer one it prefixes only when it has this many characters

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


# Names Windows will not open as files, whatever the extension.
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}


def slug(text: str) -> str:
    """Safe file-name part: folded ASCII words joined by '-', so it can never climb out of a folder."""
    out = "-".join(re.findall(r"[a-z0-9]+", fold(text)))[:60].strip("-")
    if not out or out == "retired":
        raise StoreError(f"cannot make a safe name from {text!r}; use letters or digits (and not 'retired')")
    if out in _RESERVED:
        raise StoreError(f"{out!r} is a reserved file name on Windows; pick another name")
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
    ("JWT", re.compile(r"(?<![\w-])eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}")),
    ("Google API key", re.compile(r"(?<![\w-])AIza[0-9A-Za-z_-]{35}")),
    ("password in a URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@", re.IGNORECASE)),
    # A value with no digit is prose ("token: Refreshing the page"), not a secret.
    ("password or key assignment", re.compile(rf"(?:{_KEYWORDS})[ \t]*[:=][ \t]*(?=\S*\d)\S{{6,}}", re.IGNORECASE)),
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


_STATUS_LINE = re.compile(r"^- \*\*Status:\*\*")


def _with_status(text: str, status: str) -> str | None:
    """``text`` with the Status line of its header (the lines before the first ``## ``) set to ``status``.

    Changed by position, never by a text match over the whole note: the steps may quote a Status
    line. None when the header has no Status line or more than one.
    """
    rows = text.split("\n")
    end = next((i for i, row in enumerate(rows) if row.startswith("## ")), len(rows))
    found = [i for i in range(end) if _STATUS_LINE.match(rows[i])]
    if len(found) != 1:
        return None
    rows[found[0]] = f"- **Status:** {status}"
    return "\n".join(rows)


LIVE = ("candidate", "established")  # statuses a skill is offered with


def as_skill(path: str, text: str) -> dict | None:
    """Fields of a note that counts as a skill, else None: the note is then an ordinary one.

    It must sit in a live skills folder, be complete (title, When, Steps, Learned from), say
    candidate, established or retired in its Status line, and hold nothing find_secret objects
    to: a note put there by other means never reaches the skills block without a skill's checks.
    A retired one still counts, so a half-finished retirement stays out of every context.
    """
    if not is_skill(path):
        return None
    fields = parse_skill(text)
    if not all(fields[k] for k in ("title", "when", "steps", "learned_from")):
        return None
    if fields["status"] not in (*LIVE, "retired") or find_secret(text):
        return None
    return fields


def _stamp(session: str) -> str:
    day = now_local().date().isoformat()
    return f"{day}, session {session[:SESSION_SHORT]}" if session else day


_DATED = re.compile(r"^- \d{4}-\d{2}-\d{2}")
_STEM = re.compile(r'"([^"]+)"\*')


def _stems(text: str) -> set[str]:
    """The content stems search would use for ``text`` (filler words dropped)."""
    return set(_STEM.findall(build_query(text, content_only=True)))


def _stem_hit(stem: str, stems: set[str]) -> bool:
    """Whether ``stem`` equals a stem in ``stems`` or is a prefix of one (or the other way round)."""
    return any(stem == o or (min(len(stem), len(o)) >= STEM_PREFIX_MIN and (o.startswith(stem) or stem.startswith(o)))
               for o in stems)


def _words(stems: set[str]) -> list[list[str]]:
    """``stems`` grouped into words: forms of one word ("sistem", "sistemi", "sistemim") count once."""
    words: list[list[str]] = []
    for stem in sorted(stems, key=lambda s: (len(s), s)):
        for word in words:
            if _stem_hit(stem, {word[0]}):
                word.append(stem)
                break
        else:
            words.append([stem])
    return words


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

    def write_skill(self, name: str, when: str, steps: str, learned_from: str, pitfalls: str = "",
                    project: str = "", expected_sha: str = "", session: str = "") -> dict:
        """Create a candidate skill, or revise one (status and source stay) when ``expected_sha`` matches."""
        if "\n" in when.strip() or "\r" in when.strip():
            raise StoreError("When must be a single line")
        title, when = " ".join(name.split()), " ".join(when.split())
        if len(title) > MAX_TITLE_CHARS:
            raise StoreError(f"name is too long ({len(title)} characters); keep it to {MAX_TITLE_CHARS}")
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
        if len(text) > MAX_RULE_CHARS:
            raise StoreError(f"rule is too long ({len(text)} characters); keep it to {MAX_RULE_CHARS}")
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
        path, kind = entry.get("path"), entry.get("kind")
        if not isinstance(path, str) or kind not in ("rule", "skill_edit", "skill_new"):
            raise StoreError("the latest ledger entry is damaged or of an unknown kind; not undoing anything")

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
            if kind == "skill_new" and isinstance(state.get("skills"), dict):
                state["skills"].pop(path, None)  # a new skill under the same name must not inherit these counters
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
        if not isinstance(entry.get("not_helped"), list):
            entry["not_helped"] = []
        if not isinstance(entry.get("wrong"), int):
            entry["wrong"] = 0
        return entry

    @staticmethod
    def _verdict(entry: dict) -> str:
        """What the counters say about a skill: 'retire', 'promote' or 'keep'."""
        if entry["wrong"] >= RETIRE_WRONG or (len(entry["not_helped"]) >= RETIRE_NOT_HELPED and not entry["helped"]):
            return "retire"
        return "promote" if len(entry["helped"]) >= PROMOTE_AFTER else "keep"

    def _settle(self, path: str, verdict: str) -> dict:
        """Carry out a verdict on the note itself; returns the skill's resulting path and status.

        Called after the counters are saved and the lock released: the store takes the same
        lock for each note change, and the lock is not re-entrant. A note the verdict cannot be
        carried out on (unreadable, no single Status line in its header, a retired twin in the
        way) is left as it is: one bad note must not break feedback or the skills block.
        """
        status = ""
        try:
            note = self.store.read(path)
            status = parse_skill(note.text)["status"] or "candidate"
            if verdict == "keep" or (verdict == "promote" and status != "candidate"):
                return {"path": path, "status": status}
            new = "retired" if verdict == "retire" else "established"
            if status != new:
                text = _with_status(note.text, new)
                if text is None:
                    return {"path": path, "status": status}
                self.store.write(path, text, note.sha, f"skill {new}: {path}")
                status = new  # what the note now says, should the move below fail
            if verdict == "promote":
                return {"path": path, "status": status}
            parts = list(_parts(path))
            parts.insert(-1, "retired")
            retired = "/".join(parts)
            self.store.move(path, retired, f"skill retired: {path}")
        except (StoreError, OSError, ValueError):  # ValueError: a note that is not UTF-8
            return {"path": path, "status": status}
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
        """Note that a skill was shown to a session (once per session or, with none, per day).

        Only recorded, for the review question: showing never retires a skill, since a session may
        end, or run without hooks, before anyone could say whether it helped.
        """
        key = self._evidence_key(session)
        try:
            if not is_skill(path) or not self.store.exists(path):
                return
        except StoreError:  # a path the store refuses: nothing to record
            return
        with self.store._locked():
            state = self._load()
            entry = self._skill_state(state, path)
            if key not in entry["shown"]:
                entry["shown"].append(key)
                self._save(state)

    def shown_in(self, session: str) -> list[str]:
        """Skills already shown to this session, so they are not shown again."""
        key = session[:SESSION_KEY]
        skills = self._load().get("skills")
        if not key or not isinstance(skills, dict):
            return []
        return [p for p, e in skills.items() if isinstance(e, dict) and key in (e.get("shown") or [])]

    def feedback(self, name: str, outcome: str, session: str = "", project: str = "") -> dict:
        """Record whether a skill helped; may promote it to established or retire it.

        ``name`` is the skill's path as the context and the review question show it (``project`` is
        then ignored), or its title, slugged under ``project``.
        """
        if outcome not in OUTCOMES:
            raise StoreError(f"outcome must be one of {', '.join(OUTCOMES)}")
        given = name.strip().replace("\\", "/")
        path = given if is_skill(given) else skill_path(name, project)
        live = self.skills().get(path)
        if live is None or live[1]["status"] not in LIVE:
            raise StoreError(f"no live skill named {name!r} at {path}")
        key = session[:SESSION_KEY]
        with self.store._locked():
            state = self._load()
            entry = self._skill_state(state, path)
            if outcome in ("helped", "not_helped") and self._evidence_key(session) not in entry[outcome]:
                entry[outcome].append(self._evidence_key(session))
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

    def skills(self) -> dict[str, tuple[str, dict]]:
        """Every note in a live skills folder that counts as a skill (see ``as_skill``), by path: its
        text and fields. A note that cannot be read is left out."""
        out = {}
        for path in self.store.list():
            if not is_skill(path):
                continue
            try:
                text = self.store.read(path).text
            except (StoreError, OSError, ValueError):  # gone since listing, unreadable, or not UTF-8
                continue
            if (fields := as_skill(path, text)) is not None:
                out[path] = (text, fields)
        return out

    def match(self, query: str, limit: int = SKILL_LIMIT) -> list[dict]:
        """Live skills worth offering for ``query``, best first.

        Every live skill is scored, not only those a vault-wide search ranks high: ordinary notes
        sharing the words must not crowd a skill out. A message word found in the title or When line
        counts HEAD_WEIGHT times its rarity, a word found only in the body counts its rarity once.
        The sum is divided by the square root of the number of words in the message, so a long
        message does not match by length alone. A skill is offered with at least MIN_HEAD_WORDS
        different words in its title or When line and a score of MIN_SCORE: the body alone, where
        any long message finds some of its words, never brings a skill up.
        """
        words = _words(_stems(query))
        if not words:
            return []
        live = {p: v for p, v in self.skills().items() if v[1]["status"] in LIVE}
        if not live:
            return []
        head = {p: _stems(f"{f['title']} {f['when']}") for p, (_, f) in live.items()}
        body = {p: _stems(f"{f['steps']} {f['pitfalls']} {f['learned_from']}") for p, (_, f) in live.items()}
        whole = {p: head[p] | body[p] for p in live}
        n = max(len(live), RARITY_LIBRARY)  # floored: a small library must not shrink every score
        rarity = []  # of each word: that of its rarest form
        for word in words:
            df = min(sum(1 for p in live if _stem_hit(s, whole[p])) for s in word)
            rarity.append(math.log(1 + n / max(df, 1)))
        out = []
        for path, (text, fields) in live.items():
            total, in_head = 0.0, 0
            for word, rare in zip(words, rarity):
                if any(_stem_hit(s, head[path]) for s in word):
                    total += HEAD_WEIGHT * rare
                    in_head += 1
                elif any(_stem_hit(s, body[path]) for s in word):
                    total += rare
            score = total / math.sqrt(len(words))
            if in_head >= MIN_HEAD_WORDS and score >= MIN_SCORE:
                out.append({"path": path, "title": fields["title"], "status": fields["status"],
                            "text": text, "score": round(score, 3)})
        out.sort(key=lambda m: -m["score"])
        return out[:limit]

    def note_review_asked(self) -> None:
        """Count one time the agent asked the user to review what it learned."""
        with self.store._locked():
            state = self._load()
            asked = state.get("reviews")
            if not isinstance(asked, list):
                asked = state["reviews"] = []
            asked.append(now_local().isoformat(timespec="seconds"))
            self._save(state)

    def summary(self, days: float = 7) -> dict:
        """What was learned in the last ``days``, plus how many skills are established or retired right now."""
        state = self._load()
        cutoff = now_local() - dt.timedelta(days=days)

        def recent(ts) -> bool:
            try:
                return dt.datetime.fromisoformat(ts) >= cutoff
            except (TypeError, ValueError):
                return False

        def events(key: str) -> list[dict]:
            raw = state.get(key) if isinstance(state.get(key), list) else []
            return [e for e in raw if isinstance(e, dict) and recent(e.get("ts"))]

        ledger = events("ledger")
        kinds = [e.get("kind") for e in ledger]
        reviews = state.get("reviews") if isinstance(state.get("reviews"), list) else []
        verdicts = [e.get("outcome") for e in events("feedback")]
        paths = self.store.list()
        # skills() skips a note that vanished or cannot be read since listing: a count must not fail usage.
        established = sum(1 for _, fields in self.skills().values() if fields["status"] == "established")
        return {
            "reviews_asked": sum(1 for ts in reviews if recent(ts)),
            "skills_new": kinds.count("skill_new"), "skills_revised": kinds.count("skill_edit"),
            "rules": kinds.count("rule"), "undone": sum(1 for e in ledger if e.get("undone")),
            "established": established, "retired": sum(1 for p in paths if is_retired(p)),
            "helped_rate": verdicts.count("helped") / len(verdicts) if verdicts else None,
            "possible_repeats": [{"line": e.get("line"), "repeat_of": e["repeat_of"]}
                                 for e in ledger if e.get("kind") == "rule" and e.get("repeat_of")],
        }

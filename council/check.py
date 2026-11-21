"""Checks that change nothing: do the owner's questions still find their notes, do links still lead to a note.

Questions live in ``<data>/questions.json``, outside the vault: a note holding them would match itself in
every search it is meant to measure.
"""
from __future__ import annotations

import json
import os
import posixpath
import re
from urllib.parse import unquote

from .context import FIXED, relevant
from .store import LOG_DIR, SESSION_ARCHIVE, SESSIONS, Store, StoreError, now_local

QUESTIONS_FILE = "questions.json"
SEARCH_LIMIT = 8  # what council_search returns by default
INSTEAD = 3  # notes named for a missed question
MAYBE = 3  # places named for a broken link


class CheckError(Exception):
    """A question that cannot be saved, or a questions file that cannot be read."""


# ---------- questions ----------

def _same(a: str, b: str) -> bool:
    return " ".join(a.split()).casefold() == " ".join(b.split()).casefold()


def questions(store: Store) -> list[dict]:
    """The saved questions: ``{"question", "expect": [paths], "added"}``. A file that is not what this
    module wrote is reported, never replaced."""
    path = store.data / QUESTIONS_FILE
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        ok = isinstance(data, list) and all(
            isinstance(q, dict) and isinstance(q.get("question"), str) and isinstance(q.get("expect"), list)
            and all(isinstance(p, str) for p in q["expect"]) for q in data)
    except (OSError, ValueError):
        ok = False
    if not ok:
        raise CheckError(f"{path} is not a readable list of questions; fix or remove it")
    return data


def _save(store: Store, data: list[dict]) -> None:
    tmp = store.data / f".{QUESTIONS_FILE}.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, store.data / QUESTIONS_FILE)


def add_question(store: Store, question: str, paths: list[str]) -> dict:
    """Save a question and the notes one of which must come back for it; the same question again replaces it."""
    question = " ".join(question.split())
    if not question:
        raise CheckError("the question is empty")
    expect: list[str] = []
    for p in paths:
        try:
            rel, full = store.resolve(p)
        except StoreError as e:
            raise CheckError(str(e)) from e
        if not full.is_file():
            raise CheckError(f"note not found: {rel}")
        if rel not in expect:
            expect.append(rel)
    if not expect:
        raise CheckError("name at least one note the question should find")
    entry = {"question": question, "expect": expect, "added": now_local().date().isoformat()}
    _save(store, [q for q in questions(store) if not _same(q["question"], question)] + [entry])
    return entry


def remove_question(store: Store, question: str) -> bool:
    """Drop a saved question; False if it was not there."""
    data = questions(store)
    kept = [q for q in data if not _same(q["question"], question)]
    if len(kept) == len(data):
        return False
    _save(store, kept)
    return True


# ---------- search ----------

def _exists(store: Store, path: str) -> bool:
    try:
        return store.exists(path)
    except StoreError:
        return False


def _paths(hits: list[dict]) -> list[str]:
    return list(dict.fromkeys(h["path"] for h in hits))


def search_report(store: Store) -> dict:
    """For every saved question: does one of its notes come by itself with a message (what ``relevant``
    sends, or a note every session starts with), and does the search tool find it.

    A question whose notes are all gone is not measured; it is listed under ``gone``.
    """
    asked = questions(store)
    out = {"questions": len(asked), "measured": 0, "auto": 0, "search": 0, "missed": [], "gone": []}
    for q in asked:
        expect = [p for p in q["expect"] if _exists(store, p)]
        if not expect:
            out["gone"].append({"question": q["question"], "expect": q["expect"]})
            continue
        trace: dict = {}
        relevant(store, q["question"], trace=trace)
        came = _paths(trace.get("shown", []))
        found = _paths(store.index.search(q["question"], limit=SEARCH_LIMIT))
        auto = any(p in FIXED or p in came for p in expect)
        search = any(p in found for p in expect)
        out["measured"] += 1
        out["auto"] += auto
        out["search"] += search
        if not (auto and search):
            out["missed"].append({"question": q["question"], "expect": expect, "auto": auto, "search": search,
                                  "got_auto": came[:INSTEAD], "got_search": found[:INSTEAD]})
    return out


def render_search(r: dict) -> str:
    if not r["questions"]:
        return 'search: no questions yet (add one: council check add "question" path/to/note.md)\n'
    head = f"search: {r['questions']} questions"
    if r["measured"]:
        head += (f" · comes by itself {r['auto']}/{r['measured']}"
                 f" · found by search {r['search']}/{r['measured']}")
    if r["gone"]:
        head += f" · {len(r['gone'])} with no note left"
    lines = [head]
    for m in r["missed"]:
        lines.append(f'  missed: "{m["question"]}"')
        lines.append(f"    expected: {', '.join(m['expect'])}")
        if not m["auto"]:
            lines.append(f"    by itself came: {', '.join(m['got_auto']) or 'nothing'}")
        if not m["search"]:
            lines.append(f"    search found: {', '.join(m['got_search']) or 'nothing'}")
    for g in r["gone"]:
        lines.append(f'  note gone: "{g["question"]}" (expected {", ".join(g["expect"])})')
    return "\n".join(lines) + "\n"


# ---------- links ----------

_FENCE = re.compile(r"^[ \t]*(```|~~~).*?(?:^[ \t]*\1[ \t]*$|\Z)", re.M | re.S)
_CODE = re.compile(r"(`+)[^\n]*?\1")
_WIKI = re.compile(r"\[\[([^\[\]|#\n]+)(?:#[^\[\]|\n]*)?(?:\|[^\[\]\n]*)?\]\]")
_MD = re.compile(r"(?<!!)\[[^\[\]\n]*\]\(\s*<?([^()\s<>]+)>?(?:\s+\"[^\"\n]*\")?\s*\)")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_EXT = re.compile(r"\.[A-Za-z0-9]{1,5}$")
HISTORY = (LOG_DIR + "/", SESSION_ARCHIVE + "/")  # records of the day they were written; never rewritten


def _targets(text: str) -> list[str]:
    """Link targets that claim to be notes, in order: ``[[target]]`` and ``[text](target.md)``.

    Code (fenced or inline) only shows what a link looks like; web addresses, anchors, images and other
    files are not notes.
    """
    text = _CODE.sub(" ", _FENCE.sub("\n", text))
    out = []
    for m in _WIKI.finditer(text):
        t = m.group(1).strip()
        if t and not _SCHEME.match(t) and (t.endswith(".md") or not _EXT.search(t)):
            out.append((m.start(), t))
    for m in _MD.finditer(text):
        t = unquote(m.group(1)).split("#", 1)[0].strip()
        if t.endswith(".md") and not _SCHEME.match(t):
            out.append((m.start(), t))
    return [t for _, t in sorted(out)]


def _resolves(note: str, target: str, notes: set[str], stems: set[str]) -> bool:
    """Whether ``target`` written in ``note`` names a note: from the vault root or from the note's folder,
    with or without ``.md``; a bare name also names a note of that name in any folder."""
    names = [target] if target.endswith(".md") else [target, target + ".md"]
    for name in names:
        for base in ("", posixpath.dirname(note)):
            path = posixpath.normpath(posixpath.join(base, name.lstrip("/") if not base else name))
            if path in notes:
                return True
    return "/" not in target and target.removesuffix(".md") in stems


def link_report(store: Store) -> dict:
    """Links between notes that lead nowhere. History (the log, session cards) is not read: it shows the
    day it was written. A broken link comes with notes of the same file name elsewhere, if there are any."""
    notes = set(store.list())
    stems = {posixpath.basename(p).removesuffix(".md") for p in notes}
    by_name: dict[str, list[str]] = {}
    for p in sorted(notes):
        by_name.setdefault(posixpath.basename(p), []).append(p)
    checked, broken = 0, {}
    for note in sorted(notes):
        if note == SESSIONS or note.startswith(HISTORY):
            continue
        try:
            text = store.read(note).text
        except (StoreError, OSError, ValueError):  # gone meanwhile, or not UTF-8: nothing to check in it
            continue
        for target in _targets(text):
            checked += 1
            if not _resolves(note, target, notes, stems):
                name = posixpath.basename(target)
                name = name if name.endswith(".md") else name + ".md"
                broken[(note, target)] = {"note": note, "target": target, "maybe": by_name.get(name, [])[:MAYBE]}
    return {"checked": checked, "broken": [broken[k] for k in sorted(broken)]}


def render_links(r: dict) -> str:
    lines = [f"links: {r['checked']} checked, {len(r['broken'])} broken"]
    for b in r["broken"]:
        maybe = f"  (maybe: {', '.join(b['maybe'])})" if b["maybe"] else ""
        lines.append(f"  {b['note']} → {b['target']}{maybe}")
    return "\n".join(lines) + "\n"

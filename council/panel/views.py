"""The sections of the panel as data: the live schema with its events, today's activity, health, the notes, the
map and the releases.

Only note paths, counts, character totals and times leave this module. ``context.start_plan`` and the skill
index hand over the notes' text; it is measured here and dropped. No heading, query, stem, rule text, commit
message or check question is ever put into a value this module returns; questions are known by number only.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import json
import logging
import threading
from importlib import resources
from pathlib import Path

from .. import __version__, check, context, learn
from ..learn import Learning, is_skill
from ..store import CORE, LOG_DIR, RULES, SEED, SESSIONS, THREADS
from . import mechanism, reader, text_tr
from . import sampler as sampler_mod

AT_LIMIT = lambda chars: chars >= context.MESSAGE_BUDGET - context.MIN_ROOM  # noqa: E731

EVENT_COUNT = 30
SCHEMA_WINDOW = 30 * 86400  # how far back the schema looks for events
DAY = 86400
LANES = ("start", "inject", "read", "search", "open", "pointer")
_LANE_OF = {"start": "start", "context": "start", "inject": "inject", "read": "read", "search": "search",
            "open": "open", "pointer": "pointer"}
_WRITES = ("card", "thread", "log", "note")
_SAME_COMMIT = 5  # seconds within which a learning and a commit of the same kind are one event
log = logging.getLogger("council")


@contextlib.contextmanager
def _memory(data_dir):
    """A frozen store for one call; its search index is closed again before the call returns."""
    store = reader.open_memory(data_dir)
    try:
        yield store
    finally:
        store.index.db.close()


class _Cache:
    """One value per data folder and kind, kept with the mark it was computed for (the vault's HEAD, the usage
    log's rows) and computed again when the mark moves. A value is stored whole, as one tuple, so two requests
    that race compute it twice at worst and never see half of one. It holds only what an answer carries."""

    def __init__(self):
        self._lock = threading.Lock()
        self._entries: dict[tuple[str, str], tuple] = {}

    def get(self, data_dir, kind: str, mark, compute):
        if mark is None:  # nothing to know a change by: never kept
            return compute()
        key = (str(Path(data_dir).resolve()), kind)
        with self._lock:
            entry = self._entries.get(key)
        if entry is not None and entry[0] == mark:
            return entry[1]
        value = compute()
        with self._lock:
            self._entries[key] = (mark, value)
        return value


_CACHE = _Cache()


def _plan(store):
    # The budgets are passed on every call: start_plan's own defaults were fixed when it was defined.
    return context.start_plan(store, budget=context.START_BUDGET, cards=context.START_CARDS, announce=False)


def _shown_chars(section: dict) -> int:
    return len(section["sep"].join(section["units"][:section["shown"]]))


def _left_out(plan: dict) -> list[dict]:
    return [{"name": text_tr.UNIT_NAMES[s["path"]], "chars": len(unit)}
            for s in plan["sections"] for unit in s["units"][s["shown"]:]]


def _parts(plan: dict) -> list[dict]:
    return [{"name": text_tr.SECTION_NAMES[s["path"]], "chars": _shown_chars(s)} for s in plan["sections"]]


def _index(store) -> tuple[int, int, int]:
    """Characters of the skill index as served, skills listed, skills left out."""
    paths, left = Learning(store).index()
    return len(context.skills_index(Learning(store), learn.INDEX_BUDGET)), len(paths), left


# ---------- the schema ----------

def _change_kind(paths: list[str]) -> str:
    rules = (
        ("card", lambda p: p == SESSIONS),
        ("thread", lambda p: p == THREADS),
        ("log", lambda p: p.startswith(LOG_DIR + "/")),
        ("rule", lambda p: p.rsplit("/", 1)[-1] == RULES),
        ("skill", is_skill),
    )
    return next((kind for kind, matches in rules if any(matches(p) for p in paths)), "note")


def _lines(paths: list[str]) -> str:
    return "\n".join(paths)


def _step(block: str, key: str, value: str = "") -> dict:
    return {"block": block, "text": text_tr.STEPS[key], "value": value}


def _usage_events(raw: list[dict]) -> list[dict]:
    """Usage events as journeys. A pointer event is not an event of its own: it lights the pointer block of the
    inject that shares its second."""
    pointers: dict[int, list[str]] = {}
    for e in raw:
        if e["kind"] == "pointer":
            pointers.setdefault(int(e["ts"]), []).extend(e["paths"])
    out = []
    for e in raw:
        kind, paths, chars = e["kind"], e["paths"], e["chars"]
        notes = text_tr.VALUES["notes"].format(n=len(paths))
        count = text_tr.VALUES["chars"].format(n=chars)
        if kind in ("start", "context"):
            path = (["h1"] if kind == "start" else []) + ["bas", "diz", "haf"]
            steps = ([_step("h1", "h1")] if kind == "start" else []) + [
                _step("bas", "bas", count), _step("diz", "diz"), _step("haf", "haf_read")]
            memory = "read"
        elif kind == "inject" and not chars:
            path, steps, memory = ["h2", "ara", "sec"], [_step("h2", "h2"), _step("ara", "ara"),
                                                          _step("sec", "sec_none", notes)], ""
        elif kind == "inject":
            marked = pointers.get(int(e["ts"]))
            size = count + (" · " + text_tr.VALUES["at_limit"] if AT_LIMIT(chars) else "")
            path = ["h2", "ara", "sec", "haf"] + (["isa"] if marked else [])
            steps = [_step("h2", "h2"), _step("ara", "ara"), _step("sec", "sec", f"{notes} · {size}")]
            if marked:
                steps.append(_step("isa", "isa", _lines(list(dict.fromkeys(marked)))))
            steps.append(_step("haf", "haf_inject", _lines(paths)))
            memory = "read"
        elif kind in ("read", "open", "search"):
            value = _lines(([notes] if kind == "search" else []) + paths)
            path, steps, memory = ["haf"], [_step("haf", {"read": "haf_note", "open": "haf_open",
                                                          "search": "haf_search"}[kind], value)], "read"
        else:  # a pointer, or a kind this panel does not know
            continue
        out.append({"ts": e["ts"], "kind": kind, "title": text_tr.KIND_TITLES[kind], "path": path,
                    "memory": memory, "steps": steps})
    return out


def _write_event(ts: float, kind: str, paths: list[str]) -> dict:
    if kind in _WRITES:
        path = ["h3", "yaz", "haf"]
        steps = [_step("h3", "h3"), _step("yaz", f"yaz_{kind}", text_tr.VALUES["notes"].format(n=len(paths))),
                 _step("haf", "haf_written", _lines(paths))]
    else:
        path = ["h3", "ogr", "haf"]
        steps = [_step("h3", "h3"), _step("ogr", f"ogr_{kind}"), _step("haf", "haf_written", _lines(paths))]
    return {"ts": ts, "kind": kind, "title": text_tr.KIND_TITLES[kind], "path": path, "memory": "written",
            "steps": steps}


def _is_birth(change: dict) -> bool:
    """The commit that seeded a new memory is its birth, not something that was done in it."""
    return set(change["paths"]) <= set(SEED) and set(change["added"]) == set(change["paths"])


def _write_events(store, data_dir, since: float) -> list[dict]:
    out = [_write_event(c["ts"], _change_kind(c["paths"]), c["paths"])
           for c in reader.changes(store, since) if not _is_birth(c)]
    for e in reader.learnings(data_dir, since):
        # a rule or skill is also a commit of its own; the commit already says so
        if not any(o["kind"] == e["kind"] and abs(o["ts"] - e["ts"]) <= _SAME_COMMIT for o in out):
            out.append(_write_event(e["ts"], e["kind"], [e["path"]]))
    return out


def _numbers(store, data_dir, now: float, index: tuple[int, int, int], notes: int) -> dict[str, list[str]]:
    n = text_tr.NUMBERS
    numbers: dict[str, list[str]] = {b["id"]: [] for b in mechanism.blocks()}
    plan = _plan(store)
    for s in plan["sections"]:
        numbers["bas"].append(n["bas_part"].format(name=text_tr.SECTION_NAMES[s["path"]], chars=_shown_chars(s)))
        out = s["units"][s["shown"]:]
        if out:
            numbers["bas"].append(n["bas_left"].format(name=text_tr.SECTION_NAMES[s["path"]], count=len(out),
                                                       chars=sum(len(u) for u in out)))
    _, listed, left = index
    numbers["diz"] = [n["diz_listed"].format(n=listed)] + ([n["diz_left"].format(n=left)] if left else [])
    messages = reader.event_totals(data_dir, "inject", now - DAY)
    numbers["h2"] = [n["h2_messages"].format(n=messages["count"])]
    numbers["sec"] = [n["sec_given"].format(n=messages["given"])] + (
        [n["sec_mean"].format(n=round(messages["chars"] / messages["given"]))] if messages["given"] else [])
    week = now - 7 * DAY
    numbers["isa"] = [n["isa_pointers"].format(n=reader.pointed(data_dir, week)),
                      n["isa_opened"].format(n=reader.event_totals(data_dir, "open", week)["count"])]
    changed = [c for c in reader.changes(store, week) if not _is_birth(c)]
    numbers["haf"] = [n["haf_notes"].format(n=notes), n["haf_changes"].format(n=len(changed))]
    backup = reader.backup_state(data_dir)
    ok = backup and backup["last_ok"]
    numbers["yed"] = [n["yed_ok"].format(when=dt.datetime.fromtimestamp(ok).strftime("%Y-%m-%d %H:%M"))
                      if ok else n["yed_none"]]
    try:
        numbers["den"] = [n["den_questions"].format(n=len(check.questions(store)))]
    except Exception:  # an unreadable questions file is shown as no line, not as a wrong number
        log.exception("saved questions not counted")
    return numbers


def schema(data_dir, now: dt.datetime, sampler=None) -> dict:
    """The status line, the blocks, a live line or two per block and the 30 newest events with their journeys.
    With the panel's ``sampler``, the status line also holds the service's state and the newest check run."""
    ts = now.timestamp()
    since = ts - SCHEMA_WINDOW
    with _memory(data_dir) as store:
        index = _index(store)
        _, listed, left = index
        count = reader.note_count(store)
        backup = reader.backup_state(data_dir) or {}
        status = {"notes": count, "backup_last_ok": backup.get("last_ok"),
                  "backup_failing": bool(backup.get("failing")), "skills": listed + left,
                  "service": _now_state(sampler, ts)["service"], "check": _check_totals(sampler),
                  "panel_version": __version__, "service_version": _service_version(sampler, ts)}
        numbers = _numbers(store, data_dir, ts, index, count)
        events = _usage_events(reader.events(data_dir, since)) + _write_events(store, data_dir, since)
    events.sort(key=lambda e: e["ts"], reverse=True)
    return {"status": status, "lanes": list(mechanism.LANES), "blocks": mechanism.blocks(), "numbers": numbers,
            "events": events[:EVENT_COUNT]}


# ---------- today ----------

def today(data_dir, now: dt.datetime) -> dict:
    """Today's usage events (the memory's local day containing ``now``), their counts and the budgets."""
    local = now.astimezone()
    day = local.date()
    start = dt.datetime(day.year, day.month, day.day).timestamp()  # local midnight, whatever the offset then
    out, counts = [], dict.fromkeys(LANES, 0)
    for e in reversed(reader.events(data_dir, start, limit=100000)):  # oldest first
        lane = _LANE_OF.get(e["kind"])
        moment = dt.datetime.fromtimestamp(e["ts"])
        if lane is None or moment.date() != day or (lane == "inject" and not e["chars"]):
            continue  # a message that got no note is not counted and not drawn
        counts[lane] += 1
        out.append({"minute": moment.hour * 60 + moment.minute, "lane": lane, "chars": e["chars"],
                    "at_limit": lane == "inject" and AT_LIMIT(e["chars"])})
    with _memory(data_dir) as store:
        plan = _plan(store)
        chars, listed, left = _index(store)
    return {"date": day.isoformat(), "now_minute": local.hour * 60 + local.minute, "lanes": list(LANES),
            "events": out, "counts": counts, "at_limit": sum(e["at_limit"] for e in out),
            "budgets": {"start": {"budget": context.START_BUDGET, "parts": _parts(plan), "left_out": _left_out(plan)},
                        "message": {"budget": context.MESSAGE_BUDGET, "min_room": context.MIN_ROOM},
                        "index": {"budget": learn.INDEX_BUDGET, "chars": chars, "listed": listed,
                                  "left_out": left}}}


# ---------- health ----------

def _now_state(sampler, ts: float) -> dict[str, str]:
    """The state of each component in the newest sample; a sample older than two sampling periods says
    nothing about now."""
    newest = sampler.latest() if sampler is not None else None
    fresh = newest is not None and ts - newest["ts"] <= 2 * sampler_mod.SAMPLE_EVERY
    return {c: sampler_mod.state_of([newest[c]]) if fresh else "none" for c in sampler_mod.COMPONENTS}


def _service_version(sampler, ts: float) -> str | None:
    """The version the memory service named in the newest sample; None when the sample is stale or named none."""
    newest = sampler.latest() if sampler is not None else None
    if newest is None or ts - newest["ts"] > 2 * sampler_mod.SAMPLE_EVERY:
        return None
    return newest["version"]


def _measured(run: dict) -> tuple[int, int, int, int]:
    """Questions measured, came by themselves, found by search, both; a null (notes gone) is not measured."""
    pairs = [(a, s) for a, s in zip(run["auto"], run["search"]) if a is not None and s is not None]
    return (len(pairs), sum(bool(a) for a, _ in pairs), sum(bool(s) for _, s in pairs),
            sum(bool(a and s) for a, s in pairs))


def _check_totals(sampler) -> dict | None:
    runs = sampler.runs(limit=1) if sampler is not None else []
    if not runs:
        return None
    questions, auto, search, _ = _measured(runs[-1])
    return {"questions": questions, "auto": auto, "search": search}


def health(data_dir, now: dt.datetime, sampler) -> dict:
    """The state now, the last 30 days per component, the newest check runs and the numbers (1-based) of the
    questions the newest run missed by itself or by search. Questions appear by number only."""
    runs = sampler.runs()
    summary = {**_now_state(sampler, now.timestamp()), "questions": 0, "both": 0}
    missing: list[int] = []
    if runs:
        newest = runs[-1]
        summary["questions"], _, _, summary["both"] = _measured(newest)
        missing = [i + 1 for i, (a, s) in enumerate(zip(newest["auto"], newest["search"]))
                   if a is not None and s is not None and not (a and s)]
    return {"summary": summary, "days": sampler.days(now), "runs": runs, "missing": missing}


# ---------- notes ----------

ALWAYS_LOADED = [CORE, RULES, THREADS, SESSIONS]
CALENDAR_DAYS = 35


def _local_midnight(day: dt.date) -> float:
    return dt.datetime(day.year, day.month, day.day).timestamp()


def _calendar(store, today_: dt.date) -> list[dict]:
    first = today_ - dt.timedelta(days=CALENDAR_DAYS - 1)
    days = {first + dt.timedelta(days=i): {"changes": 0, "paths": set(), "added": 0} for i in range(CALENDAR_DAYS)}
    for c in reader.changes(store, _local_midnight(first)):
        day = dt.datetime.fromtimestamp(c["ts"]).date()
        if day not in days or _is_birth(c):
            continue
        days[day]["changes"] += 1
        days[day]["paths"].update(c["paths"])
        days[day]["added"] += len(c["added"])
    return [{"date": d.isoformat(), "changes": v["changes"], "notes": len(v["paths"]), "added": v["added"]}
            for d, v in days.items()]


def notes(data_dir, now: dt.datetime) -> dict:
    """How often each note was used, the notes never used, a calendar of the last 35 days of changes and the local
    date of the first recorded change (``first_change``, None without history)."""
    usage = _CACHE.get(data_dir, "usage", reader.usage_mark(data_dir), lambda: reader.note_usage(data_dir))
    with _memory(data_dir) as store:
        paths = [n["path"] for n in reader.note_list(store)]
        days = _calendar(store, now.astimezone().date())
        born = reader.first_change(store)
    used = [{"path": p, **usage[p]} for p in paths if p in usage and sum(usage[p].values())]
    used.sort(key=lambda u: (-(u["injected"] + u["read"] + u["found"]), u["path"]))
    in_use = {u["path"] for u in used}
    return {"since": reader.usage_since(data_dir), "total": len(paths), "ranking": used,
            "unused": [p for p in paths if p not in in_use], "always_loaded": list(ALWAYS_LOADED), "days": days,
            "first_change": dt.datetime.fromtimestamp(born).date().isoformat() if born is not None else None}


# ---------- map ----------

_HISTORY = (LOG_DIR, "sessions")


def _region(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return "cekirdek"
    if parts[0] in _HISTORY:
        return "gecmis"
    if parts[0] == "projects" and len(parts) > 2:
        return parts[1]
    return parts[0]


def _map_notes(store) -> dict:
    """The part of the map that only a commit changes: the notes, their links and regions."""
    listed = reader.note_list(store)
    links = reader.note_links(store)
    newest: dict[str, float] = {}
    for c in reader.changes(store, 0):  # newest first
        for p in c["paths"]:
            newest.setdefault(p, c["ts"])
    index = {n["path"]: i for i, n in enumerate(listed)}
    pairs = sorted({tuple(sorted((index[a], index[b]))) for a, targets in links.items() if a in index
                    for b in targets if b in index and a != b})
    counts: dict[str, int] = {}
    out = []
    for n in listed:
        region = _region(n["path"])
        counts[region] = counts.get(region, 0) + 1
        out.append({**n, "region": region, "changed": newest.get(n["path"])})
    return {"notes": out, "links": [list(p) for p in pairs],
            "regions": [{"id": r, "name": text_tr.REGIONS.get(r, r), "count": c} for r, c in sorted(counts.items())]}


def memory_map(data_dir, now: dt.datetime) -> dict:
    """Every note with its folder region and last change, the links between notes, and the notes of the newest
    message. The notes and links are kept until the vault's HEAD moves; the newest message is read every time."""
    with _memory(data_dir) as store:
        fixed = _CACHE.get(data_dir, "map", reader.vault_head(store), lambda: _map_notes(store))
    recent = next((e["paths"] for e in reader.events(data_dir, 0, limit=1, kind="inject")), [])
    return {**fixed, "recent": recent}


# ---------- releases ----------

def releases() -> dict:
    """The release history, the ring and what comes next: a data file kept by hand with every release."""
    return json.loads(resources.files("council.panel").joinpath("releases.json").read_text(encoding="utf-8"))

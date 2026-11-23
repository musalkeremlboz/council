"""What the panel records on its own: a health sample every SAMPLE_EVERY seconds and a check run when the notes
changed (or CHECK_EVERY passed). Both live in the panel's own file, ``panel.sqlite3``; nothing here writes to the
memory.

A sample holds 1, 0 or NULL per component (the memory service, the backup, the automatic update). A run holds,
per saved question in the order they are saved, two booleans (came by itself, found by search) or null for a
question whose notes are gone. The text of a question is matched in memory and never stored.
"""
from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import json
import logging
import math
import sqlite3
import time
import urllib.request
from contextlib import closing
from pathlib import Path

from .. import check
from ..local import _update_state
from ..store import BACKUP_GRACE
from . import reader

SAMPLE_EVERY = 900          # seconds
CHECK_EVERY = 3600
KEEP_DAYS = 400
PROBE_TIMEOUT = 3
MAX_HEALTH_BODY = 4096      # bytes of the health answer that are read
MAX_VERSION = 32            # longest version string that is stored
COMPONENTS = ("service", "backup", "updates")
log = logging.getLogger("council")
# The service sits on this machine: no proxy the system names may stand between, or a working service reads as down.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _open(url: str, timeout: float):
    return _OPENER.open(url, timeout=timeout)


def _version_in(body) -> str | None:
    """The ``version`` of a health answer when it is a short plain string; anything else is no version."""
    try:
        version = json.loads(body).get("version")
    except Exception:
        return None
    return version if isinstance(version, str) and 0 < len(version) <= MAX_VERSION and version.isprintable() else None


def probe_health(service_url: str) -> bool | str:
    """False when the memory service does not answer its health address with 200 within PROBE_TIMEOUT seconds.
    When it does: the version its answer names, or True when the answer names none. A probe returns False, True
    or a version string; a version string means "up, this version"."""
    try:
        with _open(service_url.rstrip("/") + "/health", timeout=PROBE_TIMEOUT) as r:
            if r.status != 200:
                return False
            try:
                return _version_in(r.read(MAX_HEALTH_BODY)) or True
            except Exception:  # up, but the body could not be read: no version
                return True
    except Exception:  # refused, timed out, an HTTP error status, a malformed answer: the service is down
        return False


def _finite(value) -> float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def state_of(values: list) -> str:
    """A day's state from its samples of one component."""
    known = [v for v in values if v is not None]
    if not known:
        return "none"
    if all(known):
        return "full"
    return "failed" if not any(known) else "partial"


class Sampler:
    def __init__(self, data_dir, service_url: str):
        self.data = Path(data_dir)
        self.service_url = service_url
        self.path = self.data / "panel.sqlite3"
        self.probe = probe_health  # probe(url) -> bool | version str; a test may put another one here
        with self._db() as db:
            db.execute("CREATE TABLE IF NOT EXISTS samples (ts REAL, service INTEGER, backup INTEGER, "
                       "updates INTEGER, version TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS runs (ts REAL, head TEXT, auto TEXT, search TEXT)")
            db.execute("CREATE INDEX IF NOT EXISTS samples_ts ON samples (ts)")
            db.execute("CREATE INDEX IF NOT EXISTS runs_ts ON runs (ts)")

    @contextlib.contextmanager
    def _db(self):
        """One connection per call, committed and closed on leaving: never shared between threads."""
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            yield db

    # ---------- samples ----------

    def _backup(self, now: float) -> int | None:
        state = reader.backup_state(self.data)
        if state is None:
            return None
        ok = _finite(state["last_ok"])
        if ok is not None and now - ok <= 2 * SAMPLE_EVERY:
            return 1
        return 1 if ok is not None and not state["failing"] and now - ok <= BACKUP_GRACE else 0

    def _updates(self) -> int | None:
        if not (self.data / "update.json").exists():
            return None
        state = _update_state(self.data)
        if not isinstance(state, dict):
            return None
        return 0 if state.get("error") else 1

    def sample(self, now: float | None = None, probe=None) -> dict:
        """Take one sample, store it and drop samples older than KEEP_DAYS."""
        now = time.time() if now is None else now
        probe = probe or self.probe
        try:
            answer = probe(self.service_url)
        except Exception:
            answer = False
        service = 1 if answer else 0
        version = answer if isinstance(answer, str) and 0 < len(answer) <= MAX_VERSION else None
        row = {"ts": now, "service": service, "backup": self._backup(now), "updates": self._updates()}
        with self._db() as db:
            db.execute("INSERT INTO samples (ts, service, backup, updates, version) VALUES (?, ?, ?, ?, ?)",
                       (now, row["service"], row["backup"], row["updates"], version))
            db.execute("DELETE FROM samples WHERE ts < ?", (now - KEEP_DAYS * 86400,))
        return row

    def latest(self) -> dict | None:
        with self._db() as db:
            r = db.execute("SELECT ts, service, backup, updates, version FROM samples "
                           "ORDER BY ts DESC LIMIT 1").fetchone()
        return dict(zip(("ts", *COMPONENTS, "version"), r)) if r else None

    def days(self, now: dt.datetime, count: int = 30) -> list[dict]:
        """The ``count`` local days ending with the one holding ``now``, oldest first, with a state per
        component."""
        last = now.astimezone().date()
        dates = [last - dt.timedelta(days=count - 1 - i) for i in range(count)]
        start = dt.datetime(dates[0].year, dates[0].month, dates[0].day).timestamp()
        end_day = last + dt.timedelta(days=1)
        end = dt.datetime(end_day.year, end_day.month, end_day.day).timestamp()
        with self._db() as db:
            rows = db.execute("SELECT ts, service, backup, updates FROM samples WHERE ts >= ? AND ts < ?",
                              (start, end)).fetchall()
        per: dict[dt.date, dict[str, list]] = {d: {c: [] for c in COMPONENTS} for d in dates}
        for ts, *values in rows:
            day = per.get(dt.datetime.fromtimestamp(ts).date())
            if day is not None:
                for c, v in zip(COMPONENTS, values):
                    day[c].append(v)
        return [{"date": d.isoformat(), **{c: state_of(per[d][c]) for c in COMPONENTS}} for d in dates]

    # ---------- check runs ----------

    def _results(self, store) -> tuple[list, list] | None:
        """Per saved question (in saved order) whether it came by itself and whether search found it; None and
        None for a question whose notes are gone. None when the file changed between the two reads."""
        asked = check.questions(store)
        report = check.search_report(store)
        gone = [g["question"] for g in report["gone"]]
        missed = [(m["question"], m["auto"], m["search"]) for m in report["missed"]]
        auto, search, g, m = [], [], 0, 0
        for q in asked:  # search_report walks the same list in the same order
            text = q["question"]
            if g < len(gone) and gone[g] == text:
                auto.append(None), search.append(None)
                g += 1
            elif m < len(missed) and missed[m][0] == text:
                auto.append(bool(missed[m][1])), search.append(bool(missed[m][2]))
                m += 1
            else:
                auto.append(True), search.append(True)
        if report["questions"] != len(asked) or g != len(gone) or m != len(missed):
            return None
        return auto, search

    def run_check(self, now: float | None = None, force: bool = False) -> bool:
        """Run the saved questions when the vault's HEAD moved since the last run, CHECK_EVERY passed, or
        ``force``; store the results and drop runs older than KEEP_DAYS. True when a run was stored."""
        now = time.time() if now is None else now
        store = reader.open_memory(self.data)
        try:
            head = reader.vault_head(store)
            with self._db() as db:
                last = db.execute("SELECT ts, head FROM runs ORDER BY ts DESC LIMIT 1").fetchone()
            if not force and last is not None and last[1] == head and now - last[0] < CHECK_EVERY:
                return False
            try:
                results = self._results(store)
            except check.CheckError:
                log.warning("panel: the saved questions could not be read; no check run stored")
                return False
        finally:
            store.index.db.close()
        if results is None or not results[0]:
            return False
        auto, search = results
        with self._db() as db:
            db.execute("INSERT INTO runs (ts, head, auto, search) VALUES (?, ?, ?, ?)",
                       (now, head, json.dumps(auto), json.dumps(search)))
            db.execute("DELETE FROM runs WHERE ts < ?", (now - KEEP_DAYS * 86400,))
        return True

    def runs(self, limit: int = 12) -> list[dict]:
        """The newest ``limit`` runs, oldest first."""
        with self._db() as db:
            rows = db.execute("SELECT ts, auto, search FROM runs ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for ts, auto, search in reversed(rows):
            try:
                out.append({"ts": ts, "auto": json.loads(auto), "search": json.loads(search)})
            except (TypeError, ValueError):
                continue
        return out

    # ---------- the loop ----------

    async def loop(self) -> None:
        """Sample, then check, every SAMPLE_EVERY seconds, off the event loop. Each failing step is logged on its
        own, so a failed sample does not skip the round's check; only cancellation ends the loop."""
        while True:
            for step, what in ((self.sample, "sample"), (self.run_check, "check")):
                try:
                    await asyncio.to_thread(step)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception("panel: a health %s failed", what)
            await asyncio.sleep(SAMPLE_EVERY)

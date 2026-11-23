"""Health: the samples the panel takes, the history of check runs, and the health view."""
import asyncio
import datetime as dt
import hashlib
import json
import sqlite3
import subprocess

import pytest
from conftest import SECRETS

from council import check
from council.panel import sampler as sampler_mod
from council.panel import views
from council.panel.sampler import SAMPLE_EVERY, Sampler
from council.store import Store

UP = lambda url: True  # noqa: E731
DOWN = lambda url: False  # noqa: E731


def midnight(day: dt.date) -> float:
    return dt.datetime(day.year, day.month, day.day).timestamp()


def local(ts: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(ts).astimezone()


def by_date(days):
    return {d["date"]: d for d in days}


def test_a_day_is_full_partial_failed_or_has_no_record(panel_data):
    s = Sampler(panel_data, "http://127.0.0.1:9")
    today = dt.date.today()
    days = [today - dt.timedelta(days=n) for n in (3, 2, 1, 0)]
    for probes, day in zip(((UP, UP), (UP, DOWN), (DOWN, DOWN), ()), days):
        for i, probe in enumerate(probes):
            s.sample(now=midnight(day) + 3600 * (i + 1), probe=probe)
    got = by_date(s.days(local(midnight(today) + 7200)))
    assert [got[d.isoformat()]["service"] for d in days] == ["full", "partial", "failed", "none"]
    assert len(s.days(local(midnight(today) + 7200))) == 30


def test_a_day_follows_local_time(panel_data):
    s = Sampler(panel_data, "http://127.0.0.1:9")
    today = dt.date.today()
    s.sample(now=midnight(today) + 1800, probe=DOWN)
    s.sample(now=midnight(today) - 1800, probe=UP)
    got = by_date(s.days(local(midnight(today) + 3600)))
    assert got[today.isoformat()]["service"] == "failed"
    assert got[(today - dt.timedelta(days=1)).isoformat()]["service"] == "full"


def _write_and_commit(data):
    store = Store(data)
    try:
        store.write("projects/ev/yeni.md", "# Yeni\n\nyeni bir not\n")
    finally:
        store.index.db.close()


def test_a_check_runs_when_the_notes_changed_and_stores_no_question_text(leaky):
    s = Sampler(leaky, "http://127.0.0.1:9")
    assert s.run_check(force=True) is True
    runs = s.runs()
    assert len(runs) == 1 and runs[0]["auto"] == [True] and runs[0]["search"] == [True]
    raw = (leaky / "panel.sqlite3").read_bytes()
    assert not [x for x in SECRETS if x.encode() in raw]
    assert s.run_check() is False
    _write_and_commit(leaky)
    assert s.run_check() is True
    assert len(s.runs()) == 2


def test_a_check_runs_again_after_check_every(leaky):
    s = Sampler(leaky, "http://127.0.0.1:9")
    t = 2_000_000_000.0
    assert s.run_check(now=t) is True
    assert s.run_check(now=t + sampler_mod.CHECK_EVERY - 1) is False
    assert s.run_check(now=t + sampler_mod.CHECK_EVERY) is True


def _files(data):
    vault = data / "vault"
    head = (vault / ".git" / "HEAD").read_text()
    paths = [vault / ".git" / "HEAD", vault / ".git" / head.split(":", 1)[1].strip()] if head.startswith("ref:") \
        else [vault / ".git" / "HEAD"]
    paths += [data / name for name in ("index.sqlite3", "usage.sqlite3", "index.sqlite3-wal", "usage.sqlite3-wal")]
    out = {}
    for p in paths:
        if p.exists():
            st = p.stat()
            out[p.name] = (st.st_mtime_ns, st.st_size, hashlib.sha256(p.read_bytes()).hexdigest())
    rev = subprocess.run(["git", "-C", str(vault), "rev-parse", "HEAD"], capture_output=True, text=True).stdout
    return out, rev


def test_a_check_writes_nothing_to_the_memory(leaky):
    before = _files(leaky)
    s = Sampler(leaky, "http://127.0.0.1:9")
    usage_rows = sqlite3.connect(leaky / "usage.sqlite3").execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert s.run_check(force=True) is True
    assert _files(leaky) == before
    assert sqlite3.connect(leaky / "usage.sqlite3").execute("SELECT COUNT(*) FROM events").fetchone()[0] == usage_rows


def _two_questions(data):
    """The first question finds its note both ways; the second one's words are in no note."""
    store = Store(data)
    try:
        store.write("projects/ev/kira.md", "# Kira\n\nKira her ayın yirmi beşinde ödenir.\n")
        store.write("projects/ev/su.md", "# Su\n\nSu faturası\n")
        check.add_question(store, "kira ne zaman ödenir", ["projects/ev/kira.md"])
        check.add_question(store, "zzzz qqqq hiç geçmeyen sözcükler", ["projects/ev/su.md"])
    finally:
        store.index.db.close()


def test_health_names_the_questions_missed_by_number(panel_data):
    _two_questions(panel_data)
    s = Sampler(panel_data, "http://127.0.0.1:9")
    assert s.run_check(force=True)
    run = s.runs()[-1]
    assert run["search"] == [True, False]
    data = views.health(panel_data, dt.datetime.now().astimezone(), s)
    assert data["missing"] == [2]
    assert data["summary"]["questions"] == 2 and data["summary"]["both"] == 1
    assert data["runs"] == s.runs() and len(data["days"]) == 30
    assert "kira" not in json.dumps(data) and "zzzz" not in json.dumps(data)


def test_a_question_whose_notes_are_gone_is_stored_as_null(panel_data):
    _two_questions(panel_data)
    qfile = panel_data / check.QUESTIONS_FILE
    asked = json.loads(qfile.read_text(encoding="utf-8"))
    asked.insert(0, {"question": "silinmiş not sorusu", "expect": ["projects/yok.md"], "added": "2026-11-22"})
    qfile.write_text(json.dumps(asked, ensure_ascii=False), encoding="utf-8")
    s = Sampler(panel_data, "http://127.0.0.1:9")
    assert s.run_check(force=True)
    run = s.runs()[-1]
    assert run["auto"][0] is None and run["search"] == [None, True, False]
    data = views.health(panel_data, dt.datetime.now().astimezone(), s)
    assert data["missing"] == [3] and data["summary"]["questions"] == 2


def test_no_backup_configured_is_no_record_not_a_failure(panel_data):
    s = Sampler(panel_data, "http://127.0.0.1:9")
    row = s.sample(probe=UP)
    assert row["backup"] is None
    assert s.days(dt.datetime.now().astimezone())[-1]["backup"] == "none"
    assert views.health(panel_data, dt.datetime.now().astimezone(), s)["summary"]["backup"] == "none"


def test_the_backup_sample_follows_the_backup_record(panel_data):
    s = Sampler(panel_data, "http://127.0.0.1:9")
    now = 2_000_000_000.0
    cases = [({"last_ok": now - 60, "error": "x"}, 1),            # a success in the last two sampling periods
             ({"last_ok": now - 86400, "error": ""}, 1),           # no failure and a success within the grace
             ({"last_ok": now - 86400, "error": "push failed"}, 0),
             ({"last_ok": now - 3 * 86400, "error": ""}, 0),
             ({"last_ok": float("nan"), "error": ""}, 0),
             ({"error": ""}, 0)]
    for record, want in cases:
        (panel_data / "backup.json").write_text(json.dumps(record))
        assert s.sample(now=now, probe=UP)["backup"] == want, record


def test_the_update_sample_follows_the_update_state(panel_data):
    s = Sampler(panel_data, "http://127.0.0.1:9")
    assert s.sample(probe=UP)["updates"] is None
    (panel_data / "update.json").write_text(json.dumps({"checked": 1.0}))
    assert s.sample(probe=UP)["updates"] == 1
    (panel_data / "update.json").write_text(json.dumps({"checked": 1.0, "error": "could not read"}))
    assert s.sample(probe=UP)["updates"] == 0


def test_old_samples_and_runs_are_pruned(leaky):
    s = Sampler(leaky, "http://127.0.0.1:9")
    old = 1_000_000_000.0
    s.sample(now=old, probe=UP)
    s.run_check(now=old, force=True)
    later = old + (sampler_mod.KEEP_DAYS + 1) * 86400
    s.sample(now=later, probe=UP)
    s.run_check(now=later, force=True)
    db = sqlite3.connect(leaky / "panel.sqlite3")
    assert [r[0] for r in db.execute("SELECT ts FROM samples")] == [later]
    assert [r[0] for r in db.execute("SELECT ts FROM runs")] == [later]
    assert db.execute("SELECT version FROM samples").fetchone() == (None,)


def test_the_loop_survives_a_failing_probe(panel_data):
    def broken(url):
        raise OSError("refused")

    s = Sampler(panel_data, "http://127.0.0.1:9")
    s.probe = broken

    async def go():
        task = asyncio.create_task(s.loop())
        for _ in range(500):
            if s.latest():
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):  # it ends by its cancellation and by nothing else
            await task

    asyncio.run(go())
    assert s.latest()["service"] == 0


def test_the_loop_keeps_going_when_a_round_fails(panel_data, monkeypatch):
    monkeypatch.setattr(sampler_mod, "SAMPLE_EVERY", 0)
    s = Sampler(panel_data, "http://127.0.0.1:9")
    calls, checks = [], []

    def flaky(now=None, probe=None):
        calls.append(1)
        raise sqlite3.OperationalError("database is locked")

    s.sample = flaky
    s.run_check = lambda: checks.append(1)  # a failing sample does not skip the round's check

    async def go():
        task = asyncio.create_task(s.loop())
        for _ in range(500):
            if len(calls) >= 3:
                break
            await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(go())
    assert len(calls) >= 3 and len(checks) >= len(calls) - 1


def test_the_probe_asks_the_service_health(monkeypatch):
    seen = {}

    class Answer:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake(url, timeout):
        seen["url"], seen["timeout"] = url, timeout
        return Answer()

    monkeypatch.setattr(sampler_mod, "_open", fake)
    assert sampler_mod.probe_health("http://127.0.0.1:8765") is True
    assert seen == {"url": "http://127.0.0.1:8765/health", "timeout": 3}

    def refuse(url, timeout):
        raise OSError("refused")

    monkeypatch.setattr(sampler_mod, "_open", refuse)
    assert sampler_mod.probe_health("http://127.0.0.1:8765") is False


def test_a_stale_newest_sample_is_no_record(panel_data):
    s = Sampler(panel_data, "http://127.0.0.1:9")
    now = dt.datetime.now().astimezone()
    s.sample(now=now.timestamp() - 3 * SAMPLE_EVERY, probe=UP)
    assert views.health(panel_data, now, s)["summary"]["service"] == "none"
    s.sample(now=now.timestamp() - 60, probe=UP)
    assert views.health(panel_data, now, s)["summary"]["service"] == "full"


def test_the_schema_status_carries_the_service_and_the_check(leaky):
    s = Sampler(leaky, "http://127.0.0.1:9")
    now = dt.datetime.now().astimezone()
    status = views.schema(leaky, now, s)["status"]
    assert status["service"] == "none" and status["check"] is None
    s.sample(probe=UP)
    s.run_check(force=True)
    status = views.schema(leaky, now, s)["status"]
    assert status["service"] == "full" and status["check"] == {"questions": 1, "auto": 1, "search": 1}


def test_the_health_address_answers_with_the_sampler_of_the_app(leaky_panel):
    sampler = leaky_panel.app.state.sampler
    sampler.sample(probe=UP)
    sampler.run_check(force=True)
    data = leaky_panel.get("/panel/api/health").json()
    assert data["summary"]["service"] == "full" and data["runs"][0]["auto"] == [True]
    assert leaky_panel.get("/panel/api/schema").json()["status"]["check"]["questions"] == 1


def test_a_background_app_starts_and_stops_its_loop(panel_data, monkeypatch):
    from starlette.testclient import TestClient

    from council.panel.app import build

    started = []

    async def fake_loop(self):
        started.append(1)
        await asyncio.sleep(3600)

    monkeypatch.setattr(Sampler, "loop", fake_loop)
    app = build(panel_data)
    try:
        with TestClient(app, base_url="http://127.0.0.1:8766"):
            assert started == [1]
    finally:
        app.state.gate.close()


def test_the_probe_goes_straight_to_the_service_whatever_proxy_the_system_names(monkeypatch):
    import http.server
    import threading

    class Health(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path == "/health" else 404)
            self.end_headers()
            self.wfile.write(b'{"version": "1.2.3"}')

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Health)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for name in ("http_proxy", "HTTP_PROXY"):
            monkeypatch.setenv(name, "http://127.0.0.1:9")  # nothing listens there
        for name in ("no_proxy", "NO_PROXY"):
            monkeypatch.delenv(name, raising=False)
        assert sampler_mod.probe_health(f"http://127.0.0.1:{server.server_port}") == "1.2.3"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_the_panel_file_indexes_the_times(panel_data):
    import contextlib

    Sampler(panel_data, "http://127.0.0.1:9")
    with contextlib.closing(sqlite3.connect(panel_data / "panel.sqlite3")) as db:
        indexed = {r[0] for r in db.execute("SELECT tbl_name FROM sqlite_master WHERE type = 'index' AND sql LIKE '%(ts)%'")}
    assert indexed == {"samples", "runs"}

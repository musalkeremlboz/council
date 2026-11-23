import datetime as dt
import hashlib
import sys
import time
from pathlib import Path

import pytest
from conftest import ODD_FOLDER, remove_history

from council import context
from council.panel import text_tr, views
from council.store import Store
from council.usage import Usage

PLAN = f"projects/{ODD_FOLDER}/plan.md"


def record(data, rows):
    """Usage events as (kind, chars, paths, ts) rows."""
    usage = Usage(data / "usage.sqlite3")
    try:
        for kind, chars, paths, ts in rows:
            usage.record(kind, "s1", "MESAJ-SIRRI", chars, None, [{"path": p, "heading": "BASLIK-SIRRI"} for p in paths], ts=ts)
    finally:
        usage.db.close()


def snapshot(data):
    return {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(data.rglob("*")) if p.is_file() and ".git/" not in p.as_posix()}


def newest(events, kind):
    return next(e for e in events if e["kind"] == kind)


def test_an_inject_event_lights_its_blocks_and_lists_paths_only(leaky):
    event = newest(views.schema(leaky, dt.datetime.now().astimezone())["events"], "inject")
    assert event["path"] == ["h2", "ara", "sec", "haf"] and event["memory"] == "read"
    text = str(event["steps"])
    assert "projects/ev/kaynak.md" in text and PLAN in text
    assert "BASLIK-SIRRI" not in text and "MESAJ-SIRRI" not in text
    assert {s["block"] for s in event["steps"]} == {"h2", "ara", "sec", "haf"}
    chosen = next(s for s in event["steps"] if s["block"] == "sec")
    assert "not" in chosen["text"] and "bölüm" not in chosen["text"] and chosen["value"].startswith("2 not")


def test_an_inject_that_found_nothing_stops_before_the_memory(leaky):
    record(leaky, [("inject", 0, [], time.time())])
    event = views.schema(leaky, dt.datetime.now().astimezone())["events"][0]
    assert event["kind"] == "inject" and event["path"] == ["h2", "ara", "sec"] and event["memory"] == ""


def test_a_pointer_in_the_same_second_lights_the_pointer_block(leaky):
    base = int(time.time()) + 5
    record(leaky, [("inject", 200, ["projects/ev/kaynak.md"], base + 0.2),
                   ("pointer", 60, ["skills/kira-odeme.md"], base + 0.4)])
    events = views.schema(leaky, dt.datetime.now().astimezone())["events"]
    inject = events[0]
    assert inject["kind"] == "inject" and inject["path"] == ["h2", "ara", "sec", "haf", "isa"]
    assert "skills/kira-odeme.md" in str(inject["steps"])
    assert all(e["kind"] != "pointer" for e in events)


def test_the_kinds_light_their_blocks(leaky):
    t = time.time() + 5
    record(leaky, [("start", 10, [], t), ("context", 10, [], t + 1), ("read", 5, ["core.md"], t + 2),
                   ("open", 0, ["skills/kira-odeme.md"], t + 3), ("search", 5, ["core.md"], t + 4)])
    by_kind = {e["kind"]: e for e in views.schema(leaky, dt.datetime.now().astimezone())["events"]}
    assert by_kind["start"]["path"] == ["h1", "bas", "diz", "haf"]
    assert by_kind["context"]["path"] == ["bas", "diz", "haf"]
    for kind in ("read", "open", "search"):
        assert by_kind[kind]["path"] == ["haf"] and by_kind[kind]["memory"] == "read"
    assert by_kind["start"]["memory"] == "read"


def test_writes_come_from_the_history_of_the_notes(leaky):
    store = Store(leaky)
    try:
        store.upsert_session("sess1234", "KART-ETIKETI", "body")
        store.append_log("ozet", ["core.md"], session_id="sess1234")
    finally:
        store.index.db.close()
    events = views.schema(leaky, dt.datetime.now().astimezone())["events"]
    for kind in ("card", "log"):
        event = newest(events, kind)
        assert event["path"] == ["h3", "yaz", "haf"] and event["memory"] == "written"
    assert newest(events, "log")["steps"][-1]["value"].count("log/") == 1
    assert "KART-ETIKETI" not in str(events) and "ozet" not in str(events)
    learned = {e["kind"] for e in events if e["path"] == ["h3", "ogr", "haf"]}
    assert learned == {"rule", "skill"}  # the skill and the rule of the fixture


def test_a_learning_and_its_commit_are_one_event(leaky):
    events = views.schema(leaky, dt.datetime.now().astimezone())["events"]
    assert sum(e["kind"] == "skill" for e in events) == 1 and sum(e["kind"] == "rule" for e in events) == 1


def test_the_birth_of_the_memory_is_not_an_event(panel_data):
    assert views.schema(panel_data, dt.datetime.now().astimezone())["events"] == []


def test_at_limit_is_the_last_two_hundred_characters(leaky):
    assert not views.AT_LIMIT(3299) and views.AT_LIMIT(3300) and views.AT_LIMIT(3527)
    now = dt.datetime(2026, 6, 15, 12, 0).astimezone()
    t = now.timestamp()
    record(leaky, [("inject", 3299, [], t - 50), ("inject", 3300, [], t - 40), ("inject", 3527, [], t - 30),
                   ("read", 4000, ["core.md"], t - 20)])
    today = views.today(leaky, now)
    assert today["at_limit"] == 2
    assert [e["at_limit"] for e in today["events"] if e["lane"] == "inject"] == [False, True, True]
    assert today["counts"]["inject"] == 3 and today["counts"]["read"] == 1
    assert today["lanes"] == ["start", "inject", "read", "search", "open", "pointer"]


@pytest.fixture
def zone(monkeypatch):
    if not hasattr(time, "tzset"):
        pytest.skip("no time.tzset on this system")
    monkeypatch.setenv("TZ", "Etc/GMT-3")  # UTC+3 all year
    time.tzset()
    yield dt.timezone(dt.timedelta(hours=3))
    monkeypatch.undo()
    time.tzset()


def test_today_is_the_local_day(panel_data, zone):
    now = dt.datetime(2026, 3, 10, 12, 0, tzinfo=zone)
    midnight = dt.datetime(2026, 3, 10, tzinfo=zone).timestamp()
    assert midnight % 86400 != 0  # local midnight is not UTC midnight
    record(panel_data, [("read", 1, [], midnight - 3600), ("read", 2, [], midnight + 3600),
                        ("context", 3, [], midnight + 7200)])
    today = views.today(panel_data, now)
    assert today["date"] == "2026-03-10" and today["now_minute"] == 720
    assert [(e["minute"], e["lane"], e["chars"]) for e in today["events"]] == [(60, "read", 2), (120, "start", 3)]


def test_the_start_budget_names_what_did_not_fit(tmp_path, monkeypatch):
    data = tmp_path / "data"
    store = Store(data)
    try:
        for i in range(3):
            store.upsert_session(f"sess{i}", f"kart {i}", "x" * 400)
    finally:
        store.index.db.close()
    monkeypatch.setattr(context, "START_BUDGET", 1100)
    budget = views.today(data, dt.datetime.now().astimezone())["budgets"]
    start = budget["start"]
    assert start["budget"] == 1100 and start["left_out"]
    assert {"name": "oturum kartı", "chars": start["left_out"][0]["chars"]} in start["left_out"]
    assert start["left_out"][0]["chars"] > 400
    assert len(start["parts"]) == 4 and sum(p["chars"] for p in start["parts"]) <= 1100
    assert budget["message"] == {"budget": context.MESSAGE_BUDGET, "min_room": context.MIN_ROOM}
    assert set(budget["index"]) == {"budget", "chars", "listed", "left_out"}


def test_the_numbers_are_live_lines_without_text(leaky):
    schema = views.schema(leaky, dt.datetime.now().astimezone())
    assert set(schema["numbers"]) == {b["id"] for b in schema["blocks"]}
    assert schema["status"]["notes"] >= 5 and schema["status"]["skills"] == 1
    assert schema["status"]["backup_last_ok"] and schema["status"]["backup_failing"] is False
    assert schema["numbers"]["den"] and schema["numbers"]["yed"] and schema["numbers"]["bas"]


def test_a_memory_without_a_backup_says_so(panel_data):
    schema = views.schema(panel_data, dt.datetime.now().astimezone())
    assert any("kayıt yok" in line for line in schema["numbers"]["yed"])
    assert schema["status"]["backup_last_ok"] is None


def everything(data):
    """Every file under the data folder, the vault's .git included, except the panel's own file."""
    return {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(data.rglob("*")) if p.is_file() and not p.name.startswith("panel.sqlite3")}


def test_the_panel_writes_nothing_but_its_own_file(leaky_panel, leaky):
    from council.panel.app import SECTIONS

    sampler = leaky_panel.app.state.sampler
    before = everything(leaky)
    assert ".git/HEAD" in str(before) and "usage.sqlite3" in before
    now = dt.datetime.now().astimezone()
    views.schema(leaky, now)
    views.today(leaky, now)
    for section in SECTIONS:
        assert "error" not in leaky_panel.get(f"/panel/api/{section}").json(), section
    sampler.sample(probe=lambda url: True)
    assert sampler.run_check(force=True)
    for section in SECTIONS:  # once more, now with a sample and a check run behind them
        leaky_panel.get(f"/panel/api/{section}")
    assert everything(leaky) == before


def test_an_empty_memory_gives_empty_sections_not_an_error(panel_data, panel_signed_in):
    now = dt.datetime.now().astimezone()
    assert views.schema(panel_data, now)["events"] == [] and views.today(panel_data, now)["events"] == []
    for section in ("schema", "today"):
        r = panel_signed_in.get(f"/panel/api/{section}")
        assert r.status_code == 200 and r.json()["events"] == []


def test_a_section_that_fails_answers_unavailable_not_500(panel_signed_in, monkeypatch, caplog):
    def boom(*args):
        raise RuntimeError("boom")

    monkeypatch.setattr(views, "schema", boom)
    r = panel_signed_in.get("/panel/api/schema")
    assert r.status_code == 200 and r.json() == {"error": "unavailable"}
    assert "boom" in caplog.text
    assert "summary" in panel_signed_in.get("/panel/api/health").json()  # the other sections still answer


# ---------- notes, map, releases ----------

def test_the_ranking_puts_the_most_used_note_first_and_lists_the_unused(panel_data):
    store = Store(panel_data)
    try:
        for p in ("a.md", "b.md", "c.md", "d.md"):
            store.write(p, "# T\n")
    finally:
        store.index.db.close()
    t = time.time() - 100
    record(panel_data, [("inject", 5, ["b.md"], t), ("inject", 5, ["b.md", "a.md"], t + 1),
                        ("read", 5, ["b.md"], t + 2), ("search", 5, ["c.md", "a.md"], t + 3)])
    notes = views.notes(panel_data, dt.datetime.now().astimezone())
    assert notes["ranking"] == [{"path": "b.md", "injected": 2, "read": 1, "found": 0},
                                {"path": "a.md", "injected": 1, "read": 0, "found": 1},
                                {"path": "c.md", "injected": 0, "read": 0, "found": 1}]
    assert notes["unused"] == ["core.md", "d.md", "rules.md", "sessions.md", "threads.md"]
    assert notes["total"] == 8 and notes["since"] == pytest.approx(t, abs=1)
    assert notes["always_loaded"] == ["core.md", "rules.md", "threads.md", "sessions.md"]


def test_usage_counts_are_not_capped_at_five_hundred_events(panel_data):
    t = time.time() - 5000
    record(panel_data, [("inject", 1, ["core.md"], t + i) for i in range(600)])
    notes = views.notes(panel_data, dt.datetime.now().astimezone())
    assert notes["ranking"] == [{"path": "core.md", "injected": 600, "read": 0, "found": 0}]


def test_days_follow_the_history_and_days_without_change_are_zero(leaky):
    now = dt.datetime.now().astimezone()
    days = views.notes(leaky, now)["days"]
    assert len(days) == 35 and days[-1]["date"] == now.date().isoformat()
    assert [d["date"] for d in days] == sorted(d["date"] for d in days)
    assert days[-1]["changes"] > 0 and days[-1]["notes"] > 0 and days[-1]["added"] > 0
    assert all(d == {"date": d["date"], "changes": 0, "notes": 0, "added": 0} for d in days[:-1])
    later = views.notes(leaky, now + dt.timedelta(days=10))["days"]
    assert later[-11]["changes"] == days[-1]["changes"]
    assert all(d["changes"] == 0 for d in later[-10:])


def test_the_first_recorded_change_is_dated_even_before_the_window(leaky):
    now = dt.datetime.now().astimezone()
    born = views.notes(leaky, now)["first_change"]
    assert born == now.date().isoformat()
    later = views.notes(leaky, now + dt.timedelta(days=60))
    assert later["first_change"] == born and born < later["days"][0]["date"]


def test_a_memory_without_history_has_no_first_change(panel_data):
    import subprocess

    vault = panel_data / "vault"
    remove_history(vault)
    subprocess.run(["git", "-C", str(vault), "init", "-q"], check=True)
    notes = views.notes(panel_data, dt.datetime.now().astimezone())
    assert notes["first_change"] is None
    assert all(d["changes"] == 0 for d in notes["days"])


def test_the_map_groups_notes_by_folder_and_links_each_pair_once(leaky):
    m = views.memory_map(leaky, dt.datetime.now().astimezone())
    paths = [n["path"] for n in m["notes"]]
    region = {n["path"]: n["region"] for n in m["notes"]}
    assert region["core.md"] == "cekirdek" and region["projects/ev/kaynak.md"] == "ev"
    assert region[f"projects/{ODD_FOLDER}/plan.md"] == ODD_FOLDER
    assert region["skills/kira-odeme.md"] == "skills"
    assert {n["path"]: n["skill"] for n in m["notes"]}["skills/kira-odeme.md"] is True
    names = {r["id"]: r for r in m["regions"]}
    assert names["cekirdek"]["name"] == "Çekirdek" and names["skills"]["name"] == "İş tarifleri"
    assert names["ev"] == {"id": "ev", "name": "ev", "count": 2}
    assert sum(r["count"] for r in m["regions"]) == len(paths)
    pairs = {tuple(sorted((paths[i], paths[j]))) for i, j in m["links"]}
    assert pairs == {("projects/ev/baglanti.md", "projects/ev/kaynak.md")}
    assert len(m["links"]) == 1 and m["links"][0][0] < m["links"][0][1]
    assert all(n["changed"] is not None for n in m["notes"] if n["path"].startswith("projects/ev/"))


def test_history_folders_are_one_region(panel_data):
    store = Store(panel_data)
    try:
        store.write("log/2026-11.md", "# L\n")
        store.write("sessions/x.md", "# S\n")
    finally:
        store.index.db.close()
    m = views.memory_map(panel_data, dt.datetime.now().astimezone())
    region = {n["path"]: n["region"] for n in m["notes"]}
    assert region["log/2026-11.md"] == region["sessions/x.md"] == "gecmis"
    assert {r["id"]: r["name"] for r in m["regions"]}["gecmis"] == "Geçmiş"


def test_the_recent_notes_are_those_of_the_newest_message(leaky):
    t = time.time() + 5
    record(leaky, [("inject", 5, ["core.md"], t), ("read", 5, ["rules.md"], t + 1),
                   ("inject", 5, ["threads.md", "rules.md"], t + 2)])
    m = views.memory_map(leaky, dt.datetime.now().astimezone())
    assert m["recent"] == ["threads.md", "rules.md"]


def test_releases_has_six_ring_parts_four_versions_and_seven_next_items():
    r = views.releases()
    assert [p["n"] for p in r["ring"]] == [1, 2, 3, 4, 5, 6]
    assert r["ring"][0] == {"n": 1, "name": "Hafıza", "state": "full"}
    assert r["ring"][1] == {"n": 2, "name": "İşlerden öğrenme", "state": "measured"}
    assert all(p["state"] == "waiting" for p in r["ring"][2:])
    assert [v["version"] for v in r["versions"]] == ["0.3.0", "0.2.1", "0.2.0", "0.1.0"]
    assert len({v["version"] for v in r["versions"]}) == 4
    assert [v["state"] for v in r["versions"]] == ["pending", "released", "released", "first"]
    assert all(v["summary"] and v["added"] for v in r["versions"])
    assert len(r["next"]) == 7
    assert all(n["title"] and n["text"] and n["waits_for"] for n in r["next"])


def test_the_three_addresses_are_served(leaky_panel):
    for name in ("notes", "map", "releases"):
        body = leaky_panel.get(f"/panel/api/{name}").json()
        assert "section" not in body and "error" not in body
    assert "ranking" in leaky_panel.get("/panel/api/notes").json()
    assert "regions" in leaky_panel.get("/panel/api/map").json()


def test_the_recent_notes_survive_many_newer_events_of_other_kinds(leaky):
    t = time.time() + 5
    record(leaky, [("inject", 5, ["threads.md"], t)] + [("read", 1, ["core.md"], t + 1 + i) for i in range(600)])
    assert views.memory_map(leaky, dt.datetime.now().astimezone())["recent"] == ["threads.md"]


def test_the_status_names_both_versions_and_says_when_they_differ(leaky):
    from council import __version__
    from council.panel.sampler import SAMPLE_EVERY, Sampler

    s = Sampler(leaky, "http://127.0.0.1:9")
    now = dt.datetime.now().astimezone()
    status = views.schema(leaky, now, s)["status"]
    assert status["panel_version"] == __version__ and status["service_version"] is None  # no sample yet
    s.sample(probe=lambda url: True)  # up, but the answer named no version: nothing is invented
    assert views.schema(leaky, now, s)["status"]["service_version"] is None
    s.sample(probe=lambda url: "9.9.9")
    status = views.schema(leaky, now, s)["status"]
    assert status["service_version"] == "9.9.9" and status["panel_version"] == __version__
    later = now + dt.timedelta(seconds=3 * SAMPLE_EVERY)  # a stale sample names no version
    assert views.schema(leaky, later, s)["status"]["service_version"] is None
    assert views.schema(leaky, now)["status"]["service_version"] is None  # no sampler
    assert "farklı sürümde" in text_tr.ui()["status_version_differs"]


def test_the_probe_reads_the_version_from_the_health_answer(monkeypatch):
    from council.panel import sampler as sampler_mod

    def answer(body, status=200):
        class A:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self, n=-1):
                return body

        A.status = status
        return lambda url, timeout: A()

    for body, want in ((b'{"ok": true, "version": "0.2.1"}', "0.2.1"), (b'{"ok": true}', True), (b"not json", True),
                       (b'{"version": 5}', True), (b'{"version": "' + b"x" * 40 + b'"}', True)):
        monkeypatch.setattr(sampler_mod, "_open", answer(body))
        assert sampler_mod.probe_health("http://127.0.0.1:8765") == want
        assert type(sampler_mod.probe_health("http://127.0.0.1:8765")) is type(want)


DEPLOY = Path(__file__).resolve().parent.parent / "deploy"


def test_the_panel_service_file_runs_the_panel_after_the_memory_service():
    unit = (DEPLOY / "council-panel.service").read_text()
    assert ("ExecStart=/opt/council/.venv/bin/council panel --host 127.0.0.1 --port 8766 --base-path /panel\n"
            in unit)
    assert "After=council.service\n" in unit
    assert "Restart=on-failure" in unit
    assert "RestartPreventExitStatus=2\n" in unit  # the command exits 2 when no owner password is set
    main = (DEPLOY / "council.service").read_text()
    for line in main.splitlines():  # the hardening and environment lines are copied as they are
        if line.startswith(("Environment=", "NoNewPrivileges", "ProtectSystem", "ProtectHome", "ReadWritePaths",
                            "PrivateTmp")):
            assert line in unit.splitlines()


def test_the_caddyfile_sends_the_panel_to_its_port_before_the_memory_service():
    text = (DEPLOY / "Caddyfile").read_text()
    assert "\t@panel path /panel /panel/*\n" in text and "/panel*" not in text  # not /panelfoo
    panel = text.index("handle @panel {")
    assert text.index("reverse_proxy 127.0.0.1:8766") > panel
    assert text.index("reverse_proxy 127.0.0.1:8765") > text.index("reverse_proxy 127.0.0.1:8766")
    assert text.count("reverse_proxy") == 2


# ---------- counts that are true at any size, and the cost of a poll ----------

def test_the_numbers_count_every_event_of_the_last_day_not_the_newest_five_hundred(panel_data):
    t = time.time() - 3600
    record(panel_data, [("inject", 100 if i % 3 else 0, ["core.md"], t + i) for i in range(750)]
           + [("pointer", 5, ["skills/a.md", "skills/b.md"], t + 0.5 + i) for i in range(260)]
           + [("open", 0, ["skills/a.md"], t + 0.7 + i) for i in range(520)])
    numbers = views.schema(panel_data, dt.datetime.now().astimezone())["numbers"]
    assert numbers["h2"] == [text_tr.NUMBERS["h2_messages"].format(n=750)]
    assert numbers["sec"] == [text_tr.NUMBERS["sec_given"].format(n=500), text_tr.NUMBERS["sec_mean"].format(n=100)]
    assert numbers["isa"] == [text_tr.NUMBERS["isa_pointers"].format(n=520), text_tr.NUMBERS["isa_opened"].format(n=520)]


def test_today_counts_and_draws_only_the_messages_that_got_notes(panel_data):
    now = dt.datetime(2026, 6, 15, 12, 0).astimezone()
    t = now.timestamp()
    record(panel_data, [("inject", 0, [], t - 50), ("inject", 120, ["core.md"], t - 40), ("inject", 0, [], t - 30),
                        ("inject", 3400, ["core.md"], t - 20)])
    today = views.today(panel_data, now)
    assert today["counts"]["inject"] == 2
    assert [e["chars"] for e in today["events"] if e["lane"] == "inject"] == [120, 3400]
    assert today["at_limit"] == 1
    schema = views.schema(panel_data, now)["numbers"]
    assert schema["sec"][0] == text_tr.NUMBERS["sec_given"].format(n=today["counts"]["inject"])


def test_changes_of_the_week_leave_out_the_birth_of_the_memory(panel_data):
    numbers = views.schema(panel_data, dt.datetime.now().astimezone())["numbers"]
    assert text_tr.NUMBERS["haf_changes"].format(n=0) in numbers["haf"]
    store = Store(panel_data)
    try:
        store.write("a.md", "# A\n")
    finally:
        store.index.db.close()
    numbers = views.schema(panel_data, dt.datetime.now().astimezone())["numbers"]
    assert text_tr.NUMBERS["haf_changes"].format(n=1) in numbers["haf"]


def test_a_schema_request_builds_the_skill_index_once_and_reads_no_note_to_count_notes(leaky, monkeypatch):
    from council.panel import reader

    built, listed = [], []
    index = views.context.skills_index
    monkeypatch.setattr(views.context, "skills_index", lambda *a, **k: built.append(1) or index(*a, **k))
    monkeypatch.setattr(reader, "note_list", lambda store: listed.append(1) or [])
    views.schema(leaky, dt.datetime.now().astimezone())
    assert len(built) == 1 and listed == []


def _uncached_map(data, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(views, "_CACHE", views._Cache())
        return views.memory_map(data, dt.datetime.now().astimezone())


def test_the_map_is_cached_by_the_head_of_the_notes_and_its_recent_part_stays_live(leaky, monkeypatch):
    from council.panel import reader

    now = dt.datetime.now().astimezone()
    first = views.memory_map(leaky, now)
    assert views.memory_map(leaky, now) == first == _uncached_map(leaky, monkeypatch)
    record(leaky, [("inject", 5, ["threads.md"], time.time() + 5)])
    assert views.memory_map(leaky, now)["recent"] == ["threads.md"]  # no commit, still fresh
    store = Store(leaky)
    try:
        store.write("projects/ev/yeni.md", "# Yeni\n\nSee [[kaynak]].\n")
    finally:
        store.index.db.close()
    after = views.memory_map(leaky, now)
    assert after != first and "projects/ev/yeni.md" in [n["path"] for n in after["notes"]]
    assert after == _uncached_map(leaky, monkeypatch)
    walks = []
    history = reader.history
    monkeypatch.setattr(reader, "history", lambda *a: walks.append(a) or history(*a))
    monkeypatch.setattr(reader, "note_links", lambda store: walks.append("links") or {})
    views.memory_map(leaky, now)
    assert walks == []  # the same head: the history and the links are not read again


def _commit_a_note(data, path="projects/ev/sonradan.md"):
    store = Store(data)
    try:
        store.write(path, "# Sonradan\n")
    finally:
        store.index.db.close()


def _uncached(view, data, now, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(views, "_CACHE", views._Cache())
        return view(data, now)


def test_the_history_is_read_once_per_head_whichever_section_asks(leaky, monkeypatch):
    from council.panel import reader

    now = dt.datetime.now().astimezone()
    reads = []
    history = reader.history
    monkeypatch.setattr(reader, "history", lambda store: reads.append(1) or history(store))
    first = views.schema(leaky, now)
    assert views.schema(leaky, now) == first == _uncached(views.schema, leaky, now, monkeypatch)
    reads.clear()
    notes = views.notes(leaky, now)
    views.memory_map(leaky, now)
    views.schema(leaky, now)
    assert reads == []  # the same head: nobody walks the history again
    assert notes == _uncached(views.notes, leaky, now, monkeypatch)
    reads.clear()
    _commit_a_note(leaky)
    later = dt.datetime.now().astimezone()
    after = views.schema(leaky, later)
    assert len(reads) == 1 and after == _uncached(views.schema, leaky, later, monkeypatch)
    assert any("projects/ev/sonradan.md" in s["value"] for e in after["events"] for s in e["steps"])
    assert views.notes(leaky, later)["days"][-1]["changes"] == notes["days"][-1]["changes"] + 1


def test_a_history_that_could_not_be_read_is_not_kept(leaky, monkeypatch):
    from council.panel import reader

    now = dt.datetime.now().astimezone()
    whole = _uncached(views.notes, leaky, now, monkeypatch)
    assert sum(d["changes"] for d in whole["days"]) > 0
    with monkeypatch.context() as m:
        m.setattr(reader, "history", lambda store: None)  # git timed out, say
        assert sum(d["changes"] for d in views.notes(leaky, now)["days"]) == 0
    assert views.notes(leaky, now) == whole


def test_the_skill_index_is_built_once_per_head_for_schema_and_today(leaky, monkeypatch):
    now = dt.datetime.now().astimezone()
    built = []
    index = views.context.skills_index
    monkeypatch.setattr(views.context, "skills_index", lambda *a, **k: built.append(1) or index(*a, **k))
    schema, today = views.schema(leaky, now), views.today(leaky, now)
    views.schema(leaky, now), views.today(leaky, now)
    assert len(built) == 1
    assert schema == _uncached(views.schema, leaky, now, monkeypatch)
    assert today == _uncached(views.today, leaky, now, monkeypatch)
    built.clear()
    _commit_a_note(leaky)
    views.today(leaky, now)
    assert len(built) == 1  # the notes moved: built again


def test_note_usage_is_read_again_only_when_the_log_grew(panel_data, monkeypatch):
    from council.panel import reader

    record(panel_data, [("inject", 5, ["core.md"], time.time() - 10)])
    now = dt.datetime.now().astimezone()
    reads = []
    usage = reader.note_usage
    monkeypatch.setattr(reader, "note_usage", lambda d: reads.append(1) or usage(d))
    first = views.notes(panel_data, now)
    assert views.notes(panel_data, now) == first and len(reads) == 1
    record(panel_data, [("read", 5, ["core.md"], time.time() - 5)])
    assert views.notes(panel_data, now)["ranking"][0]["read"] == 1 and len(reads) == 2


def test_an_answer_that_cannot_be_written_as_json_answers_unavailable(panel_signed_in, monkeypatch):
    for odd in ({"chars": float("nan")}, {"path": "not-\udcff.md"}):  # a NaN, a file name that is not UTF-8
        monkeypatch.setattr(views, "notes", lambda *a, odd=odd: odd)
        r = panel_signed_in.get("/panel/api/notes")
        assert r.status_code == 200 and r.json() == {"error": "unavailable"}


def test_the_guides_give_the_same_caddy_lines_and_the_same_facts_about_sessions():
    root = DEPLOY.parent / "docs"
    for guide in ("kurulum.md", "setup.md"):
        text = (root / guide).read_text(encoding="utf-8")
        assert "@panel path /panel /panel/*" in text and "handle @panel {" in text and "/panel*" not in text, guide
        assert "panel.sqlite3" in text and "12" in text, guide

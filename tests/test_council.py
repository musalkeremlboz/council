import datetime as dt
import json
import re

import pytest

from council.context import bootstrap
from council.importer import Importer
from council.store import Conflict, Store, StoreError


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "data")


def test_seed_and_paths(store):
    assert "core.md" in store.list()
    for bad in ["../x.md", "/etc/passwd", ".git/config.md", "a/.hidden.md", "x.txt", ""]:
        with pytest.raises(StoreError):
            store.resolve(bad)


def test_write_requires_sha_to_replace(store):
    n = store.write("projects/a/project.md", "# A\n\nilk")
    with pytest.raises(Conflict):
        store.write("projects/a/project.md", "x")
    with pytest.raises(Conflict):
        store.write("projects/a/project.md", "x", expected_sha="deadbeef")
    n2 = store.write("projects/a/project.md", "# A\n\nikinci", expected_sha=n.sha)
    assert store.read("projects/a/project.md").sha == n2.sha


def test_edit_exactly_once(store):
    store.write("n.md", "elma armut elma")
    with pytest.raises(StoreError):
        store.edit("n.md", [{"old": "elma", "new": "x"}])
    store.edit("n.md", [{"old": "armut", "new": "kiraz"}])
    assert store.read("n.md").text == "elma kiraz elma"


def test_search_folds_turkish(store):
    store.write("projects/havuz/project.md", "# Havuz\n\n## Vardiya\n\nŞifresiz bağlantı kurulumu yapıldı.")
    hits = store.index.search("sifresiz baglanti")
    assert hits and hits[0]["path"] == "projects/havuz/project.md"
    assert store.index.search("kurulumunu")  # suffix variation


def test_session_cards_only_touch_own(store):
    store.upsert_session("aaaaaaaa1111", "ilk", "A gövde")
    store.upsert_session("bbbbbbbb2222", "ikinci", "B gövde")
    store.upsert_session("aaaaaaaa1111", "ilk güncel", "A yeni")
    text = store.read("sessions.md").text
    assert text.count("· aaaaaaaa") == 1 and "A yeni" in text and "A gövde" not in text
    assert "B gövde" in text
    assert text.index("bbbbbbbb") < text.index("aaaaaaaa")  # B was opened later, stays on top


def test_log_validates_refs(store):
    with pytest.raises(StoreError):
        store.append_log("iş", ["yok.md"])
    path = store.append_log("iş bitti", ["core.md"], "sess1234xyz", "claude")
    assert "[[core.md]]" in store.read(path).text


def test_git_history(store):
    store.write("n.md", "bir")
    log = store._git("log", "--oneline").stdout
    assert "write n.md" in log


def test_bootstrap(store):
    store.edit("core.md", [{"old": "# Core", "new": "# Core\n\n- Ad: Deneme Kişi"}])
    store.write("projects/x/project.md", "# X\n\nYüzme havuzu vardiya planı")
    ctx = bootstrap(store, "havuz vardiya")
    assert "Deneme Kişi" in ctx and "projects/x/project.md" in ctx


def test_import_avenox(tmp_path, store):
    src = tmp_path / "vault"
    comp = src / "🔮 850-Companion"
    proj = src / "🏰 300-Projects" / "Alka-Web"
    comp.mkdir(parents=True)
    proj.mkdir(parents=True)
    (src / "receipts").mkdir()
    (src / "knowledge" / "v3").mkdir(parents=True)
    (comp / "Core.md").write_text("# Ben\n\n- Ad: Test", encoding="utf-8")
    (comp / "Kurallar.md").write_text("# K\n\n- [kapsam: x] `🏰 300-Projects/Alka-Web/Kurallar.md`", encoding="utf-8")
    (comp / "Threads.md").write_text("# T\n\n## Active Threads\n\n### İş\n\n## Closed Threads\n", encoding="utf-8")
    (comp / "Last-Session.md").write_text(
        "# Son oturum\n\n## 2026-01-01 10:00 · iş · abcd1234\n\n- x\n\nHenüz bir çalışma sonucu kaydedilmedi. talimat", encoding="utf-8")
    (proj / "Alka-Web.md").write_text("# Proje\n\nbkz [[Alka-Web]]", encoding="utf-8")
    (proj / "Kurallar.md").write_text("# PK", encoding="utf-8")
    (src / "knowledge" / "v3" / "outcomes.md").write_text("generated", encoding="utf-8")
    meta = {"created_at": "2026-01-01T10:00:00+00:00", "session": "abcd1234ffff", "harness": "claude",
            "refs": ["🏰 300-Projects/Alka-Web/Alka-Web.md"]}
    (src / "receipts" / "r.md").write_text(f"---\n{json.dumps(meta)}\n---\nYapıldı", encoding="utf-8")

    Importer(src, store).run()
    assert store.read("core.md").text.startswith("# Ben")
    assert "projects/alka-web/rules.md" in store.read("rules.md").text
    assert "## Active" in store.read("threads.md").text and "Active Threads" not in store.read("threads.md").text
    assert "talimat" not in store.read("sessions.md").text
    assert "[[projects/alka-web/project.md]]" in store.read("projects/alka-web/project.md").text
    assert not any(p.startswith("knowledge/v3") for p in store.list())
    log = store.read("log/2026-01.md").text
    assert "Yapıldı" in log and "[[projects/alka-web/project.md]]" in log


def _transcript(tmp_path, names, start=1000.0):
    f = tmp_path / "t.jsonl"
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}})]
    for k, n in enumerate(names):
        ts = dt.datetime.fromtimestamp(start + k * 10, dt.timezone.utc).isoformat().replace("+00:00", "Z")
        lines.append(json.dumps({"type": "assistant", "timestamp": ts,
                                 "message": {"content": [{"type": "tool_use", "name": n, "input": {}}]}}))
    f.write_text("\n".join(lines) + "\n")
    return str(f)


def test_stop_hook(tmp_path, monkeypatch, capsys):
    from council import hook

    monkeypatch.setattr(hook, "STATE", tmp_path / "state")
    none = lambda sid: None
    ev = lambda names: {"session_id": "s1", "transcript_path": _transcript(tmp_path, names)}
    hook.stop_check(ev(["Read", "Bash"]), none)
    assert capsys.readouterr().out == ""  # nothing changed
    hook.stop_check(ev(["mcp__council__council_edit", "mcp__council__council_log"]), none)
    assert capsys.readouterr().out == ""  # logged after the change
    hook.stop_check(ev(["mcp__council__council_log", "Edit"]), none)
    assert json.loads(capsys.readouterr().out)["decision"] == "block"
    hook.stop_check(ev(["mcp__council__council_log", "Edit"]), none)
    assert capsys.readouterr().out == ""  # reminded once for the same edits
    hook.stop_check({**ev(["Edit", "Edit", "Write"]), "stop_hook_active": True}, none)
    assert capsys.readouterr().out == ""


def test_stop_hook_sees_server_logs(tmp_path, monkeypatch, capsys):
    from council import hook

    monkeypatch.setattr(hook, "STATE", tmp_path / "state")
    ev = {"session_id": "s2", "transcript_path": _transcript(tmp_path, ["Edit", "Bash"], start=1000.0)}
    hook.stop_check(ev, lambda sid: 1015.0)  # logged by a script after the edit at t=1000
    assert capsys.readouterr().out == ""
    hook.stop_check(ev, lambda sid: 990.0)  # server log is older than the edit
    assert json.loads(capsys.readouterr().out)["decision"] == "block"


def test_session_log_marks(store):
    store.append_log("iş", ["core.md"], "abcdef123456")
    assert "abcdef12" in store.session_logs()


def test_relevant_excludes_fixed(store):
    from council.context import relevant

    store.write("projects/x/project.md", "# X\n\nvardiya planı")
    out = relevant(store, "vardiya")
    assert "projects/x/project.md" in out and "core.md" not in out


def test_reimport_is_idempotent(tmp_path, store):
    src = tmp_path / "v"
    (src / "receipts").mkdir(parents=True)
    meta = {"created_at": "2026-01-01T10:00:00+00:00", "session": "abcd1234", "harness": "claude", "refs": []}
    (src / "receipts" / "r.md").write_text(f"---\n{json.dumps(meta)}\n---\nBir kez", encoding="utf-8")
    Importer(src, store).run()
    Importer(src, store).run()
    assert store.read("log/2026-01.md").text.count("Bir kez") == 1


def test_session_log_backfill(store):
    store.write("log/2026-01.md", "# Log\n\n## 2026-01-02 10:15 · claude · deadbeef\n\nx\n")
    (store.data / "session-logs.json").unlink(missing_ok=True)
    assert "deadbeef" in store.session_logs()


# ---------- chunking: big sections split at list items ----------

def _big_section(n=8):
    """One section of n list items (~220 chars each, far above one chunk), each with a nested line."""
    return "# Not\n\n## Açık\n" + "\n".join(
        f"- madde{i} " + "kelime " * 28 + f"\n  - ayrıntı{i}" for i in range(n))


def test_big_section_splits_at_list_items():
    from council.index import chunks

    bodies = [b for h, b in chunks(_big_section()) if h == "Not > Açık"]
    assert len(bodies) > 1
    assert all(len(b) <= 720 for b in bodies)
    assert all(b.startswith("## Açık\n- madde") for b in bodies)  # heading kept, cut only at an item start
    joined = "\n".join(bodies)
    for i in range(8):  # nothing lost, nothing duplicated, nested line stays with its item
        assert joined.count(f"- madde{i} ") == 1
        assert joined.count(f"  - ayrıntı{i}") == 1


def test_fact_deep_in_big_section_reaches_injected_context(store):
    from council.context import relevant

    store.write("projects/x/project.md", _big_section() + "\n- parola kelimesi: mavi-havuz-42")
    assert "mavi-havuz-42" in relevant(store, "parola kelimesi")


def test_old_index_is_rebuilt_with_new_chunking(tmp_path):
    import sqlite3
    from council.index import Index, fold

    data = tmp_path / "data"
    text = _big_section() + "\n- parola kelimesi: mavi-havuz-42"
    (data / "vault").mkdir(parents=True)
    (data / "vault" / "n.md").write_text(text, encoding="utf-8")
    # an index as the previous version left it: the whole section as one chunk, file marked up to date
    old = sqlite3.connect(data / "index.sqlite3")
    old.executescript(
        "CREATE TABLE files(path TEXT PRIMARY KEY, sha TEXT NOT NULL);"
        "CREATE VIRTUAL TABLE chunks USING fts5(path UNINDEXED, heading, body, folded, tokenize='unicode61 remove_diacritics 2');")
    import hashlib
    old.execute("INSERT INTO files VALUES(?,?)", ("n.md", hashlib.sha256(text.encode()).hexdigest()))
    old.execute("INSERT INTO chunks VALUES(?,?,?,?)", ("n.md", "Not > Açık", text, fold(text)))
    old.commit(); old.close()

    hit = Store(data).index.search("parola kelimesi")[0]
    assert "mavi-havuz-42" in hit["text"] and len(hit["text"]) <= 720


# ---------- stopwords: filler words alone never inject notes ----------

def test_injection_ignores_filler_words_but_search_tool_does_not(store):
    from council.context import relevant

    store.write("a.md", "# A\n\nBu iş nasıl tamam olur, sonra bakarız.")
    store.write("b.md", "# B\n\nhavuz vardiya planı")
    assert relevant(store, "evet tamam olur") == ""
    out = relevant(store, "bu havuz nasıl")
    assert "b.md" in out and "a.md" not in out
    assert store.index.search("tamam")[0]["path"] == "a.md"  # explicit search stays literal


# ---------- no repeats inside one session ----------

def test_relevant_skips_what_the_session_already_got(store):
    from council.context import relevant

    store.write("projects/x/project.md", "# X\n\nvardiya planı")
    seen = set()
    assert "projects/x/project.md" in relevant(store, "vardiya", seen=seen)
    assert relevant(store, "vardiya planı", seen=seen) == ""
    store.edit("projects/x/project.md", [{"old": "planı", "new": "planı değişti"}])
    assert "değişti" in relevant(store, "vardiya", seen=seen)  # a changed note is news again


@pytest.fixture
def api(tmp_path, monkeypatch):
    from starlette.testclient import TestClient
    from council.server import build

    monkeypatch.setenv("COUNCIL_TOKEN", "t0k")
    app, store = build(str(tmp_path / "data"))
    with TestClient(app, base_url="http://127.0.0.1:8765", headers={"Authorization": "Bearer t0k"}) as c:
        yield c, store


def test_api_does_not_repeat_notes_within_a_session(api):
    c, store = api
    store.write("projects/x/project.md", "# X\n\nvardiya planı")
    ask = lambda **kw: c.post("/api/context", json={"mode": "prompt", "query": "vardiya", **kw}).json()["context"]
    assert "projects/x/project.md" in ask(session_id="s1")
    assert ask(session_id="s1") == ""  # same session: already sent
    assert "projects/x/project.md" in ask(session_id="s2")  # another session is unaffected
    assert "projects/x/project.md" in ask()  # a hook that sends no session id keeps the old behaviour
    c.post("/api/context", json={"mode": "start", "session_id": "s1"})
    assert "projects/x/project.md" in ask(session_id="s1")  # session start (also after compaction) resets


@pytest.mark.parametrize("event", ["SessionStart", "UserPromptSubmit"])
def test_hook_tells_the_server_which_session_it_is(event, monkeypatch, capsys):
    import io
    from council import hook

    sent = []
    monkeypatch.setattr(hook, "load_config", lambda: {"url": "http://x", "token": "t"})
    monkeypatch.setattr(hook, "fetch", lambda cfg, payload, timeout=8.0: sent.append(payload) or "ctx")
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO(json.dumps(
        {"hook_event_name": event, "session_id": "s9", "prompt": "merhaba"})))
    hook.main()
    assert sent[0]["session_id"] == "s9"


def test_session_memory_is_bounded():
    from council.context import SessionSeen

    mem = SessionSeen(max_sessions=2)
    for sid in "abc":
        mem.get(sid).add(1)
    assert mem.get("c") == {1}
    assert mem.get("a") == set()  # the oldest session was dropped
    assert mem.get("") is None  # no session id: nothing to remember


# ---------- session-start budget: whole units, visible omissions, early warning ----------

def _filler(n):
    return ("dolgu " * (n // 6 + 1))[:n]


def test_bootstrap_shows_the_latest_cards_whole(store):
    for i in range(3):  # each card is ~1000 chars; two of them are far above the old 1350-char slot
        store.upsert_session(f"sess000{i}", f"iş {i}", f"- {_filler(950)}\n- kartsonu{i}")
    ctx = bootstrap(store)
    assert "kartsonu2" in ctx and "kartsonu1" in ctx  # the two newest, each to its last line
    assert "kartsonu0" not in ctx
    assert "truncated" not in ctx


def test_bootstrap_lets_long_rules_use_room_other_sections_left(store):
    rules = "# Kurallar\n\n" + "\n".join(f"- 2026-01-{i:02d}: kural{i} {_filler(140)}" for i in range(1, 19))
    store.write("rules.md", rules, expected_sha=store.read("rules.md").sha)  # ~2900 chars, old slot was 1800
    ctx = bootstrap(store)
    assert all(f"kural{i} " in ctx for i in range(1, 19))  # the newest rules sit at the end and must survive


def test_bootstrap_never_cuts_a_thread_in_half(store):
    threads = "# Threads\n\n## Active\n" + "\n".join(
        f"### Konu{i}\n- **Durum:** {_filler(2400)}\n- **Not:** konusonu{i}\n" for i in range(6)) + "\n## Closed\n"
    store.write("threads.md", threads, expected_sha=store.read("threads.md").sha)
    ctx = bootstrap(store)
    shown = [i for i in range(6) if f"konusonu{i}" in ctx]
    assert shown == [0, 1, 2]  # 9000 chars hold three such threads, in order, complete
    pointer = next(line for line in ctx.splitlines() if "threads.md" in line and "not shown" in line)
    assert all(f"Konu{i}" in pointer for i in (3, 4, 5))  # the rest are named, not silently dropped
    assert "### Konu3" not in ctx


def test_bootstrap_warns_only_when_fixed_notes_squeeze_the_budget(store):
    has_notice = lambda: "[COUNCIL maintenance]" in bootstrap(store)
    assert not has_notice()
    rules = "# Kurallar\n\n" + "\n".join(f"- 2026-01-{i:02d}: kural{i} {_filler(140)}" for i in range(1, 19))
    store.write("rules.md", rules, expected_sha=store.read("rules.md").sha)
    assert not has_notice()  # over its own target (1800), but the others leave that room unused
    store.write("core.md", "# Core\n\n" + _filler(3600), expected_sha=store.read("core.md").sha)
    notice = next(line for line in bootstrap(store).splitlines() if line.startswith("[COUNCIL maintenance]"))
    assert "rules.md" in notice and "core.md" in notice and "threads.md" not in notice  # names the big ones


# ---------- sessions.md stays small: old cards move to a monthly archive ----------

def test_old_session_cards_move_to_a_searchable_archive(store):
    from council.context import relevant

    for i in range(12):
        store.upsert_session(f"sess{i:04d}", f"iş {i}", f"- anahtar{i} yapıldı")
    current = store.read("sessions.md").text
    assert [f"anahtar{i} " in current for i in range(12)] == [False, False] + [True] * 10
    archives = store.list("sessions/")
    assert len(archives) == 1 and re.fullmatch(r"sessions/\d{4}-\d{2}\.md", archives[0])
    old = store.read(archives[0]).text
    assert "anahtar0 " in old and "anahtar1 " in old and "anahtar2 " not in old
    assert archives[0] in relevant(store, "anahtar0")  # an archived card can be injected when it is relevant


# ---------- machine events are not user messages ----------

@pytest.mark.parametrize("prompt, asked", [
    ("<task-notification>\n<task-id>b5dc</task-id>\n<status>completed</status>\n</task-notification>", 0),
    ("  <side-sessions-event>oturum bitti</side-sessions-event>", 0),
    ("<ci-monitor-event>checks failed</ci-monitor-event>", 0),
    ("<div>havuz</div> bu neden çalışmıyor", 1),  # a person pasting markup is still a person
    ("task-notification nedir, havuz vardiyası için lazım", 1),
])
def test_hook_asks_for_notes_only_on_messages_a_person_wrote(prompt, asked, monkeypatch, capsys):
    import io
    from council import hook

    sent = []
    monkeypatch.setattr(hook, "load_config", lambda: {"url": "http://x", "token": "t"})
    monkeypatch.setattr(hook, "fetch", lambda cfg, payload, timeout=8.0: sent.append(payload) or "ctx")
    monkeypatch.setattr(hook.sys, "stdin", io.StringIO(json.dumps(
        {"hook_event_name": "UserPromptSubmit", "session_id": "s9", "prompt": prompt})))
    hook.main()
    assert len(sent) == asked
    assert "COUNCIL session=s9" in capsys.readouterr().out  # the time stamp is still given


# ---------- usage log ----------

def test_usage_counts_per_note_and_ignores_old_events(tmp_path):
    import time
    from council.usage import Usage

    u = Usage(tmp_path / "u.sqlite3")
    u.record("read", session="s1", hits=[{"path": "a.md"}])
    u.record("search", session="s1", query="havuz", hits=[{"path": "a.md", "heading": "H", "score": 3.2}, {"path": "b.md"}])
    u.record("read", session="s0", hits=[{"path": "eski.md"}], ts=time.time() - 10 * 86400)
    s = u.summary(days=7)
    assert s["events"] == {"read": 1, "search": 1}
    assert s["notes"]["a.md"] == {"injected": 0, "read": 1, "found": 1}
    assert s["notes"]["b.md"] == {"injected": 0, "read": 0, "found": 1}
    assert "eski.md" not in s["notes"]


def test_api_records_what_each_message_was_given(api):
    from council.usage import Usage

    c, store = api
    store.write("projects/x/project.md", "# X\n\nvardiya planı")
    for q in ("vardiya", "evet tamam"):
        c.post("/api/context", json={"mode": "prompt", "query": q, "session_id": "s1"})
    s = Usage(store.data / "usage.sqlite3").summary(days=1)
    assert s["inject"]["messages"] == 2 and s["inject"]["with_notes"] == 1
    assert s["notes"]["projects/x/project.md"]["injected"] == 1


# ---------- off-site backup ----------

def _bare_remote(tmp_path, store, name="remote.git"):
    import subprocess

    remote = tmp_path / name
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    store._git("remote", "add", "backup", str(remote))
    return remote


def test_backup_pushes_the_history_to_the_remote(tmp_path, store):
    import subprocess

    remote = _bare_remote(tmp_path, store)
    store.write("n.md", "# N\n\nyedeklenecek")
    assert store.backup()["ok"] is True
    log = subprocess.run(["git", "--git-dir", str(remote), "log", "--all", "--format=%s"], capture_output=True, text=True)
    assert "write n.md" in log.stdout


def test_bootstrap_reports_a_backup_that_stopped_working(tmp_path, store, monkeypatch):
    import shutil, time

    assert store.backup()["ok"] is False  # no remote configured: not a backup that broke
    assert "backup" not in bootstrap(store)
    remote = _bare_remote(tmp_path, store)
    assert store.backup()["ok"] is True
    shutil.rmtree(remote)
    assert store.backup()["ok"] is False
    assert "[COUNCIL maintenance]" not in bootstrap(store)  # a short outage is not worth a warning
    real = time.time()
    monkeypatch.setattr("council.store.time.time", lambda: real + 3 * 86400)
    notice = next(line for line in bootstrap(store).splitlines() if line.startswith("[COUNCIL maintenance]"))
    assert "backup" in notice


# ---------- size watch: open a thread once the vault has grown enough ----------

def test_size_watch_opens_one_thread_when_the_vault_reaches_the_threshold(tmp_path):
    from council.cli import main

    data = tmp_path / "data"
    store = Store(data)  # 4 seed notes
    args = ["--data", str(data), "watch-size", "--notes", "6", "--chunks", "100000",
            "--title", "Anlamsal aramayı yeniden test et", "--body", "Ölçüt: projects/council/benchmark.md"]
    main(args)
    assert "Anlamsal" not in Store(data).read("threads.md").text
    for i in range(3):
        store.write(f"n{i}.md", "# N\n\nmetin")
    main(args)
    main(args)
    threads = Store(data).read("threads.md").text
    assert threads.count("### Anlamsal aramayı yeniden test et") == 1
    assert "Ölçüt: projects/council/benchmark.md" in threads and "7 notes" in threads
    assert threads.index("## Active") < threads.index("### Anlamsal") < threads.index("## Closed")

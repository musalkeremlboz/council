import sqlite3

import pytest

from council import context
from council.learn import Learning, render_skill
from council.store import Store

SK = dict(when="Çalışan bir servisin üstüne yeniden kurulum yapılırken",
          steps="1. Eski işi durdur\n2. Bittiğini doğrula\n3. Yenisini yükle",
          learned_from="Yeniden kurulum 'Input/output error' verdi; bekleyince düzeldi.")


@pytest.fixture
def api(tmp_path, monkeypatch):
    from starlette.testclient import TestClient
    from council.server import build

    monkeypatch.setenv("COUNCIL_TOKEN", "t0k")
    app, store = build(str(tmp_path / "data"))
    with TestClient(app, base_url="http://127.0.0.1:8765", headers={"Authorization": "Bearer t0k"}) as c:
        yield c, store


POINTER = "[COUNCIL · a saved skill may fit this message · open it with council_read only if it is the work being asked]"


def test_a_matching_skill_comes_with_the_message_once_per_session(api):
    c, store = api
    L = Learning(store); L.write_skill("Servisi yeniden kurarken beklet", **SK)
    store.write("projects/x/project.md", "# X\n\nservis notları: yeniden kurulum planı")
    ask = lambda q, sid: c.post("/api/context", json={"mode": "prompt", "query": q, "session_id": sid}).json()["context"]
    first = ask("servisi yeniden kurmam lazım, üstüne kurulum yapacağım", "s1")
    assert POINTER in first
    assert f"- skills/servisi-yeniden-kurarken-beklet.md — {SK['when']}\n" in first
    assert "Eski işi durdur" not in first and "Yeniden kurulum 'Input/output error'" not in first
    assert "skill may fit" not in ask("servisi yeniden kurmam lazım", "s1")
    c.post("/api/context", json={"query": "", "session_id": "s1"})        # a session start: nothing is in context
    assert POINTER in ask("servisi yeniden kurmam lazım, üstüne kurulum yapacağım", "s1")


def test_no_skills_means_no_heading_and_retired_skills_stay_out(api):
    c, store = api
    ask = lambda q: c.post("/api/context", json={"mode": "prompt", "query": q, "session_id": "s"}).json()["context"]
    assert "skill may fit" not in ask("servisi yeniden kurmam lazım")
    L = Learning(store); L.write_skill("beklet", **SK)
    L.feedback("beklet", "wrong", session="a"); L.feedback("beklet", "wrong", session="b")
    out = ask("çalışan servisin üstüne yeniden kurulum")
    assert "skill may fit" not in out and "skills/retired" not in out


def test_a_long_or_multi_line_when_is_one_clipped_line(api):
    c, store = api
    when = "Çalışan servisin üstüne yeniden kurulum yapılırken " + "ayrıntı satırı " * 40   # one line, 500+ characters
    assert len(when) > 500 and when[199] != " "
    (store.vault / "skills").mkdir(exist_ok=True)
    (store.vault / "skills" / "kurulum.md").write_text(render_skill("Kurulum", **{**SK, "when": when}), encoding="utf-8")
    out = _ask(c, "çalışan servisin üstüne yeniden kurulum")
    lines = [ln for ln in out[out.index(POINTER):].splitlines() if ln.startswith("- skills/kurulum.md")]
    assert len(lines) == 1
    clipped = lines[0].removeprefix("- skills/kurulum.md — ")
    assert len(clipped) == 200 and clipped == when[:200]
    # a line break inside the When never makes a second pointer line
    (store.vault / "skills" / "kurulum.md").write_text(
        render_skill("Kurulum", **{**SK, "when": "Çalışan servisin üstüne yeniden kurulum\nikinci satır"}), encoding="utf-8")
    out = _ask(c, "çalışan servisin üstüne yeniden kurulum", "s2")   # a new session: the pointer is shown again
    assert len([ln for ln in out[out.index(POINTER):].splitlines() if ln.startswith("- skills/kurulum.md")]) == 1


def test_a_broken_learning_file_does_not_stop_the_notes(api):
    c, store = api
    store.write("projects/x/project.md", "# X\n\nservis notları: yeniden kurulum planı")
    Learning(store).write_skill("Servisi yeniden kurarken beklet", **SK)
    (store.data / "learning.json").write_text("{not json", encoding="utf-8")
    out = c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum",
                                       "session_id": "s"}).json()["context"]
    assert "projects/x/project.md" in out


@pytest.mark.parametrize("broken", ["match", "parse_skill"])
def test_nothing_in_the_skills_path_stops_the_notes(api, monkeypatch, caplog, broken):
    c, store = api
    store.write("projects/x/project.md", "# X\n\nservis notları: yeniden kurulum planı")
    Learning(store).write_skill("Servisi yeniden kurarken beklet", **SK)

    def boom(*a, **k):
        raise sqlite3.OperationalError("disk I/O error")
    monkeypatch.setattr(Learning if broken == "match" else context, broken, boom)
    r = c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum",
                                     "session_id": "s"})
    assert r.status_code == 200 and "projects/x/project.md" in r.json()["context"]
    assert "skill may fit" not in r.json()["context"]
    assert [rec.exc_info[0] for rec in caplog.records if rec.name == "council"] == [sqlite3.OperationalError]


def test_a_failed_block_does_not_hide_the_skill_for_the_session(api, monkeypatch):
    c, store = api
    Learning(store).write_skill("Servisi yeniden kurarken beklet", **SK)
    ask = lambda: c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum",
                                               "session_id": "s"}).json()["context"]
    with monkeypatch.context() as m:
        m.setattr(context, "parse_skill", lambda *a, **k: 1 / 0)
        assert "skill may fit" not in ask()
    assert "skill may fit" in ask()


def test_the_council_context_tool_text_carries_the_skills(tmp_path):
    from council.server import context_for_tool
    from council.usage import Usage
    store = Store(tmp_path / "data")
    L = Learning(store); L.write_skill("Servisi yeniden kurarken beklet", **SK)
    usage = Usage(tmp_path / "u.sqlite3")
    q = "çalışan servisin üstüne yeniden kurulum"
    text = context_for_tool(store, L, usage, q)
    assert "[COUNCIL · saved skills" in text and f"- skills/servisi-yeniden-kurarken-beklet.md — {SK['when']}\n" in text
    assert text.index("[COUNCIL · saved skills") < text.index(POINTER) and "Eski işi durdur" not in text
    assert "skill may fit" not in context_for_tool(store, L, usage, "vardiya")


def test_session_endpoint_reports_the_live_skills_among_the_paths_read_and_counts_reviews(api):
    c, store = api
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]; q = L.write_skill("ikinci", **SK)["path"]
    L.write_skill("eski", **SK); L.feedback("eski", "wrong", session="a"); L.feedback("eski", "wrong", session="b")
    store.write("skills/notum.md", "# Not a skill\n\njust a note")
    read = [q, "skills/retired/eski.md", "skills/notum.md", 5, None, p, q, "core.md"]
    r = c.post("/api/session", json={"session_id": "sess-1", "review": True, "read": read}).json()
    assert r["skills"] == [q, p] and "last_log" in r
    assert Learning(store).summary()["reviews_asked"] == 1


def test_session_endpoint_uses_at_most_200_read_entries_and_ignores_a_non_list(api):
    c, store = api
    p = Learning(store).write_skill("beklet", **SK)["path"]
    late = ["x"] * 200 + [p]
    assert c.post("/api/session", json={"session_id": "s", "read": late}).json()["skills"] == []
    assert c.post("/api/session", json={"session_id": "s", "read": p}).json()["skills"] == []


def test_session_endpoint_without_read_reports_no_skills(api):
    c, store = api
    Learning(store).write_skill("beklet", **SK)
    assert c.post("/api/session", json={"session_id": "sess-1", "review": True}).json()["skills"] == []
    assert c.post("/api/session", json={"session_id": "sess-1"}).json()["skills"] == []


def test_reading_a_live_skill_is_logged_as_opened(tmp_path, monkeypatch):
    import asyncio
    import json
    from council import server
    from council.usage import Usage
    made = []
    real = server.MCPServer
    monkeypatch.setattr(server, "MCPServer", lambda *a, **k: made.append(real(*a, **k)) or made[-1])
    monkeypatch.setenv("COUNCIL_TOKEN", "t0k")
    _, store = server.build(str(tmp_path / "data"))
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]
    L.write_skill("eski", **SK); L.feedback("eski", "wrong", session="a"); L.feedback("eski", "wrong", session="b")
    store.write("skills/notum.md", "# Not a skill\n\njust a note")
    store.write("notum.md", "# Normal")
    u = Usage(store.data / "usage.sqlite3")
    events = lambda: [(k, json.loads(h)) for k, h in u.db.execute("select kind, hits from events order by ts, rowid")]

    def read(path):
        asyncio.run(made[0].call_tool("council_read", {"path": path}))

    for other in ("skills/retired/eski.md", "skills/notum.md", "notum.md"):
        read(other)
    assert [k for k, _ in events()] == ["read"] * 3                         # nothing opened
    read(p)
    assert [k for k, _ in events()][-2:] == ["read", "open"]
    assert events()[-1][1] == [{"path": p}]


def test_a_failing_open_check_does_not_fail_the_read(tmp_path, monkeypatch, caplog):
    import asyncio
    import logging
    from council import server
    made = []
    real = server.MCPServer
    monkeypatch.setattr(server, "MCPServer", lambda *a, **k: made.append(real(*a, **k)) or made[-1])
    monkeypatch.setenv("COUNCIL_TOKEN", "t0k")
    _, store = server.build(str(tmp_path / "data"))
    p = Learning(store).write_skill("beklet", **SK)["path"]

    def boom(self, path):
        raise RuntimeError("check broke")

    monkeypatch.setattr(Learning, "is_live_skill", boom)
    with caplog.at_level(logging.ERROR, logger="council"):
        out = asyncio.run(made[0].call_tool("council_read", {"path": p}))
    assert "Eski işi durdur" in str(out) and "skill open not recorded" in caplog.text


def test_hook_and_server_together_ask_about_the_live_skill_that_was_opened(api, tmp_path, monkeypatch, capsys):
    import json
    from council import hook
    c, store = api
    L = Learning(store)
    live = L.write_skill("beklet", **SK)["path"]
    L.write_skill("eski", **SK); L.feedback("eski", "wrong", session="a"); L.feedback("eski", "wrong", session="b")
    store.write("skills/notum.md", "# Not a skill\n\njust a note")
    reads = [("mcp__council__council_read", {"path": p})
             for p in (live, "skills/retired/eski.md", "skills/notum.md", "core.md")]
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}})]
    for name, args in reads + [("Read", {})] * 15:
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": name, "input": args}]}}))
    t = tmp_path / "t.jsonl"
    t.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def session_info(sid, review=False, read=None):       # what hook.server_session sends, through the real route
        body = {"session_id": sid, "review": review, **({"read": read} if read is not None else {})}
        return c.post("/api/session", json=body).json()

    monkeypatch.setattr(hook, "STATE", tmp_path / "state")
    monkeypatch.setattr(hook, "CONFIG", tmp_path / "no-config.json")
    hook.stop_check({"session_id": "sess-1", "transcript_path": str(t)}, session_info)
    reason = json.loads(capsys.readouterr().out)["reason"]
    assert f"You opened these skills since the last review: {live}. " in reason
    assert "eski.md" not in reason and "notum.md" not in reason and "core.md" not in reason
    assert L.feedback(live, "helped", session="sess-1")["path"] == live


def test_learning_tools_are_listed_and_instructions_mention_them(api):
    from council import server
    for word in ("council_rule", "council_skill", "council_unlearn", "council_skill_feedback", "never secrets"):
        assert word in server.INSTRUCTIONS
    assert len(server.INSTRUCTIONS) < 2600


def test_instructions_say_to_open_a_listed_skill_and_report_on_it(api):
    from council import server
    text = " ".join(server.INSTRUCTIONS.split())
    assert "shown skill" not in text
    assert "The start context lists saved skills by path." in text
    assert ("When the work asked for is the work one names, open it with council_read and follow it, "
            "and afterwards report with council_skill_feedback (name = its path) whether it helped.") in text


def test_tool_docstrings_speak_of_opened_skills_and_naming_the_work(tmp_path, monkeypatch):
    import asyncio
    from council import server
    made = []
    real = server.MCPServer
    monkeypatch.setattr(server, "MCPServer", lambda *a, **k: made.append(real(*a, **k)) or made[-1])
    monkeypatch.setenv("COUNCIL_TOKEN", "t0k")
    server.build(str(tmp_path / "data"))
    doc = {t.name: " ".join((t.description or "").split()) for t in asyncio.run(made[0].list_tools())}
    assert "a skill you opened" in doc["council_skill_feedback"] and "shown" not in doc["council_skill_feedback"]
    assert ("The name should name the work itself, most important words first (the first 60 characters become "
            "the path agents choose by)") in doc["council_skill"]


def _ask(c, q, sid="s"):
    return c.post("/api/context", json={"mode": "prompt", "query": q, "session_id": sid}).json()["context"]


Q = "çalışan servisin üstüne yeniden kurulum yapacağım"


def test_an_ordinary_note_under_skills_is_served_as_a_note_and_never_as_a_skill(api):
    c, store = api
    store.write("skills/python.md", "# Servis kurulum notlarım\n\nÇalışan servisin üstüne yeniden kurulum: "
                                    "önce yedek al, sonra kur.")
    out = _ask(c, Q)
    assert "- skills/python.md" in out and "skill may fit" not in out
    assert Learning(store).match(Q) == []


def test_a_hand_written_skill_with_a_secret_is_not_offered(api):
    c, store = api
    from council.learn import render_skill
    store.write("skills/deploy.md", render_skill(
        "Servisi yeniden kur", SK["when"], "1. PASSWORD=hunter2abc ile gir\n2. Yeniden kur", SK["learned_from"],
        status="established"))
    assert Learning(store).match(Q) == [] and "skill may fit" not in _ask(c, Q)


def test_a_live_note_whose_status_says_retired_is_kept_out(api):
    c, store = api
    from council.learn import render_skill
    store.write("skills/eski.md", render_skill("Servisi yeniden kurarken beklet", SK["when"], SK["steps"],
                                               SK["learned_from"], status="retired"))
    out = _ask(c, Q)
    assert "skills/eski.md" not in out and "Eski işi durdur" not in out


def test_council_context_never_injects_a_retired_skill_and_shows_a_live_one_once(tmp_path):
    from council.server import context_for_tool
    from council.usage import Usage
    store = Store(tmp_path / "data")
    L = Learning(store)
    L.write_skill("beklet", **{**SK, "steps": "1. Emekli adım: eski işi bekle"})
    L.feedback("beklet", "wrong", session="a"); L.feedback("beklet", "wrong", session="b")
    L.write_skill("Servisi yeniden kurarken beklet", **SK)
    text = context_for_tool(store, L, Usage(tmp_path / "u.sqlite3"), Q)
    assert "skills/retired" not in text and "Emekli adım" not in text
    assert "Eski işi durdur" not in text and text.count("- skills/servisi-yeniden-kurarken-beklet.md — ") == 1
    assert POINTER in text


def test_session_endpoint_answers_when_the_review_count_fails(api, monkeypatch):
    c, store = api
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]
    monkeypatch.setattr(Learning, "note_review_asked", lambda self: 1 / 0)
    r = c.post("/api/session", json={"session_id": "sess-1", "review": True, "read": [p]})
    assert r.status_code == 200 and r.json()["skills"] == [p] and "last_log" in r.json()


def test_instructions_ask_for_the_session_id(api):
    from council import server
    assert "Pass your session id to all four learning tools" in server.INSTRUCTIONS


def test_a_pointer_is_logged_and_does_not_count_as_injected(tmp_path):
    import json
    from council.server import context_for_tool
    from council.usage import Usage
    store = Store(tmp_path / "data")
    L = Learning(store); L.write_skill("Servisi yeniden kurarken beklet", **SK)
    u = Usage(tmp_path / "u.sqlite3")
    assert POINTER in context_for_tool(store, L, u, "çalışan servisin üstüne yeniden kurulum")
    kinds = dict(u.db.execute("select kind, hits from events").fetchall())
    assert "skill" not in kinds and json.loads(kinds["pointer"])[0]["path"] == "skills/servisi-yeniden-kurarken-beklet.md"
    assert "skills/servisi-yeniden-kurarken-beklet.md" not in u.summary()["notes"]


def test_a_skill_whose_file_name_is_not_a_slug_still_comes_as_a_pointer(api):
    c, store = api
    (store.vault / "skills").mkdir(exist_ok=True)
    (store.vault / "skills" / "Yedek alma notu.md").write_text(render_skill("Yedek alma notu", **SK), encoding="utf-8")
    out = _ask(c, "çalışan servisin üstüne yeniden kurulum")
    assert f"- skills/Yedek alma notu.md — {SK['when']}\n" in out and "Eski işi durdur" not in out
    start = c.post("/api/context", json={"query": "", "session_id": "s2"}).json()["context"]
    assert "Yedek alma notu" not in start


def test_usage_summary_counts_pointers_per_skill_and_opens_per_read(tmp_path):
    from council.usage import Usage
    u = Usage(tmp_path / "u.sqlite3")
    assert u.summary()["skills"] == {"pointers": 0, "opened": 0}
    u.record("pointer", hits=[{"path": "skills/a.md"}, {"path": "skills/b.md"}])
    u.record("pointer", hits=[{"path": "skills/a.md"}])
    u.record("open", hits=[{"path": "skills/a.md"}])
    assert u.summary()["skills"] == {"pointers": 3, "opened": 1}


def test_council_usage_prints_the_skills_line(tmp_path, capsys):
    from council import cli
    from council.usage import Usage
    Store(tmp_path / "data")
    u = Usage(tmp_path / "data" / "usage.sqlite3")
    u.record("pointer", hits=[{"path": "skills/a.md"}, {"path": "skills/b.md"}])
    u.record("open", hits=[{"path": "skills/a.md"}])
    u.db.close()
    assert cli.main(["--data", str(tmp_path / "data"), "usage"]) == 0
    lines = capsys.readouterr().out.splitlines()
    i = next(i for i, l in enumerate(lines) if l.startswith("skills now:"))
    assert "skills: 2 pointers sent, 1 opened" in lines[i + 1:]

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
    when = "Çalışan servisin üstüne yeniden kurulum yapılırken\n" + "ayrıntı satırı " * 40
    note = render_skill("Kurulum", **{**SK, "when": when})
    (store.vault / "skills").mkdir(exist_ok=True)
    (store.vault / "skills" / "kurulum.md").write_text(note, encoding="utf-8")
    out = _ask(c, "çalışan servisin üstüne yeniden kurulum")
    lines = [ln for ln in out[out.index(POINTER):].splitlines() if ln.startswith("- skills/kurulum.md")]
    assert len(lines) == 1
    clipped = lines[0].removeprefix("- skills/kurulum.md — ")
    assert 0 < len(clipped) <= 200 and "\n" not in clipped
    assert clipped == " ".join(when.split())[:len(clipped)] and len(" ".join(when.split())) > 200


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


def test_session_endpoint_reports_shown_skills_and_counts_reviews(api):
    c, store = api
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]; L.record_shown(p, "sess-1")
    r = c.post("/api/session", json={"session_id": "sess-1", "review": True}).json()
    assert r["skills"] == [p] and "last_log" in r
    assert Learning(store).summary()["reviews_asked"] == 1


def test_learning_tools_are_listed_and_instructions_mention_them(api):
    from council import server
    for word in ("council_rule", "council_skill", "council_unlearn", "council_skill_feedback", "never secrets"):
        assert word in server.INSTRUCTIONS
    assert len(server.INSTRUCTIONS) < 2600


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
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]; L.record_shown(p, "sess-1")
    monkeypatch.setattr(Learning, "note_review_asked", lambda self: 1 / 0)
    r = c.post("/api/session", json={"session_id": "sess-1", "review": True})
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

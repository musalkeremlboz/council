import sqlite3

import pytest

from council.learn import Learning
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


def test_a_matching_skill_comes_with_the_message_once_per_session(api):
    c, store = api
    L = Learning(store); L.write_skill("Servisi yeniden kurarken beklet", **SK)
    store.write("projects/x/project.md", "# X\n\nservis notları: yeniden kurulum planı")
    ask = lambda q, sid: c.post("/api/context", json={"mode": "prompt", "query": q, "session_id": sid}).json()["context"]
    first = ask("servisi yeniden kurmam lazım, üstüne kurulum yapacağım", "s1")
    assert "[COUNCIL · skills that may apply]" in first and "skills/servisi-yeniden-kurarken-beklet.md (candidate)" in first
    assert first.count("Eski işi durdur") == 1                      # not repeated among the ordinary notes
    assert "skills that may apply" not in ask("servisi yeniden kurmam lazım", "s1")
    assert Learning(store).shown_in("s1") == ["skills/servisi-yeniden-kurarken-beklet.md"]


def test_no_skills_means_no_heading_and_retired_skills_stay_out(api):
    c, store = api
    ask = lambda q: c.post("/api/context", json={"mode": "prompt", "query": q, "session_id": "s"}).json()["context"]
    assert "skills that may apply" not in ask("servisi yeniden kurmam lazım")
    L = Learning(store); L.write_skill("beklet", **SK)
    L.feedback("beklet", "wrong", session="a"); L.feedback("beklet", "wrong", session="b")
    out = ask("çalışan servisin üstüne yeniden kurulum")
    assert "skills that may apply" not in out and "skills/retired" not in out


def test_skills_have_their_own_budget(api):
    c, store = api
    L = Learning(store)
    for n in ("bir", "iki", "uc"):
        L.write_skill(f"kurulum {n}", **{**SK, "steps": "yeniden kurulum adımı. " * 150})
    out = c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum", "session_id": "s"}).json()["context"]
    block = out[out.index("[COUNCIL · skills that may apply]"):]
    assert block.count("skills/kurulum-") <= 2 and len(block) <= 1500 + 100


def test_a_broken_learning_file_does_not_stop_the_notes(api):
    c, store = api
    store.write("projects/x/project.md", "# X\n\nservis notları: yeniden kurulum planı")
    Learning(store).write_skill("Servisi yeniden kurarken beklet", **SK)
    (store.data / "learning.json").write_text("{not json", encoding="utf-8")
    out = c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum",
                                       "session_id": "s"}).json()["context"]
    assert "projects/x/project.md" in out


@pytest.mark.parametrize("broken", ["match", "record_shown"])
def test_nothing_in_the_skills_path_stops_the_notes(api, monkeypatch, caplog, broken):
    c, store = api
    store.write("projects/x/project.md", "# X\n\nservis notları: yeniden kurulum planı")
    Learning(store).write_skill("Servisi yeniden kurarken beklet", **SK)

    def boom(*a, **k):
        raise sqlite3.OperationalError("disk I/O error")
    monkeypatch.setattr(Learning, broken, boom)
    r = c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum",
                                     "session_id": "s"})
    assert r.status_code == 200 and "projects/x/project.md" in r.json()["context"]
    assert "skills that may apply" not in r.json()["context"]
    assert [rec.exc_info[0] for rec in caplog.records if rec.name == "council"] == [sqlite3.OperationalError]


def test_a_failed_block_does_not_hide_the_skill_for_the_session(api, monkeypatch):
    c, store = api
    Learning(store).write_skill("Servisi yeniden kurarken beklet", **SK)
    ask = lambda: c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum",
                                               "session_id": "s"}).json()["context"]
    with monkeypatch.context() as m:
        m.setattr(Learning, "record_shown", lambda *a, **k: 1 / 0)
        assert "skills that may apply" not in ask()
    assert "skills that may apply" in ask()


def test_the_council_context_tool_text_carries_the_skills(tmp_path):
    from council.server import context_for_tool
    from council.usage import Usage
    store = Store(tmp_path / "data")
    L = Learning(store); L.write_skill("Servisi yeniden kurarken beklet", **SK)
    usage = Usage(tmp_path / "u.sqlite3")
    q = "çalışan servisin üstüne yeniden kurulum"
    assert "[COUNCIL · skills that may apply]" in context_for_tool(store, L, usage, q)
    assert "skills that may apply" not in context_for_tool(store, L, usage, "vardiya")


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
    assert "- skills/python.md" in out and "skills that may apply" not in out
    assert Learning(store).match(Q) == []


def test_a_hand_written_skill_with_a_secret_is_not_offered(api):
    c, store = api
    from council.learn import render_skill
    store.write("skills/deploy.md", render_skill(
        "Servisi yeniden kur", SK["when"], "1. PASSWORD=hunter2abc ile gir\n2. Yeniden kur", SK["learned_from"],
        status="established"))
    assert Learning(store).match(Q) == [] and "skills that may apply" not in _ask(c, Q)


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
    assert text.count("Eski işi durdur") == 1 and "[COUNCIL · skills that may apply]" in text


def test_session_endpoint_answers_when_the_review_count_fails(api, monkeypatch):
    c, store = api
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]; L.record_shown(p, "sess-1")
    monkeypatch.setattr(Learning, "note_review_asked", lambda self: 1 / 0)
    r = c.post("/api/session", json={"session_id": "sess-1", "review": True})
    assert r.status_code == 200 and r.json()["skills"] == [p] and "last_log" in r.json()


def test_instructions_ask_for_the_session_id(api):
    from council import server
    assert "Pass your session id to all four learning tools" in server.INSTRUCTIONS


def test_usage_counts_a_shown_skill_as_injected(tmp_path):
    from council.usage import Usage
    u = Usage(tmp_path / "u.sqlite3")
    u.record("skill", session="s1", query="q", chars=10, top=9.5, hits=[{"path": "skills/beklet.md", "score": 9.5}])
    assert u.summary()["notes"]["skills/beklet.md"] == {"injected": 1, "read": 0, "found": 0}

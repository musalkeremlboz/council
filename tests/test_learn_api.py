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
    (store.data / "learning.json").write_text("{not json")
    out = c.post("/api/context", json={"mode": "prompt", "query": "çalışan servisin üstüne yeniden kurulum",
                                       "session_id": "s"}).json()["context"]
    assert "projects/x/project.md" in out


@pytest.mark.parametrize("broken", ["match", "record_shown"])
def test_nothing_in_the_skills_path_stops_the_notes(api, monkeypatch, broken):
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

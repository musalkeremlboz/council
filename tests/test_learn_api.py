import pytest

from council.learn import Learning

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
    store.write("projects/x/project.md", "# X\n\nvardiya planı")
    (store.data / "learning.json").write_text("{not json")
    out = c.post("/api/context", json={"mode": "prompt", "query": "vardiya", "session_id": "s"}).json()["context"]
    assert "projects/x/project.md" in out

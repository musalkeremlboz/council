import json

from council import context
from council.store import Store


def filled(tmp_path):
    s = Store(tmp_path / "data")
    s.write("core.md", "# Core\n\n" + "k" * 300, expected_sha=s.read("core.md").sha)
    for i in range(3):
        s.upsert_session(f"sess{i}", f"kart {i}", "x" * 400)
    return s


def test_the_plan_says_what_bootstrap_shows(tmp_path):
    s = filled(tmp_path)
    plan = context.start_plan(s, budget=1100, announce=False)
    assert [x["path"] for x in plan["sections"]] == ["core.md", "rules.md", "threads.md", "sessions.md"]
    cards = plan["sections"][3]
    assert len(cards["units"]) == 2 and cards["shown"] < 2  # START_CARDS cards, and they do not all fit
    text = context.bootstrap(s, budget=1100)
    for sec in plan["sections"]:
        for unit in sec["units"][: sec["shown"]]:
            assert unit in text
    assert "more cards not shown" in text


def test_a_plan_that_does_not_announce_leaves_the_update_notice_for_the_agent(tmp_path):
    s = filled(tmp_path)
    state = s.data / "update.json"
    state.write_text(json.dumps({"installed": {"from": "0.2.0", "to": "0.2.1"}}))
    before = state.read_text()
    assert not any("updated itself" in n for n in context.start_plan(s, announce=False)["notices"])
    assert state.read_text() == before
    assert "updated itself from 0.2.0 to 0.2.1" in context.bootstrap(s)

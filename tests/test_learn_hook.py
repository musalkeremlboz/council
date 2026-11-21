import datetime as dt
import json

import pytest

from council import hook


@pytest.fixture(autouse=True)
def no_user_config(tmp_path, monkeypatch):
    """A developer's own config.json must not change the default review interval."""
    monkeypatch.setattr(hook, "CONFIG", tmp_path / "no-config.json")


def transcript(tmp_path, names, start=1000.0):          # same shape as _transcript in tests/test_council.py
    f = tmp_path / "t.jsonl"
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}})]
    for k, n in enumerate(names):
        ts = dt.datetime.fromtimestamp(start + k * 10, dt.timezone.utc).isoformat().replace("+00:00", "Z")
        lines.append(json.dumps({"type": "assistant", "timestamp": ts,
                                 "message": {"content": [{"type": "tool_use", "name": n, "input": {}}]}}))
    f.write_text("\n".join(lines) + "\n")
    return str(f)


INFO = lambda skills=(): (lambda sid, review=False: {"last_log": None, "skills": list(skills)})

def run(tmp_path, monkeypatch, capsys, names, info=INFO(), sid="s1"):
    monkeypatch.setattr(hook, "STATE", tmp_path / "state")
    hook.stop_check({"session_id": sid, "transcript_path": transcript(tmp_path, names)}, info)
    out = capsys.readouterr().out
    return json.loads(out)["reason"] if out else ""

def test_review_is_asked_after_fifteen_tool_calls_and_only_once(tmp_path, monkeypatch, capsys):
    assert run(tmp_path, monkeypatch, capsys, ["Read"] * 14) == ""
    reason = run(tmp_path, monkeypatch, capsys, ["Read"] * 15)
    assert "council_skill" in reason and "council_rule" in reason and "never" in reason
    assert "session_id=s1" in reason
    assert run(tmp_path, monkeypatch, capsys, ["Read"] * 15) == ""           # same calls: not asked again
    assert run(tmp_path, monkeypatch, capsys, ["Read"] * 29) == ""           # 14 more: not yet
    assert "council_skill" in run(tmp_path, monkeypatch, capsys, ["Read"] * 30)

def test_review_names_the_skills_shown_and_joins_the_log_reminder(tmp_path, monkeypatch, capsys):
    reason = run(tmp_path, monkeypatch, capsys, ["Edit"] + ["Read"] * 15, INFO(["skills/beklet.md"]))
    assert "council_log" in reason and "council_skill_feedback" in reason and "skills/beklet.md" in reason

def test_learning_by_itself_counts_as_a_review(tmp_path, monkeypatch, capsys):
    names = ["Read"] * 15 + ["mcp__council__council_skill"] + ["Read"] * 5
    assert run(tmp_path, monkeypatch, capsys, names) == ""

def test_review_can_be_turned_off_and_is_told_to_the_server(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook, "load_config", lambda: {"review_every": 0})
    assert run(tmp_path, monkeypatch, capsys, ["Read"] * 40) == ""
    monkeypatch.setattr(hook, "load_config", lambda: {})
    asked = []
    info = lambda sid, review=False: asked.append(review) or {"last_log": None, "skills": []}
    run(tmp_path, monkeypatch, capsys, ["Read"] * 15, info, sid="s9")
    assert asked[-1] is True

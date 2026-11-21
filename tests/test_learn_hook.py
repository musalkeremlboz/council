import datetime as dt
import json

import pytest

from council import hook


@pytest.fixture(autouse=True)
def no_user_config(tmp_path, monkeypatch):
    """A developer's own config.json must not change the default review interval."""
    monkeypatch.setattr(hook, "CONFIG", tmp_path / "no-config.json")


def transcript(tmp_path, names, start=1000.0):          # same shape as _transcript in tests/test_council.py
    """``names`` entries are tool names, or (name, input) pairs for a call that carries an input."""
    f = tmp_path / "t.jsonl"
    lines = [json.dumps({"type": "user", "message": {"content": "hi"}})]
    for k, n in enumerate(names):
        n, args = n if isinstance(n, tuple) else (n, {})
        ts = dt.datetime.fromtimestamp(start + k * 10, dt.timezone.utc).isoformat().replace("+00:00", "Z")
        lines.append(json.dumps({"type": "assistant", "timestamp": ts,
                                 "message": {"content": [{"type": "tool_use", "name": n, "input": args}]}}))
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(f)


INFO = lambda skills=(): (lambda sid, review=False, read=None: {"last_log": None, "skills": list(skills)})

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

def test_review_names_the_skills_opened_and_joins_the_log_reminder(tmp_path, monkeypatch, capsys):
    reason = run(tmp_path, monkeypatch, capsys, ["Edit"] + ["Read"] * 15, INFO(["skills/beklet.md"]))
    assert "council_log" in reason and "council_skill_feedback" in reason and "skills/beklet.md" in reason
    assert "You opened these skills since the last review: skills/beklet.md. For each, report with " \
           "council_skill_feedback (name = its path) whether it helped." in reason


def test_review_without_a_skill_list_when_the_server_answer_has_none(tmp_path, monkeypatch, capsys):
    for answer in ({"last_log": None}, {"last_log": None, "skills": []}):
        info = lambda sid, review=False, read=None, a=answer: dict(a)
        reason = run(tmp_path, monkeypatch, capsys, ["Read"] * 15, info, sid="n" + str(len(answer)))
        assert "council_skill" in reason and "You opened" not in reason and "council_skill_feedback" not in reason


def test_review_names_only_skills_opened_since_the_previous_review(tmp_path, monkeypatch, capsys):
    sent = []
    def info(sid, review=False, read=None):
        sent.append(read)
        return {"last_log": None, "skills": list(read or [])}
    rd = lambda p: ("mcp__abc-123__council_read", {"path": p})
    first = [rd("skills/a.md")] + ["Read"] * 15
    reason = run(tmp_path, monkeypatch, capsys, first, info)
    assert "skills/a.md" in reason and sent[-1] == ["skills/a.md"]
    second = first + [rd("skills/b.md"), rd("skills/b.md")] + ["Read"] * 14
    reason = run(tmp_path, monkeypatch, capsys, second, info)
    assert "skills/b.md" in reason and "skills/a.md" not in reason and sent[-1] == ["skills/b.md"]


def test_opened_skills_are_counted_from_the_previous_review_not_from_a_learning_call(tmp_path, monkeypatch, capsys):
    sent = []
    info = lambda sid, review=False, read=None: sent.append(read) or {"last_log": None, "skills": list(read or [])}
    names = [("mcp__council__council_read", {"path": "skills/a.md"})] + ["Read"] * 5 \
        + ["mcp__council__council_skill_feedback"] + ["Read"] * 15
    run(tmp_path, monkeypatch, capsys, names, info)
    assert sent[-1] == ["skills/a.md"]       # the feedback call raised `reviewed`, but the read still counts


def test_read_paths_collects_council_read_inputs_under_any_server_prefix_and_skips_malformed(tmp_path):
    t = transcript(tmp_path, [
        ("mcp__council__council_read", {"path": "skills/a.md"}),
        ("mcp__0f3a-uuid__council_read", {"path": "projects/p/skills/b.md"}),
        ("council_read", {"path": "skills/a.md"}),                    # repeat
        ("mcp__council__council_read", {"path": 7}),
        ("mcp__council__council_read", {}),
        ("mcp__council__council_list", {"path": "skills/c.md"}),      # another tool
        ("Read", {"path": "skills/d.md"}),
        ("mcp__council__council_read", {"path": "skills/e.md"}),
    ])
    assert hook.read_paths(t, -1) == ["skills/a.md", "projects/p/skills/b.md", "skills/e.md"]
    assert hook.read_paths(t, 7) == ["skills/e.md"]
    assert hook.read_paths(str(tmp_path / "missing.jsonl"), -1) == []

def test_learning_by_itself_counts_as_a_review(tmp_path, monkeypatch, capsys):
    names = ["Read"] * 15 + ["mcp__council__council_skill"] + ["Read"] * 5
    assert run(tmp_path, monkeypatch, capsys, names) == ""

def test_review_can_be_turned_off_and_is_told_to_the_server(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook, "load_config", lambda: {"review_every": 0})
    assert run(tmp_path, monkeypatch, capsys, ["Read"] * 40) == ""
    monkeypatch.setattr(hook, "load_config", lambda: {})
    asked = []
    info = lambda sid, review=False, read=None: asked.append(review) or {"last_log": None, "skills": []}
    run(tmp_path, monkeypatch, capsys, ["Read"] * 15, info, sid="s9")
    assert asked[-1] is True

def test_no_review_when_the_server_does_not_answer_and_it_is_asked_later(tmp_path, monkeypatch, capsys):
    down = lambda sid, review=False, read=None: {}
    assert run(tmp_path, monkeypatch, capsys, ["Read"] * 15, down) == ""
    assert "council_skill" in run(tmp_path, monkeypatch, capsys, ["Read"] * 15)    # not consumed

def test_log_reminder_still_fires_alone_when_the_server_is_down(tmp_path, monkeypatch, capsys):
    asked = []
    down = lambda sid, review=False, read=None: asked.append(review) or {}
    reason = run(tmp_path, monkeypatch, capsys, ["Edit"] + ["Read"] * 5, down)
    assert "council_log" in reason and "council_skill" not in reason
    assert asked == [False]

def test_server_session_is_empty_not_an_error_when_unreachable(tmp_path, monkeypatch):
    assert hook.server_session("s1") == {}                                          # no config file
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"url": "http://127.0.0.1:9", "token": "t"}))        # nothing listens
    monkeypatch.setattr(hook, "CONFIG", cfg)
    assert hook.server_session("s1", review=True) == {}


def test_server_session_sends_read_only_when_given(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"url": "http://x", "token": "t"}))
    monkeypatch.setattr(hook, "CONFIG", cfg)
    sent = []

    class R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"last_log": None, "skills": ["skills/a.md"]}).encode()

    monkeypatch.setattr(hook.urllib.request, "urlopen", lambda req, **k: sent.append(json.loads(req.data)) or R())
    assert hook.server_session("s1")["skills"] == ["skills/a.md"]
    hook.server_session("s1", review=True, read=["skills/a.md"])
    assert "read" not in sent[0] and sent[1]["read"] == ["skills/a.md"]

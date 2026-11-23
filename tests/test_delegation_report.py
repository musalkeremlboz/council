import datetime as dt
import json
import os
import pytest
from council import cli, delegation
from council.delegation import PRICES, summarise

M = 1_000_000
FABLE, OPUS, SONNET = "claude-fable-5-2", "claude-opus-5-5", "claude-sonnet-5-5"
SID = "a" * 36

def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat().replace("+00:00", "Z")

def line(model, mid, t, tools=0, **usage):
    return {"type": "assistant", "timestamp": iso(t),
            "message": {"id": mid, "model": model, "usage": usage, "content": [{"type": "tool_use", "name": "Read"}] * tools}}

def session(tree, lines, sid=SID):
    f = tree / "proj" / f"{sid}.jsonl"; f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    return f

def worker(tree, name, lines, meta={"agentType": "general-purpose"}, sid=SID):
    d = tree / "proj" / sid / "subagents"; d.mkdir(parents=True, exist_ok=True)
    (d / f"agent-{name}.jsonl").write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    if meta is not None:
        (d / f"agent-{name}.meta.json").write_text(json.dumps(meta), encoding="utf-8")

def tier4(tree, log=None):
    return summarise(tree, log or tree / "none.jsonl", days=14)["tiers"]["4"]

def test_tokens_are_counted_once_per_message_and_priced_by_tier(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1000), line(FABLE, "m1", 11, output_tokens=1000)])
    worker(tmp_path, "w", [line(OPUS, "w1", 20, input_tokens=M, cache_read_input_tokens=M, cache_creation_input_tokens=M)])
    t = tier4(tmp_path)
    assert t["sessions"] == 1 and t["agents"] == 1 and t["models"][FABLE]["output"] == 1000
    opus = PRICES[3]["input"] + PRICES[3]["cache_read"] + PRICES[3]["cache_write"]
    assert t["models"][OPUS]["cost"] == pytest.approx(opus)
    assert t["cost"] == pytest.approx(opus + 1000 / M * PRICES[4]["output"])
    assert t["below_share"] == pytest.approx(opus / t["cost"])

def test_a_worker_above_the_ceiling_is_a_violation_and_a_fork_is_counted_apart(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "ok", [line(OPUS, "a", 20, output_tokens=1)])
    worker(tmp_path, "bad", [line(FABLE, "b", 20, output_tokens=1)])
    worker(tmp_path, "fork", [line(FABLE, "c", 20, output_tokens=1)], meta={"agentType": "fork"})
    worker(tmp_path, "odd", [line("gpt-9", "d", 20, output_tokens=1)], meta=None)       # unknown model, no meta file
    t = tier4(tmp_path)
    assert (t["agents"], t["violations"], t["forks"]) == (4, 1, 1)

def test_the_comparison_point_follows_a_model_switch(tmp_path):
    session(tmp_path, [line(OPUS, "m1", 0, output_tokens=1), line(FABLE, "m2", 100, output_tokens=1)])
    worker(tmp_path, "early", [line(OPUS, "a", 50, output_tokens=1)])      # main was Opus then: Opus is above the ceiling
    worker(tmp_path, "late", [line(OPUS, "b", 150, output_tokens=1)])      # main is Fable now: Opus is the ceiling
    assert tier4(tmp_path)["violations"] == 1                                # the session is filed under its last model

def test_an_unknown_comparison_model_is_no_violation(tmp_path):
    session(tmp_path, [line("gpt-9", "m1", 0, output_tokens=1), line(FABLE, "m2", 100, output_tokens=1)])
    worker(tmp_path, "early", [line(OPUS, "a", 50, output_tokens=1)])      # the hook enforced nothing then
    t = tier4(tmp_path)
    assert t["agents"] == 1 and t["violations"] == 0 and t["violations_by_reason"] == {}

def test_violations_are_broken_down_by_what_the_hook_decided(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "a", [line(FABLE, "a", 20, output_tokens=M)], meta={"agentType": "mine", "toolUseId": "toolu_a"})
    worker(tmp_path, "b", [line(FABLE, "b", 20, input_tokens=M)], meta={"agentType": "x", "toolUseId": "toolu_b"})
    worker(tmp_path, "c", [line(FABLE, "c", 20, cache_read_input_tokens=M)], meta={"agentType": "y", "toolUseId": "toolu_c"})
    worker(tmp_path, "ok", [line(OPUS, "d", 20, output_tokens=M)], meta={"agentType": "z", "toolUseId": "toolu_d"})
    log = tmp_path / "d.jsonl"
    log.write_text("\n".join(json.dumps({"session": SID[:16], "tool_use_id": u, "reason": r}) for u, r in
                             (("toolu_a", "own-model"), ("toolu_b", "unknown-main"), ("toolu_d", "set"))) + "\n",
                   encoding="utf-8")
    t = tier4(tmp_path, log)
    assert t["violations"] == 3
    assert t["violations_by_reason"] == {"own-model": 1, "unknown-main": 1, "no-decision": 1}
    assert t["violations_cost"] == pytest.approx(PRICES[4]["output"] + PRICES[4]["input"] + PRICES[4]["cache_read"])
    text = delegation.render(summarise(tmp_path, log, days=14))
    assert "above the ceiling: 3 sub-agents, $" in text and "(no-decision 1, own-model 1, unknown-main 1)" in text

def test_cache_writes_are_priced_by_their_lifetime(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "hour", [line(OPUS, "a", 20, cache_creation_input_tokens=M,
                                   cache_creation={"ephemeral_1h_input_tokens": M, "ephemeral_5m_input_tokens": 0})])
    worker(tmp_path, "both", [line(SONNET, "b", 20, cache_creation_input_tokens=3 * M,
                                   cache_creation={"ephemeral_1h_input_tokens": M, "ephemeral_5m_input_tokens": 2 * M})])
    t = tier4(tmp_path)
    assert t["models"][OPUS]["cost"] == pytest.approx(PRICES[3]["cache_write_1h"])
    assert (t["models"][OPUS]["cache_write"], t["models"][OPUS]["cache_write_1h"]) == (0, M)
    assert t["models"][SONNET]["cost"] == pytest.approx(PRICES[2]["cache_write_1h"] + 2 * PRICES[2]["cache_write"])
    assert t["estimated_saving"] == pytest.approx(PRICES[4]["cache_write_1h"] - PRICES[3]["cache_write_1h"]
                                                  + PRICES[4]["cache_write_1h"] + 2 * PRICES[4]["cache_write"]
                                                  - PRICES[2]["cache_write_1h"] - 2 * PRICES[2]["cache_write"])
    assert [PRICES[r]["cache_write_1h"] for r in (4, 3, 2, 1)] == pytest.approx([16, 8, 4, 0.20])
    assert [PRICES[r]["cache_write"] for r in (4, 3, 2, 1)] == pytest.approx([10, 5, 2.50, 0.125])
    assert "cache write 1h" in delegation.render(summarise(tmp_path, tmp_path / "none.jsonl", days=14))

def test_small_runs_and_the_estimate(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "small", [line(SONNET, "a", 20, tools=2, output_tokens=M)])
    worker(tmp_path, "big", [line(SONNET, "b", 20, tools=5), line(SONNET, "c", 21, tools=4)])
    t = tier4(tmp_path)
    assert t["small"] == 1 and t["small_share"] == 0.5
    assert t["estimated_saving"] == pytest.approx(PRICES[4]["output"] - PRICES[2]["output"])

def test_hook_decisions_are_joined_by_session_and_old_sessions_are_left_out(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    old = session(tmp_path, [line(FABLE, "m9", 10, output_tokens=1)], sid="b" * 36)
    os.utime(old, (1, 1))
    log = tmp_path / "d.jsonl"
    log.write_text("\n".join([json.dumps({"session": SID[:16], "reason": r}) for r in ("set", "set", "kept")]
                             + [json.dumps({"session": "zzz", "reason": "set"}), "{cut"]) + "\n", encoding="utf-8")
    t = tier4(tmp_path, log)
    assert t["sessions"] == 1 and t["hook"] == {"set": 2, "kept": 1}

def test_broken_lines_and_unrankable_sessions_do_not_stop_the_report(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=5), '{"type": "assistant", "message": {"id": "m2", "mo'])
    session(tmp_path, [line("gpt-9", "x", 10, output_tokens=5)], sid="c" * 36)
    tiers = summarise(tmp_path, tmp_path / "none.jsonl", days=14)["tiers"]
    assert list(tiers) == ["4"] and tiers["4"]["models"][FABLE]["output"] == 5

def test_the_command_prints_a_report_and_json(tmp_path, capsys):
    args = ["--data", str(tmp_path / "data"), "delegation", "report", "--projects", str(tmp_path),
            "--log", str(tmp_path / "none.jsonl")]
    assert cli.main(args) == 0 and "no sessions in the last 14 days" in capsys.readouterr().out
    assert not (tmp_path / "data").exists()                                 # read-only: no data folder made
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "w", [line(OPUS, "a", 20, output_tokens=1)])
    assert cli.main(args) == 0
    text = capsys.readouterr().out
    assert "upper-bound estimate" in text and delegation.PRICES_AS_OF in text and OPUS in text
    assert cli.main(args + ["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tiers"]["4"]["agents"] == 1

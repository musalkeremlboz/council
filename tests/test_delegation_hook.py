import json
import pytest
from council import hook

@pytest.fixture(autouse=True)
def no_user_config(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "CONFIG", tmp_path / "no-config.json")

@pytest.mark.parametrize("model, expected", [
    ("claude-mythos-5-2", 4), ("claude-fable-5-2", 4), ("fable", 4), ("claude-opus-5-5", 3), ("opus", 3),
    ("anthropic.claude-sonnet-5-5", 2), ("Sonnet", 2), ("claude-haiku-5-5", 1),
    ("gpt-9", 0), ("<synthetic>", 0), ("", 0), (None, 0), (7, 0)])
def test_tier_reads_the_family_name(model, expected):
    assert hook.tier(model) == expected

def record(tmp_path, lines):
    f = tmp_path / "t.jsonl"
    f.write_text("\n".join(json.dumps(x) if isinstance(x, dict) else x for x in lines) + "\n", encoding="utf-8")
    return str(f)

def assistant(model, **extra):
    return {"type": "assistant", "message": {"model": model, "content": []}, **extra}

def test_main_model_is_the_last_assistant_model(tmp_path):
    path = record(tmp_path, [assistant("claude-opus-5-5"), {"type": "user"}, assistant("claude-mythos-5-2")])
    assert hook.main_model(path) == "claude-mythos-5-2"

def test_main_model_skips_sidechains_synthetic_and_broken_lines(tmp_path):
    path = record(tmp_path, [assistant("claude-opus-5-5"), assistant("claude-haiku-5-5", isSidechain=True),
                             assistant("<synthetic>"), '{"type": "assistant", "message": {"mod'])
    assert hook.main_model(path) == "claude-opus-5-5"

def test_main_model_reads_the_request_line_before_any_reply_and_after_a_switch(tmp_path):
    request = lambda model: {"type": "api-request", "querySource": "sdk", "params": {"model": model}}
    assert hook.main_model(record(tmp_path, [{"type": "user"}, request("claude-haiku-5-5")])) == "claude-haiku-5-5"
    path = record(tmp_path, [request("claude-opus-5-5"), assistant("claude-opus-5-5"), request("claude-mythos-5-2")])
    assert hook.main_model(path) == "claude-mythos-5-2"
    assert hook.main_model(record(tmp_path, [assistant("claude-opus-5-5"), {"type": "api-request", "params": "x"}])) == "claude-opus-5-5"

def test_main_model_is_none_without_a_record_or_an_assistant_line(tmp_path):
    assert hook.main_model(str(tmp_path / "missing.jsonl")) is None
    assert hook.main_model(record(tmp_path, [{"type": "user"}])) is None

def test_main_model_reads_a_large_record_from_the_end(tmp_path, monkeypatch):
    f = tmp_path / "big.jsonl"
    pad = json.dumps({"type": "user", "message": {"content": "x" * 1000}})
    f.write_text("\n".join([json.dumps(assistant("claude-opus-5-5"))] + [pad] * 20000
                           + [json.dumps(assistant("claude-sonnet-5-5"))]) + "\n", encoding="utf-8")
    sizes = []
    class Counting:                                           # a file object that remembers every read size
        def __init__(self, fh): self.fh = fh
        def read(self, n=-1): sizes.append(n); return self.fh.read(n)
        def __getattr__(self, name): return getattr(self.fh, name)
        def __enter__(self): return self
        def __exit__(self, *a): return self.fh.__exit__(*a)
    monkeypatch.setattr(hook, "open", lambda *a, **k: Counting(open(*a, **k)), raising=False)
    assert hook.main_model(str(f)) == "claude-sonnet-5-5"
    assert sizes and all(0 < n <= 1 << 20 for n in sizes)    # bounded chunks, never the whole file

@pytest.mark.parametrize("config, expected", [
    (None, "enforce"), ({}, "enforce"), ({"delegation": "advise"}, "advise"), ({"delegation": "off"}, "off"),
    ({"delegation": "nonsense"}, "enforce"), ({"delegation": False}, "enforce")])
def test_delegation_mode(tmp_path, monkeypatch, config, expected):
    if config is not None:
        (tmp_path / "c.json").write_text(json.dumps(config))
        monkeypatch.setattr(hook, "CONFIG", tmp_path / "c.json")
    assert hook.delegation_mode() == expected

@pytest.mark.parametrize("chunk", [7, 64, 100, 1000])
def test_main_model_parses_a_line_that_straddles_chunks_or_is_longer_than_one(tmp_path, monkeypatch, chunk):
    monkeypatch.setattr(hook, "CHUNK", chunk)
    long_reply = assistant("claude-opus-5-5", note="y" * 300)
    path = record(tmp_path, [assistant("claude-haiku-5-5"), {"type": "user"}, long_reply, {"type": "user"}])
    assert hook.main_model(path) == "claude-opus-5-5"

"""Report on sub-agent delegation: what each model spent, whether the one-tier-below ceiling held, and an
estimate of the saving. Reads the assistant's local session records and the hook's decision log; writes nothing."""

from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

from .hook import DELEGATION_LOG, tier

# USD per million tokens, list prices; the cache-write multipliers were read from the pricing page on 2026-11-23.
# Haiku 5.5 prompts over 100,000 tokens are billed at a higher rate that this table does not model.
PRICES: dict[int, dict[str, float]] = {
    4: {"input": 8.00, "output": 40.00, "cache_read": 0.20, "cache_write": 8.00 * 1.25, "cache_write_1h": 8.00 * 2},
    3: {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 4.00 * 1.25, "cache_write_1h": 4.00 * 2},
    2: {"input": 2.00, "output": 10.00, "cache_read": 0.10, "cache_write": 2.00 * 1.25, "cache_write_1h": 2.00 * 2},
    1: {"input": 0.10, "output": 0.50, "cache_read": 0.01, "cache_write": 0.10 * 1.25, "cache_write_1h": 0.10 * 2},
}
PRICES_AS_OF = "2026-11-23"
DEFAULT_PROJECTS = Path("~/.claude/projects").expanduser()
DEFAULT_LOG = DELEGATION_LOG
KINDS = {"input": "input_tokens", "output": "output_tokens",
         "cache_read": "cache_read_input_tokens", "cache_write": "cache_creation_input_tokens"}
# Priced token counts: `cache_write` holds the 5-minute cache writes (or the undivided total when a line has no
# breakdown), `cache_write_1h` the 1-hour ones.
PRICED = (*KINDS, "cache_write_1h")
SMALL_RUN = 5  # a sub-agent with fewer tool calls than this is a small run


def cost(tokens: dict, rank: int) -> float:
    """List-price cost of these tokens at a tier's prices; 0 for an unknown tier."""
    prices = PRICES.get(rank)
    return sum(tokens.get(kind, 0) / 1_000_000 * prices[kind] for kind in PRICED) if prices else 0.0


def token_counts(usage: dict) -> dict[str, int]:
    """Token counts of one message's usage; cache writes split by lifetime when the usage carries the split."""
    counts = {kind: usage.get(key) if isinstance(usage.get(key), int) else 0 for kind, key in KINDS.items()}
    counts["cache_write_1h"] = 0
    split = usage.get("cache_creation")
    if isinstance(split, dict) and any(isinstance(split.get(k), int) for k in
                                       ("ephemeral_5m_input_tokens", "ephemeral_1h_input_tokens")):
        five, hour = split.get("ephemeral_5m_input_tokens"), split.get("ephemeral_1h_input_tokens")
        counts["cache_write"] = five if isinstance(five, int) else 0
        counts["cache_write_1h"] = hour if isinstance(hour, int) else 0
    return counts


def when(value: object) -> float | None:
    """Seconds since the epoch of an ISO timestamp, or None when there is no usable one."""
    if not isinstance(value, str):
        return None
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=dt.timezone.utc)
    return stamp.timestamp()


def read_record(path: Path, main: bool) -> dict:
    """Assistant lines of one record, read line by line: tokens per model (each message id once), tool calls,
    and the (time, model) timeline. Broken lines are skipped."""
    messages: dict[object, tuple[str, dict]] = {}
    timeline: list[tuple[float | None, str]] = []
    tools = 0
    try:
        fh = open(path, "rb")
    except OSError:
        return {"models": {}, "timeline": [], "tools": 0}
    with fh:
        for n, raw in enumerate(fh):
            if b'"assistant"' not in raw:
                continue
            try:
                entry = json.loads(raw)
            except ValueError:  # a cut-off or foreign line
                continue
            if not isinstance(entry, dict) or entry.get("type") != "assistant":
                continue
            if main and entry.get("isSidechain"):
                continue
            message = entry.get("message")
            if not isinstance(message, dict):
                continue
            model = message.get("model")
            if not isinstance(model, str) or not model or model.startswith("<"):
                continue
            content = message.get("content")
            if isinstance(content, list):
                tools += sum(1 for part in content if isinstance(part, dict) and part.get("type") == "tool_use")
            timeline.append((when(entry.get("timestamp")), model))
            usage = message.get("usage") if isinstance(message.get("usage"), dict) else {}
            counts = token_counts(usage)
            key = message.get("id") or ("line", n)
            if key in messages:  # the same message repeats on several lines: keep the fullest count once
                _, seen = messages[key]
                counts = {kind: max(seen[kind], counts[kind]) for kind in PRICED}
            messages[key] = (model, counts)
    models: dict[str, dict] = {}
    for model, counts in messages.values():
        total = models.setdefault(model, dict.fromkeys(PRICED, 0))
        for kind in PRICED:
            total[kind] += counts[kind]
    return {"models": models, "timeline": timeline, "tools": tools}


def agent_meta(record: Path, key: str) -> str:
    """A text field of a sub-agent's ``meta.json`` (``agentType``, ``toolUseId``); "" when there is none."""
    try:
        meta = json.loads(record.with_name(record.name[:-len(".jsonl")] + ".meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    value = meta.get(key) if isinstance(meta, dict) else None
    return value if isinstance(value, str) else ""


def model_at(timeline: list[tuple[float | None, str]], moment: float | None) -> str:
    """The main record's last model before a moment; its first model when none is earlier or there is no time."""
    found = timeline[0][1]
    if moment is None:
        return found
    for stamp, model in timeline:
        if stamp is not None and stamp < moment:
            found = model
    return found


def hook_rows(log: Path) -> tuple[dict[str, dict[str, int]], dict[str, str]]:
    """Decision-log reasons counted per 16-character session prefix, and the reason given for each tool call id."""
    rows: dict[str, dict[str, int]] = {}
    calls: dict[str, str] = {}
    try:
        fh = open(log, "rb")
    except OSError:
        return rows, calls
    with fh:
        for raw in fh:
            try:
                row = json.loads(raw)
            except ValueError:
                continue
            if not isinstance(row, dict) or not isinstance(row.get("session"), str):
                continue
            reasons = rows.setdefault(row["session"], {})
            reason = str(row.get("reason", ""))
            reasons[reason] = reasons.get(reason, 0) + 1
            if isinstance(row.get("tool_use_id"), str) and row["tool_use_id"]:
                calls[row["tool_use_id"]] = reason
    return rows, calls


def empty() -> dict:
    return {"sessions": 0, "agents": 0, "hook": {}, "models": {}, "cost": 0.0, "below_share": 0.0,
            "violations": 0, "violations_by_reason": {}, "violations_cost": 0.0, "forks": 0, "small": 0, "small_share": 0.0, "estimated_saving": 0.0}


def summarise(projects: Path, log: Path, days: float, now: float | None = None) -> dict:
    """Per main tier: sessions, sub-agents, the hook's reasons, tokens and cost per model, the share spent below
    the main tier, ceiling violations, forks, small runs and an upper-bound estimate of the saving."""
    since = (time.time() if now is None else now) - days * 86400
    decisions, calls = hook_rows(Path(log))
    tiers: dict[int, dict] = {}
    for record in sorted(Path(projects).glob("*/*.jsonl")):
        try:
            if record.stat().st_mtime < since:
                continue
        except OSError:
            continue
        main = read_record(record, main=True)
        if not main["timeline"]:
            continue
        rank = tier(main["timeline"][-1][1])
        if not rank:
            continue
        t = tiers.setdefault(rank, empty())
        t["sessions"] += 1
        for reason, count in decisions.get(record.stem[:16], {}).items():
            t["hook"][reason] = t["hook"].get(reason, 0) + count
        records = [main["models"]]
        for sub in sorted((record.parent / record.stem / "subagents").glob("agent-*.jsonl")):
            agent = read_record(sub, main=False)
            records.append(agent["models"])
            t["agents"] += 1
            if agent["tools"] < SMALL_RUN:
                t["small"] += 1
            for model, tokens in agent["models"].items():
                own = tier(model)
                if own:
                    t["estimated_saving"] += cost(tokens, rank) - cost(tokens, own)
            if not agent["timeline"]:
                continue
            own = tier(agent["timeline"][0][1])
            if not own:
                continue
            if agent_meta(sub, "agentType") == "fork":
                t["forks"] += 1
                continue
            stamps = [stamp for stamp, _ in agent["timeline"] if stamp is not None]
            then = tier(model_at(main["timeline"], min(stamps) if stamps else None))
            if then and own > max(then - 1, 1):  # under an unknown session model the hook holds nothing
                t["violations"] += 1
                reason = calls.get(agent_meta(sub, "toolUseId"), "no-decision")
                t["violations_by_reason"][reason] = t["violations_by_reason"].get(reason, 0) + 1
                t["violations_cost"] += sum(cost(tokens, tier(model)) for model, tokens in agent["models"].items())
        for models in records:
            for model, tokens in models.items():
                total = t["models"].setdefault(model, {**dict.fromkeys(PRICED, 0), "cost": 0.0})
                for kind in PRICED:
                    total[kind] += tokens[kind]
    out = {}
    for rank in sorted(tiers, reverse=True):
        t = tiers[rank]
        below = 0.0
        for model, total in t["models"].items():
            total["cost"] = cost(total, tier(model))
            t["cost"] += total["cost"]
            if tier(model) < rank:
                below += total["cost"]
        t["below_share"] = below / t["cost"] if t["cost"] else 0.0
        t["small_share"] = t["small"] / t["agents"] if t["agents"] else 0.0
        out[str(rank)] = t
    return {"days": float(days), "prices_as_of": PRICES_AS_OF, "tiers": out}


def render(summary: dict) -> str:
    days = f"{summary['days']:g}"
    if not summary["tiers"]:
        return f"Delegation report: no sessions in the last {days} days.\n"
    lines = [f"Delegation report, last {days} days"]
    for rank, t in summary["tiers"].items():
        lines += ["", f"Main tier {rank}: {t['sessions']} sessions, {t['agents']} sub-agent calls"]
        hook = ", ".join(f"{reason} {count}" for reason, count in sorted(t["hook"].items())) or "none"
        lines.append(f"  hook decisions: {hook}")
        lines.append(f"  {'model':<32} {'input':>13} {'output':>13} {'cache read':>15} {'cache write 5m':>15} "
                     f"{'cache write 1h':>15} {'cost $':>10}")
        for model, m in sorted(t["models"].items(), key=lambda item: -item[1]["cost"]):
            lines.append(f"  {model:<32} {m['input']:>13,} {m['output']:>13,} {m['cache_read']:>15,} "
                         f"{m['cache_write']:>15,} {m['cache_write_1h']:>15,} {m['cost']:>10,.2f}")
        lines.append(f"  total list-price cost: ${t['cost']:,.2f}; spent below the main tier: {t['below_share']:.1%}")
        why = ", ".join(f"{reason} {count}" for reason, count in
                        sorted(t["violations_by_reason"].items(), key=lambda item: (-item[1], item[0])))
        lines.append(f"  above the ceiling: {t['violations']} sub-agents, ${t['violations_cost']:,.2f}"
                     + (f" ({why})" if why else "") + f"; forks (run on the session's model): {t['forks']}")
        lines.append(f"  small runs (fewer than {SMALL_RUN} tool calls): {t['small']} ({t['small_share']:.0%})")
        lines.append(f"  saving at the main tier's prices: ${t['estimated_saving']:,.2f} (upper-bound estimate)")
    lines += ["", f"Prices: list prices as of {summary['prices_as_of']}, used as weights, not a bill."]
    return "\n".join(lines) + "\n"

"""Measure skill matching on a scenario file: python scripts/skill_eval.py SCENARIOS.json

Same code path as tests/test_skill_matching.py; exits 1 when either bar is missed.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from council.learn import Learning  # noqa: E402
from council.store import Store  # noqa: E402

ON_TOPIC_BAR = 0.80  # the right skill is among those offered
OFF_TOPIC_BAR = 0.20  # a skill is offered although none applies


def evaluate(data: dict, data_dir: Path) -> tuple[int, int, int, int]:
    """(on-topic hits, on-topic total, off-topic shown, off-topic total)."""
    learning = Learning(Store(data_dir))
    for s in data["skills"]:
        learning.write_skill(**s)
    hits = sum(any(m["title"] == c["expect"] for m in learning.match(c["message"])) for c in data["on_topic"])
    shown = sum(bool(learning.match(m)) for m in data["off_topic"])
    return hits, len(data["on_topic"]), shown, len(data["off_topic"])


def main(path: str) -> int:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # open files block deletion on Windows
        hits, on, shown, off = evaluate(data, Path(tmp) / "data")
    print(f"on-topic {hits}/{on} ({100 * hits / on:.0f}%)")
    print(f"off-topic {shown}/{off} ({100 * shown / off:.0f}%)")
    return 0 if hits / on >= ON_TOPIC_BAR and shown / off <= OFF_TOPIC_BAR else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/skill_eval.py SCENARIOS.json")
    sys.exit(main(sys.argv[1]))

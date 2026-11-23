"""The thirteen blocks of the schema, with rules whose numbers are read from the code at the moment they are built."""
from council import context, hook, learn, store
from council.panel import text_tr

LANES = ("start", "message", "end", "memory")

_LANE_OF = {
    "h1": "start", "bas": "start", "diz": "start",
    "h2": "message", "ara": "message", "sec": "message", "isa": "message",
    "h3": "end", "yaz": "end", "ogr": "end",
    "haf": "memory", "yed": "memory", "den": "memory",
}


def _number(n: int) -> str:
    """Turkish way: thousands separated by a dot, small numbers plain."""
    return f"{n:,}".replace(",", ".")


def _values() -> dict:
    # Read through the modules on every call, so a changed constant changes the text.
    return {name: _number(value) for name, value in {
        "START_BUDGET": context.START_BUDGET,
        "START_CARDS": context.START_CARDS,
        "MESSAGE_BUDGET": context.MESSAGE_BUDGET,
        "MESSAGE_LIMIT": context.MESSAGE_LIMIT,
        "SECTION_CLIP": context.SECTION_CLIP,
        "MIN_ROOM": context.MIN_ROOM,
        "INDEX_BUDGET": learn.INDEX_BUDGET,
        "SKILL_LIMIT": learn.SKILL_LIMIT,
        "MIN_HEAD_WORDS": learn.MIN_HEAD_WORDS,
        "PROMOTE_AFTER": learn.PROMOTE_AFTER,
        "RETIRE_WRONG": learn.RETIRE_WRONG,
        "RETIRE_NOT_HELPED": learn.RETIRE_NOT_HELPED,
        "REVIEW_EVERY": hook.REVIEW_EVERY,
        "BACKUP_GRACE_DAYS": store.BACKUP_GRACE // 86400,
    }.items()}


def blocks() -> list[dict]:
    """The blocks in drawing order: id, lane, name, sub-line, what it does, and its rules."""
    values = _values()
    fill = lambda text: text.format_map(values)
    return [
        {
            "id": block_id,
            "lane": _LANE_OF[block_id],
            "name": fill(copy["name"]),
            "sub": fill(copy["sub"]),
            "what": fill(copy["what"]),
            "rules": [fill(rule) for rule in copy["rules"]],
        }
        for block_id, copy in text_tr.BLOCKS.items()
    ]

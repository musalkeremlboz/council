import json

from conftest import ODD_FOLDER, SECRETS, remove_history

from council import check
from council.panel import reader
from council.store import Store


def everything(data):
    s = reader.open_memory(data)
    try:
        return {"notes": reader.note_list(s), "links": reader.note_links(s), "events": reader.events(data, 0),
                "usage": reader.note_usage(data), "changes": reader.changes(s, 0),
                "learn": reader.learnings(data, 0), "backup": reader.backup_state(data)}
    finally:
        s.index.db.close()


def test_the_reader_gives_paths_and_counts_and_none_of_the_text(leaky):
    out = everything(leaky)
    text = json.dumps(out, ensure_ascii=False)
    assert not [s for s in SECRETS if s in text]
    assert any(n["path"].startswith(f"projects/{ODD_FOLDER}/") for n in out["notes"])  # an odd name arrives as it is
    assert {e["kind"] for e in out["events"]} >= {"inject", "read", "search"}
    assert all(set(e) == {"ts", "kind", "chars", "paths"} for e in out["events"])
    assert out["links"] and out["changes"] and out["changes"][0]["paths"]
    assert any(f"projects/{ODD_FOLDER}/plan.md" in c["paths"] for c in out["changes"])  # git's quoting is undone
    assert {l["kind"] for l in out["learn"]} == {"rule", "skill"}
    assert [n["path"] for n in out["notes"]] == sorted(n["path"] for n in out["notes"])
    kaynak = next(n for n in out["notes"] if n["path"] == "projects/ev/kaynak.md")
    assert kaynak["sections"] == 2 and kaynak["chars"] > 0 and kaynak["skill"] is False
    assert any(n["skill"] for n in out["notes"])
    assert out["usage"]["projects/ev/kaynak.md"] == {"injected": 1, "read": 1, "found": 1}
    assert out["backup"]["failing"] is False and out["backup"]["last_ok"] is not None


def test_events_and_changes_and_learnings_honour_their_limits(leaky):
    import time

    s = reader.open_memory(leaky)
    try:
        assert len(reader.events(leaky, 0, limit=2)) == 2
        newest = reader.events(leaky, 0)
        assert [e["ts"] for e in newest] == sorted((e["ts"] for e in newest), reverse=True)
        assert reader.events(leaky, time.time() + 10) == []
        assert reader.changes(s, time.time() + 3600) == []
        assert reader.learnings(leaky, time.time() + 3600) == []
        assert reader.usage_since(leaky) is not None
        added = [p for c in reader.changes(s, 0) for p in c["added"]]
        assert "projects/ev/kaynak.md" in added
        assert reader.history(s) == reader.changes(s, 0) != []
    finally:
        s.index.db.close()


def test_a_memory_with_nothing_recorded_yet_reads_as_empty(tmp_path):
    data = tmp_path / "data"
    Store(data).index.db.close()
    remove_history(data / "vault")
    for name in ("usage.sqlite3", "learning.json", "backup.json"):
        assert not (data / name).exists()
    s = reader.open_memory(data)
    try:
        assert reader.events(data, 0) == [] and reader.note_usage(data) == {}
        assert reader.usage_since(data) is None
        assert reader.changes(s, 0) == [] and reader.learnings(data, 0) == []
        assert reader.history(s) is None  # no history to read is told apart from an empty one
        assert reader.backup_state(data) is None
        assert reader.note_list(s)  # the seed notes are still listed
    finally:
        s.index.db.close()


def test_unreadable_files_read_as_empty(leaky):
    (leaky / "learning.json").write_text("{not json")
    (leaky / "backup.json").write_text("[]")
    (leaky / "usage.sqlite3").write_bytes(b"this is not a database")
    assert reader.learnings(leaky, 0) == [] and reader.backup_state(leaky) is None
    assert reader.events(leaky, 0) == [] and reader.note_usage(leaky) == {} and reader.usage_since(leaky) is None


def test_note_links_names_where_each_link_leads_and_link_report_is_unchanged(leaky):
    s = Store(leaky, frozen=True)
    try:
        links = check.note_links(s)
        assert links["projects/ev/baglanti.md"] == ["projects/ev/kaynak.md"]  # twice written, once named; the broken one left out
        assert links["projects/ev/kaynak.md"] == []
        assert set(links) == set(s.list())
        report = check.link_report(s)
        assert report["checked"] == 3
        assert report["broken"] == [{"note": "projects/ev/baglanti.md", "target": "yok-boyle-bir-not", "maybe": []}]
    finally:
        s.index.db.close()


def test_events_can_be_filtered_by_kind_before_the_limit(panel_data):
    import time

    from council.usage import Usage

    t = time.time() - 100
    usage = Usage(panel_data / "usage.sqlite3")
    try:
        for i, kind in enumerate(["inject", "read", "inject", "read", "read"]):
            usage.record(kind, "s1", "", 1, None, [{"path": f"n{i}.md"}], ts=t + i)
    finally:
        usage.db.close()
    assert [e["paths"] for e in reader.events(panel_data, 0, kind="inject")] == [["n2.md"], ["n0.md"]]
    assert [e["paths"] for e in reader.events(panel_data, 0, limit=1, kind="inject")] == [["n2.md"]]
    assert reader.events(panel_data, 0, kind="start") == []
    assert len(reader.events(panel_data, 0)) == 5

import json, time
import pytest
from council.store import Conflict, Store, StoreError

@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "data")

def test_remove_and_move_keep_history_and_index(store):
    store.write("skills/a.md", "# A\n\nelma")
    store.move("skills/a.md", "skills/retired/a.md", "retire")
    assert "skills/retired/a.md" in store.list() and "skills/a.md" not in store.list()
    assert store.index.search("elma")[0]["path"] == "skills/retired/a.md"
    store.write("skills/b.md", "# B\n\nmuz")
    assert store.index.search("muz")[0]["path"] == "skills/b.md"
    with pytest.raises(Conflict):
        store.move("skills/retired/a.md", "skills/b.md")
    store.remove("skills/b.md", "undo")
    assert "skills/b.md" not in store.list() and store.index.search("muz") == []
    with pytest.raises(StoreError):
        store.remove("skills/b.md")
    log = store._git("log", "--format=%s").stdout
    assert "retire" in log and "undo" in log

def test_search_can_filter_paths(store):
    for i in range(12):
        store.write(f"notes/n{i}.md", "# N\n\nkiraz bahçesi")
    store.write("skills/k.md", "# K\n\nkiraz toplama")
    hits = store.index.search("kiraz", limit=2, where=lambda p: p.startswith("skills/"))
    assert [h["path"] for h in hits] == ["skills/k.md"]

"""The scene modules (brand/js/sahne/), checked by node's own test runner when node is installed; budgets and data checked here."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent / "js" / "brand_sahne.test.mjs"
JS = Path(__file__).resolve().parent.parent / "brand" / "js"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_shared_scene_guards():
    r = subprocess.run(["node", "--test", str(TESTS)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr


def test_scene_size_budget():
    files = sorted((JS / "sahne").glob("*.js"))
    assert {f.name for f in files} >= {"ortak.js", "yazi-kur.js", "cizgi-soz.js", "kurul-turu.js"}
    for f in files:
        assert f.stat().st_size <= 15360, (f.name, f.stat().st_size)


def test_features_file():
    data = json.loads((JS / "ozellikler.json").read_text(encoding="utf-8"))
    assert len(data) == 6
    assert data[0]["durum"] == "tamam" and data[0]["ad"] == "Hafıza" and data[0]["aciklama"]
    assert data[1]["durum"] == "denemede" and data[1]["ad"] == "Kişisel gelişim" and data[1]["aciklama"]
    for d in data[2:]:
        assert d["durum"] == "yolda" and d["ad"] is None
    assert {d["durum"] for d in data} <= {"tamam", "denemede", "yolda"}


def test_scenes_use_no_color_literals_and_no_glyph_table():
    for f in (JS / "sahne").glob("*.js"):
        src = re.sub(r'href="#[^"]+"|url\(#[^)]+\)', "", f.read_text(encoding="utf-8"))
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", src), f.name
        assert not re.search(r"\b(rgb|rgba|hsl|hsla)\(", src), f.name
    yazi = (JS / "sahne" / "yazi-kur.js").read_text(encoding="utf-8")
    assert "noktalar" in yazi and "glifler" in yazi
    assert not re.search(r"\b(bar|ring|poly)\(|new G\(", yazi)

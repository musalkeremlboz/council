"""The scene modules (brand/js/sahne/), checked by node's own test runner when node is installed; budgets and data checked here."""
import json
import re
import shutil
import subprocess
import tempfile
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
        assert d == {"ad": None, "durum": "yolda"}
    assert data[0]["en"]["ad"] == "Memory" and data[1]["en"]["ad"] == "Personal development"
    for d in data[:2]:
        assert d["en"]["ad"] and d["en"]["aciklama"], d
    assert {d["durum"] for d in data} <= {"tamam", "denemede", "yolda"}


def test_scenes_use_no_color_literals_and_no_glyph_table():
    for f in (JS / "sahne").glob("*.js"):
        src = re.sub(r'href="#[^"]+"|url\(#[^)]+\)', "", f.read_text(encoding="utf-8"))
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b", src), f.name
        assert not re.search(r"\b(rgb|rgba|hsl|hsla)\(", src), f.name
    yazi = (JS / "sahne" / "yazi-kur.js").read_text(encoding="utf-8")
    assert "noktalar" in yazi and "glifler" in yazi
    assert not re.search(r"\b(bar|ring|poly)\(|new G\(", yazi)


def _denetle():
    import importlib.util
    spec = importlib.util.spec_from_file_location("denetle", JS.parent / "denetle.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _soz_olcumu(tmp_path: Path, denetle) -> list[tuple[str, float, float, float]]:
    """Each word line of the söz form, per language, in headless Chrome: (name, text width, path length, letter spacing)."""
    css = (JS.parent / "css").resolve().as_uri()
    govde = ""
    for dil in ("tr", "en"):
        r = subprocess.run(["node", str(JS / "parca.mjs"), dil], capture_output=True, text=True, encoding="utf-8", check=True)
        govde += f'<div class="s-cs__amblem" data-dil="{dil}">{json.loads(r.stdout)["cizgiSoz"]["soz"]}</div>'
    sayfa = tmp_path / "soz.html"
    sayfa.write_text(
        f'<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="{css}/tokens.css">'
        f'<link rel="stylesheet" href="{css}/council.css"><body style="width:400px">{govde}<script>'
        'document.fonts.load(\'20px "Council Halka"\').then(() => document.fonts.ready).then(() => {'
        'document.documentElement.dataset.olcum = [...document.querySelectorAll("textPath")].map((t) => {'
        'const a = t.closest("[data-dil]").dataset.dil + "-" + t.getAttribute("href").split("-").pop();'
        'const y = document.querySelector(t.getAttribute("href")).getTotalLength();'
        'return [a, t.parentNode.getComputedTextLength(), y, parseFloat(t.parentNode.style.letterSpacing)].join(":"); }).join(",");'
        '});</script>', encoding="utf-8")
    with tempfile.TemporaryDirectory() as profil:
        r = subprocess.run([denetle.chrome_yolu(), *denetle.ORTAK, f"--user-data-dir={profil}", "--window-size=600,900",
                            "--virtual-time-budget=4000", "--dump-dom", sayfa.as_uri()],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
    m = re.search(r'data-olcum="([^"]+)"', r.stdout)
    assert m, r.stderr[-400:]
    return [(a, float(w), float(y), float(s)) for a, w, y, s in (x.split(":") for x in m.group(1).split(","))]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_soz_words_fill_their_paths_in_every_language(tmp_path):
    denetle = _denetle()
    if denetle.chrome_yolu() is None:
        pytest.skip("Chrome is not installed")
    olcum = _soz_olcumu(tmp_path, denetle)
    assert len(olcum) == 8
    for ad, genislik, yol, ara in olcum:
        # Text past the path's end is not drawn; the last letter's own spacing may hang over. A short line leaves a gap.
        assert yol - 6 <= genislik <= yol + ara + 0.5, (ad, round(genislik, 1), round(yol, 1))

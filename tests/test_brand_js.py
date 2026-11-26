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


def _tur_etiketleri(tmp_path: Path, denetle, genislik: int, azalt: bool) -> list[dict]:
    """Every Kurul turu label box (user units, after its shift) in both languages, in headless Chrome at `genislik` px."""
    css, js = (JS.parent / "css").resolve().as_uri(), JS.resolve().as_uri()
    bolum = '<section class="s-tur" id="tur-{d}" data-dil="{d}"><div class="s-tur__sahne"><figure class="s-tur__gorsel">' \
            '<svg class="s-tur__svg" viewBox="-120 -70 640 540" role="img"></svg></figure><div class="s-tur__metin">' \
            '<div class="s-tur__paneller">' + '<article class="s-tur__panel"><p>-</p></article>' * 6 + '</div></div></div></section><p>-</p>'
    sayfa = tmp_path / f"tur-{genislik}-{int(azalt)}.html"
    sayfa.write_text(
        f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f'<link rel="stylesheet" href="{css}/tokens.css"><link rel="stylesheet" href="{css}/council.css">'
        # headless --dump-dom gives no animation frames; timers stand in for them
        '<script>requestAnimationFrame = (cb) => setTimeout(() => cb(performance.now()), 16); cancelAnimationFrame = clearTimeout;</script>'
        f'<body><main class="c-kap">{bolum.format(d="tr")}{bolum.format(d="en")}</main><script type="module">'
        f'import {{ baslat }} from "{js}/sahne/kurul-turu.js";\n'
        f'const j = (y) => fetch("{js}/" + y).then((r) => r.json()), bekle = (ms) => new Promise((r) => setTimeout(r, ms));\n'
        'const [oz, metin] = await Promise.all([j("ozellikler.json"), j("metin.json")]);\n'
        'await document.fonts.ready;\n'
        'for (const s of document.querySelectorAll(".s-tur")) baslat(s, oz, metin[s.dataset.dil].kurulTuru, s.dataset.dil);\n'
        'for (const s of document.querySelectorAll(".s-tur")) { scrollTo(0, s.offsetTop + innerHeight); await bekle(600); }\n'
        'const kutular = [...document.querySelectorAll(".s-tur__svg")].filter((svg) => svg.getBoundingClientRect().width > 0).flatMap((svg) => {\n'
        '  const vb = svg.viewBox.baseVal, r = svg.getBoundingClientRect(), k = Math.min(r.width / vb.width, r.height / vb.height);\n'
        '  const lg = svg.querySelector(".s-tur__etiketler"), px = lg.getAttribute("font-size") * k;\n'
        '  return [...lg.querySelectorAll("text, path")].map((e) => {\n'
        '    const b = e.getBBox(), t = e.parentNode.transform.baseVal.consolidate()?.matrix.e || 0;\n'
        '    return { dil: svg.closest(".s-tur").dataset.dil, ad: e.textContent || "(çizgiler)", x0: b.x + t, x1: b.x + b.width + t,\n'
        '             y0: b.y, y1: b.y + b.height, sol: vb.x, sag: vb.x + vb.width, px };\n'
        '  });\n'
        '});\n'
        'const v = encodeURIComponent(JSON.stringify(kutular));\n'
        'document.documentElement.dataset.olcum = v;\n'
        'if (parent !== window) parent.document.documentElement.dataset.olcum = v;\n'
        '</script>', encoding="utf-8")
    adres = sayfa.as_uri()
    if genislik < denetle.ASGARI:   # headless Chrome opens no narrower window: the page goes in an iframe of that width
        sarmal = tmp_path / f"sarmal-{genislik}-{int(azalt)}.html"
        sarmal.write_text(f'<!doctype html><style>body{{margin:0}}iframe{{border:0;display:block}}</style>'
                          f'<iframe width="{genislik}" height="900" src="{adres}"></iframe>', encoding="utf-8")
        adres = sarmal.as_uri()
    args = [f"--window-size={max(genislik, denetle.ASGARI)},900", "--virtual-time-budget=8000", "--dump-dom", adres]
    if azalt:
        args.insert(0, "--force-prefers-reduced-motion")
    with tempfile.TemporaryDirectory() as profil:
        r = subprocess.run([denetle.chrome_yolu(), *denetle.ORTAK, f"--user-data-dir={profil}", *args],
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
    m = re.search(r'data-olcum="([^"]+)"', r.stdout)
    assert m, r.stderr[-400:]
    from urllib.parse import unquote
    return json.loads(unquote(m.group(1)))


@pytest.mark.parametrize("azalt", [False, True], ids=["canli", "durgun"])
def test_tour_labels_stay_in_view_and_off_the_ring(tmp_path, azalt):
    denetle = _denetle()
    if denetle.chrome_yolu() is None:
        pytest.skip("Chrome is not installed")
    for genislik in (320, 375, 760, 1280):
        kutular = _tur_etiketleri(tmp_path, denetle, genislik, azalt)
        assert {k["dil"] for k in kutular} == {"tr", "en"}, genislik
        assert len(kutular) >= 2 * 13, (genislik, len(kutular))   # six names, six states, "devices"
        for k in kutular:
            yer = (genislik, k["dil"], k["ad"], round(k["x0"], 1), round(k["x1"], 1))
            # The svg shows overflow; a label past the view box is cut at the screen edge on a phone.
            assert k["sol"] - 0.5 <= k["x0"] and k["x1"] <= k["sag"] + 0.5, yer
            assert k["px"] >= 11.99, (yer, k["px"])   # labels never go below the type scale's 12px
            if genislik >= 375:
                # the box keeps clear of the ring's outer edge (r 182); at 320 px the long EN states only touch it
                dx, dy = max(k["x0"] - 200, 0, 200 - k["x1"]), max(k["y0"] - 200, 0, 200 - k["y1"])
                assert (dx * dx + dy * dy) ** 0.5 >= 182, yer

"""The living example page's markup (brand/ornek/), checked without a browser."""
import json
import re
import importlib.util
from html.parser import HTMLParser
from pathlib import Path

BRAND = Path(__file__).resolve().parent.parent / "brand"
ORNEK = BRAND / "ornek" / "index.html"
ADIMLAR = ["Amblem", "Altı özellik", "Hafıza", "Kişisel gelişim", "Yolda", "1.0.0"]   # the spec's six Kurul turu steps


def _amblem():
    spec = importlib.util.spec_from_file_location("amblem", BRAND / "logo" / "amblem.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sayfa():
    return ORNEK.read_text(encoding="utf-8")


def _paneller():
    """Each .s-tur__panel as {etiket, baslik, metin}."""
    out = []

    class P(HTMLParser):
        alan = None

        def handle_starttag(self, tag, attrs):
            sinif = (dict(attrs).get("class") or "").split()
            if tag == "article" and "s-tur__panel" in sinif:
                out.append({"etiket": "", "baslik": "", "metin": ""})
            elif out and tag == "p" and "yazi-etiket" in sinif:
                self.alan = "etiket"
            elif out and tag == "h3":
                self.alan = "baslik"
            elif out and tag == "p":
                self.alan = "metin"

        def handle_endtag(self, tag):
            if tag in ("p", "h3"):
                self.alan = None

        def handle_data(self, data):
            if self.alan:
                out[-1][self.alan] += data

    P().feed(_sayfa())
    return out


def test_kurul_turu_panels_are_the_six_steps():
    paneller = _paneller()
    assert [p["baslik"] for p in paneller] == ADIMLAR
    for i, p in enumerate(paneller, 1):
        assert p["etiket"].startswith(f"{i} / 6"), p
        assert p["metin"].strip(), p


def test_kurul_turu_feature_steps_follow_the_features_file():
    oz = json.loads((BRAND / "js" / "ozellikler.json").read_text(encoding="utf-8"))
    paneller = _paneller()
    durum = {"tamam": "TAMAM", "denemede": "DENEMEDE", "yolda": "YOLDA"}
    for panel, ozellik in zip(paneller[2:4], oz[:2]):
        assert panel["baslik"] == ozellik["ad"]
        assert panel["metin"] == ozellik["aciklama"]
        assert panel["etiket"].endswith(durum[ozellik["durum"]])
    yolda = [o for o in oz if o["durum"] == "yolda"]
    assert paneller[4]["etiket"].endswith("YOLDA") and yolda
    assert "Adı henüz yazılmadı" not in _sayfa()


def test_header_logo_builds_itself_and_is_the_logo_file():
    sayfa = _sayfa()
    m = re.search(r'<div class="o-logo"[^>]*data-yazi-kur[^>]*>(<svg .*?</svg>)</div>', sayfa)
    assert m, "the header logo is inline and marked data-yazi-kur"
    assert m.group(1) == _amblem().satir_ici_logo((BRAND / "logo" / "council-logo.svg").read_text(encoding="utf-8"))
    assert not re.search(r"#[0-9A-Fa-f]{3,8}\b", m.group(1).replace("url(#ust-kesik)", ""))
    for rol in ("kor", "c", "isaret", "yazi"):
        assert f'data-kur="{rol}"' in m.group(1)


def _build():
    import importlib.util
    spec = importlib.util.spec_from_file_location("brand_build", BRAND / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_page_loads_only_the_glyphs_it_builds():
    b = _build()
    yol = BRAND / "ornek" / "glifler.json"
    assert yol.read_text(encoding="utf-8") == b.ornek_glifleri(), "run python brand/build.py"
    sayfa = _sayfa()
    assert 'data-glifler="glifler.json"' in sayfa and "../font/glifler.json" not in sayfa
    assert '<link rel="preload" href="glifler.json" as="fetch" crossorigin>' in sayfa
    alt = json.loads(yol.read_text(encoding="utf-8"))
    metinler = b.kurulan_metinler(sayfa)
    assert "COUNCIL" in metinler and "Birçok üye, tek hafıza" in metinler
    for m in metinler:
        for ch in m:
            assert ch in alt["harita"] and alt["harita"][ch] in alt["glifler"], ch
    assert {"space", "question"} <= set(alt["glifler"])
    assert yol.stat().st_size < (BRAND / "font" / "glifler.json").stat().st_size / 3


def test_glyph_subset_keeps_turkish_capitals():
    b = _build()
    veri = json.loads((BRAND / "font" / "glifler.json").read_text(encoding="utf-8"))
    alt = b.glif_altkumesi(veri, ["bir hafıza"])
    assert {"İ", "I", "i", "ı"} <= set(alt["harita"])
    assert set(alt["harita"]) <= set("bir hafıza BİR HAFIZA")
    assert {k: v for k, v in alt.items() if k not in ("harita", "glifler")} == \
        {k: v for k, v in veri.items() if k not in ("harita", "glifler")}


def test_identity_moment_starts_before_the_features_fetch():
    js = (BRAND / "ornek" / "sahneler.js").read_text(encoding="utf-8")
    assert js.index("yaziKur(document)") < js.index("fetch(")
    assert "await yaziKur" not in js


def _bosluksuz(s: str) -> str:
    return re.sub(r"\s+", "", s)


def test_logo_kur_fragment_is_the_example_header_logo():
    m = re.search(r'<div class="o-logo"[^>]*>(<svg .*?</svg>)</div>', _sayfa())
    assert m
    parca = (BRAND / "logo" / "council-logo-kur.html").read_text(encoding="utf-8")
    assert _bosluksuz(parca) == _bosluksuz(m.group(1))
    assert 'data-kur="yazi" data-metin="COUNCIL" data-ara="60"' in parca
    assert 'fill="white"' in parca and 'stroke="black"' in parca


def test_example_page_uses_the_check_module():
    sayfa = _sayfa()
    assert 'import { denetimKur } from "../js/denetim.js"' in sayfa
    assert "MutationObserver" not in sayfa and "data-tasma" not in sayfa, "the inline check block is gone"
    assert "denetimKur();" in sayfa
    assert re.search(r'class="o-logo"[^>]*data-denetim-logo', sayfa)
    assert re.search(r'id="sahneler"[^>]*data-denetim-sahne', sayfa)


def test_checker_takes_any_page(tmp_path):
    import shutil
    import sys
    import pytest
    sys.path.insert(0, str(BRAND))
    import denetle
    ek = denetle._argumanlar(["cikti", "--sayfa", "a/index.html", "--sayfa", "b/index.html"])
    assert [str(x) for x in ek.sayfa] == ["a/index.html", "b/index.html"]
    assert denetle._argumanlar(["cikti"]).sayfa is None
    if denetle.chrome_yolu() is None:
        pytest.skip("Chrome is not installed")
    kopya = tmp_path / "ornek"
    shutil.copytree(BRAND / "ornek", kopya)
    shutil.copytree(BRAND / "js", tmp_path / "js")
    shutil.copytree(BRAND / "css", tmp_path / "css")
    assert denetle.tasma_var_mi(kopya / "index.html", 1280) is False

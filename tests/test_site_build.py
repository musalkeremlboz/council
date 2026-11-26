"""site/build.py: four pages, language pairs, text key parity, tool counts, features, reproducibility, asset links."""
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

KOK = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _yukle(ad: str, yol: Path):
    """Load a module by path (site/ and brand/ are not packages; `site` is also a stdlib name)."""
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


build = _yukle("site_build", KOK / "site" / "build.py")

SAYFA_DOSYALARI = {
    ("ana", "tr"): "index.html",
    ("ana", "en"): "en/index.html",
    ("hafiza", "tr"): "hafiza/index.html",
    ("hafiza", "en"): "en/memory/index.html",
}


@pytest.fixture(scope="module")
def cikti(tmp_path_factory) -> Path:
    hedef = tmp_path_factory.mktemp("cikti")
    assert build.main(["--cikti", str(hedef)]) == 0
    return hedef


def _oku(cikti: Path, dosya: str) -> str:
    return (cikti / dosya).read_text(encoding="utf-8")


def _cozumle(cikti: Path, sayfa: str, href: str) -> Path:
    """The file a relative href on page `sayfa` points at (a folder means its index.html)."""
    yol = urlsplit(href).path
    hedef = (cikti / sayfa).parent / yol if yol else cikti / sayfa
    if yol.endswith("/") or hedef.is_dir():
        hedef = hedef / "index.html"
    return hedef.resolve()


def test_builds_four_pages(tmp_path):
    hedef = tmp_path / "cikti"
    assert build.main(["--cikti", str(hedef)]) == 0
    for (_, dil), dosya in SAYFA_DOSYALARI.items():
        html = _oku(hedef, dosya)
        assert re.search(rf'<html lang="{dil}"', html), dosya


def test_hreflang_pairs(cikti):
    for (ad, dil), dosya in SAYFA_DOSYALARI.items():
        html = _oku(cikti, dosya)
        kendi = build.SITE_URL + "/" + build.SAYFALAR[ad][dil]
        assert re.findall(r'<link rel="canonical" href="([^"]+)">', html) == [kendi], dosya
        alternatif = dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)">', html))
        assert alternatif == {
            "tr": build.SITE_URL + "/" + build.SAYFALAR[ad]["tr"],
            "en": build.SITE_URL + "/" + build.SAYFALAR[ad]["en"],
            "x-default": build.SITE_URL + "/" + build.SAYFALAR[ad]["tr"],
        }, dosya


def test_language_switch_goes_to_same_page(cikti):
    for (ad, dil), dosya in SAYFA_DOSYALARI.items():
        diger = "en" if dil == "tr" else "tr"
        html = _oku(cikti, dosya)
        baglantilar = re.findall(rf'<a href="([^"]+)" hreflang="{diger}" lang="{diger}">', html)
        assert baglantilar, dosya
        for href in baglantilar:
            assert _cozumle(cikti, dosya, href) == (cikti / SAYFA_DOSYALARI[(ad, diger)]).resolve(), (dosya, href)


def test_key_mismatch_stops_build(tmp_path, monkeypatch):
    klasor = tmp_path / "metin"
    klasor.mkdir()
    for dil in build.DILLER:
        (klasor / f"{dil}.json").write_text((build.METIN / f"{dil}.json").read_text(encoding="utf-8"), encoding="utf-8")
    en = json.loads((klasor / "en.json").read_text(encoding="utf-8"))
    en["site"]["fazladan"] = "extra"
    (klasor / "en.json").write_text(json.dumps(en, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(build, "METIN", klasor)
    with pytest.raises(SystemExit, match=r"metin: en fazla anahtar: site\.fazladan"):
        build.metin_yukle()


def test_key_missing_stops_build(tmp_path, monkeypatch):
    klasor = tmp_path / "metin"
    klasor.mkdir()
    for dil in build.DILLER:
        (klasor / f"{dil}.json").write_text((build.METIN / f"{dil}.json").read_text(encoding="utf-8"), encoding="utf-8")
    en = json.loads((klasor / "en.json").read_text(encoding="utf-8"))
    del en["site"]["atla"]
    (klasor / "en.json").write_text(json.dumps(en, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(build, "METIN", klasor)
    with pytest.raises(SystemExit, match=r"metin: en eksik anahtar: site\.atla"):
        build.metin_yukle()


def test_tool_counts():
    kaynak = (KOK / "council" / "server.py").read_text(encoding="utf-8")
    toplam = len(re.findall(r"^\s*@mcp\.tool\b", kaynak, flags=re.M))
    assert toplam == 12
    assert build.arac_sayilari() == (toplam - 4, 4)


def test_tool_counts_need_the_learning_tools(tmp_path, monkeypatch):
    sunucu = tmp_path / "server.py"
    sunucu.write_text("@mcp.tool()\ndef council_rule():\n    pass\n", encoding="utf-8")
    monkeypatch.setattr(build, "SUNUCU", sunucu)
    with pytest.raises(SystemExit, match="council_skill"):
        build.arac_sayilari()


def test_version_from_pyproject():
    import tomllib
    proje = tomllib.loads((KOK / "pyproject.toml").read_text(encoding="utf-8"))
    assert build.surum() == proje["project"]["version"]


def test_features_in_each_language():
    tr, en = build.ozellikler("tr"), build.ozellikler("en")
    assert tr[0] == {"ad": "Hafıza", "aciklama": tr[0]["aciklama"], "durum": "tamam"}
    assert en[0]["ad"] == "Memory" and en[1]["ad"] == "Personal development"
    assert en[2] == {"ad": None, "aciklama": None, "durum": "yolda"}
    assert [o["durum"] for o in tr] == [o["durum"] for o in en]


def test_named_feature_without_en_stops_build():
    yol = FIXTURES / "site-ozellikler-adsiz-en.json"
    assert build.ozellikler("tr", yol)[2]["ad"] == "Yeni özellik"
    with pytest.raises(SystemExit, match="ozellikler: Yeni özellik için en yok"):
        build.ozellikler("en", yol)


def _dosyalar(klasor: Path) -> dict[str, bytes]:
    return {p.relative_to(klasor).as_posix(): p.read_bytes() for p in sorted(klasor.rglob("*")) if p.is_file()}


def test_reproducible(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    assert build.main(["--cikti", str(a)]) == 0
    assert build.main(["--cikti", str(b)]) == 0
    assert _dosyalar(a) == _dosyalar(b)


def test_old_asset_folders_are_removed(tmp_path):
    hedef = tmp_path / "cikti"
    eski = hedef / "varlik" / "0123456789"
    eski.mkdir(parents=True)
    (eski / "eski.css").write_text("x", encoding="utf-8")
    assert build.main(["--cikti", str(hedef)]) == 0
    assert not eski.exists()
    assert len(list((hedef / "varlik").iterdir())) == 1


def test_asset_folder_layout(cikti):
    (varlik,) = (cikti / "varlik").iterdir()
    assert re.fullmatch(r"[0-9a-f]{10}", varlik.name)
    for yol in ("css/tokens.css", "css/council.css", "css/site.css", "font/CouncilHalka.woff2", "font/OFL-DMSans.txt",
                "logo/favicon.svg", "logo/council-ikon-180.png", "simge/hafiza.svg", "js/sahne/yazi-kur.js",
                "js/ozellikler.json", "js/metin.json", "js/denetim.js", "js/site.js", "glifler.json"):
        assert (varlik / yol).is_file(), yol
    for yok in ("font/build_font.py", "font/glifler.json"):
        assert not (varlik / yok).exists(), yok
    assert not [p for p in varlik.rglob("*") if "kasa" in p.name]


def test_glyph_subset_covers_the_built_text(cikti):
    (varlik,) = (cikti / "varlik").iterdir()
    veri = json.loads((varlik / "glifler.json").read_text(encoding="utf-8"))
    for harf in "COUNCILTekhafızaMemory":
        assert harf in veri["harita"], harf
    assert len(veri["glifler"]) < len(json.loads((KOK / "brand/font/glifler.json").read_text(encoding="utf-8"))["glifler"])


def test_relative_asset_links(cikti):
    for dosya in SAYFA_DOSYALARI.values():
        html = _oku(cikti, dosya)
        etiketler = [m.group(0) for m in re.finditer(r"<(?:link|script|img|source)\b[^>]*>", html)]
        kaynaklar = []
        for etiket in etiketler:
            if re.search(r'rel="(?:canonical|alternate)"', etiket):
                continue
            kaynaklar += re.findall(r'\b(?:href|src)="([^"]+)"', etiket)
        assert kaynaklar, dosya
        for href in kaynaklar:
            assert not urlsplit(href).scheme and not href.startswith("//"), (dosya, href)
            assert _cozumle(cikti, dosya, href).is_file(), (dosya, href)
        for rel in ("tokens.css", "council.css", "site.css"):
            assert re.search(rf'<link rel="stylesheet" href="(?:\.\./)*varlik/[0-9a-f]{{10}}/css/{rel}">', html), (dosya, rel)
        sira = [html.index(f"css/{rel}") for rel in ("tokens.css", "council.css", "site.css")]
        assert sira == sorted(sira), dosya


def test_shell_header_and_footer(cikti):
    for (ad, dil), dosya in SAYFA_DOSYALARI.items():
        html = _oku(cikti, dosya)
        assert re.search(r'<a class="s-logo" href="[^"]+" data-yazi-kur data-denetim-logo[^>]*><svg ', html), dosya
        assert html.count("data-yazi-kur") >= 2, dosya   # header logo + page heading
        assert '<nav class="c-gezinme"' in html
        assert 'href="https://github.com/musalkeremlboz/council"' in html
        alt = "© 2026 COUNCIL · MIT lisansı" if dil == "tr" else "© 2026 COUNCIL · MIT license"
        assert alt in html, dosya
        assert ("Hafıza" if dil == "tr" else "Memory") in re.search(r"<nav class=\"c-gezinme\".*?</nav>", html, re.S).group(0)
        assert re.search(r'<meta name="description" content="[^"]{40,}">', html), dosya
        assert re.search(r"<title>[^<]+</title>", html), dosya
        for og in ("title", "description", "url", "image", "locale"):
            assert re.search(rf'<meta property="og:{og}" content="[^"]+">', html), (dosya, og)
        assert re.search(r'<link rel="preload" href="(?:\.\./)*varlik/[0-9a-f]{10}/glifler\.json" as="fetch" crossorigin>', html)
        assert '<main id="icerik"' in html and 'href="#icerik"' in html
        if ad == "hafiza":
            assert re.search(r'<a href="[^"]+" aria-current="page">' + ("Hafıza" if dil == "tr" else "Memory"), html)

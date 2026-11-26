"""site/build.py: four pages, language pairs, text key parity, tool counts, features, reproducibility, asset links."""
import gzip
import html as html_lib
import importlib.util
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
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


# Home page (Task 5)

ANA = {"tr": "index.html", "en": "en/index.html"}
KUR_CUMLESI = {
    "tr": "Şu yönergeyi oku ve COUNCIL'i kur:\nhttps://raw.githubusercontent.com/musalkeremlboz/council/main/INSTALL.md",
    "en": "Read these instructions and set up COUNCIL:\nhttps://raw.githubusercontent.com/musalkeremlboz/council/main/INSTALL.md",
}
SAHNE_METIN = json.loads((KOK / "brand" / "js" / "metin.json").read_text(encoding="utf-8"))


def _bolum(html: str, acilis: str) -> str:
    """The element that starts with `acilis` (an opening tag prefix) up to its matching </section>."""
    bas = html.index(acilis)
    derinlik = 0
    for m in re.finditer(r"<(/?)section\b", html[bas:]):
        derinlik += -1 if m.group(1) else 1
        if derinlik == 0:
            return html[bas:html.index(">", bas + m.end()) + 1]
    raise AssertionError(f"{acilis} is not closed")


def test_home_order(cikti):
    for dil, dosya in ANA.items():
        html = _oku(cikti, dosya)
        sira = [html.index(f'id="{k}"') for k in ("icerik", "cizgi-soz-bolum", "ne-ise-yarar", "kurul-turu", "urunler")]
        assert sira == sorted(sira), (dosya, sira)
        assert html.index("data-yazi-kur data-glifler", html.index('id="icerik"')) < sira[1], dosya   # hero first
        assert re.search(r'<section id="cizgi-soz-bolum" data-denetim-sahne\b', html), dosya
        tur = _bolum(html, '<section class="s-tur" id="kurul-turu"')
        assert re.match(r'\s*<div id="kurul-sonu"', html[html.index(tur) + len(tur):]), dosya   # the skip link's target


def test_hero(cikti):
    for dil, dosya in ANA.items():
        html = _oku(cikti, dosya)
        h1 = re.findall(r'<h1 class="yazi-baslik-xl" data-yazi-kur data-glifler="((?:\.\./)*varlik/[0-9a-f]{10}/glifler\.json)">'
                        r"([^<]+)</h1>", html)
        assert [t for _, t in h1] == [build.metin_yukle()[dil]["site"]["slogan"]], dosya
        assert _cozumle(cikti, dosya, h1[0][0]).is_file()
        assert re.search(r'<a class="c-dugme c-dugme--b c-dugme--ikincil" href="https://github\.com/musalkeremlboz/council">GitHub</a>',
                         html), dosya


def test_one_kor_on_home(cikti):
    for dil, dosya in ANA.items():
        html = _oku(cikti, dosya)
        assert html.count("c-dugme--kor") == 1, dosya
        dugme = re.search(r'<button type="button" class="c-dugme c-dugme--b c-dugme--kor"([^>]*)>([^<]+)</button>', html)
        assert dugme, dosya
        assert 'data-kopyala="kur-cumlesi"' in dugme.group(1)
        assert dugme.group(2) == {"tr": "Kurulum cümlesini kopyala", "en": "Copy the setup sentence"}[dil]
        for oz in ("data-tamam", "data-hata"):
            assert re.search(rf'{oz}="[^"]+"', dugme.group(1)), (dosya, oz)


def test_install_sentence_is_text(cikti):
    for dil, dosya in ANA.items():
        kod = re.findall(r'<pre><code id="kur-cumlesi">(.*?)</code></pre>', _oku(cikti, dosya), re.S)
        assert [html_lib.unescape(k) for k in kod] == [KUR_CUMLESI[dil]], dosya


def test_what_it_does_four_items(cikti):
    for dosya in ANA.values():
        bolum = _bolum(_oku(cikti, dosya), '<section id="ne-ise-yarar"')
        maddeler = re.findall(r"<li\b.*?</li>", bolum, re.S)
        assert len(maddeler) == 4, dosya
        for madde, simge in zip(maddeler, ("hafiza", "ogrenme", "telefon", "not")):
            svg = (KOK / "brand" / "simge" / f"{simge}.svg").read_text(encoding="utf-8")
            yol = re.search(r'viewBox="0 0 24 24"[^>]*>(.*)</svg>', svg).group(1)
            assert yol in madde, (dosya, simge)
            assert re.search(r"<h3\b[^>]*>[^<]+</h3>", madde) and re.search(r"<p\b[^>]*>[^<]+</p>", madde), (dosya, simge)
        assert "c-kart" not in bolum


def test_six_tour_panels(cikti):
    for dil, dosya in ANA.items():
        tur = _bolum(_oku(cikti, dosya), '<section class="s-tur" id="kurul-turu"')
        paneller = re.findall(r'<article class="s-tur__panel">(.*?)</article>', tur, re.S)
        assert len(paneller) == 6, dosya
        etiketler = [re.search(r'<p class="yazi-etiket">([^<]+)</p>', p).group(1) for p in paneller]
        durum = SAHNE_METIN[dil]["kurulTuru"]["durum"]
        assert durum["tamam"].casefold() in etiketler[2].casefold(), etiketler
        assert durum["denemede"].casefold() in etiketler[3].casefold(), etiketler
        assert durum["yolda"].casefold() in etiketler[4].casefold(), etiketler
        assert [e.split(" ")[0] for e in etiketler] == [str(i) for i in range(1, 7)], etiketler
        for p in paneller:
            assert re.search(r'<h3 class="yazi-baslik-m">[^<]+</h3><p class="yazi-govde-l">[^<]+</p>', p), p
            assert "{" not in p, p   # every placeholder filled
        assert re.search(r'<svg class="s-tur__svg" viewBox="-120 -70 640 540" role="img" aria-label="[^"]+">', tur)
        assert 'class="ia" href="' in tur and 'class="ik" href="' in tur


def test_tour_end_counts(cikti):
    temel, ogrenme = build.arac_sayilari()
    for dil, dosya in ANA.items():
        html = _oku(cikti, dosya)
        son = re.search(r'<div id="kurul-sonu"[^>]*>(.*?)</div>', html, re.S).group(1)
        assert build.surum() in son, dosya
        beklenen = {"tr": f"{temel} temel araç + {ogrenme} kişisel gelişim aracı (denemede)",
                    "en": f"{temel} core tools + {ogrenme} personal-development tools (in trial)"}[dil]
        assert beklenen in html_lib.unescape(son), (dosya, son)


class _Metin(HTMLParser):
    """Visible text and accessible names of a page, outside lang="tr" elements and <script>/<style>."""

    BOS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr",
           "path", "rect", "circle", "line", "image"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.yigin, self.parcalar = [], []

    def _atla(self) -> bool:
        return any(self.yigin)

    def handle_starttag(self, etiket, oznitelik):
        oz = dict(oznitelik)
        atla = self._atla() or oz.get("lang") == "tr" or etiket in ("script", "style")
        if not atla:
            self.parcalar += [oz[k] for k in ("aria-label", "alt", "title") if oz.get(k)]
        if etiket not in self.BOS:
            self.yigin.append(atla)

    def handle_startendtag(self, etiket, oznitelik):
        if not self._atla():
            oz = dict(oznitelik)
            self.parcalar += [oz[k] for k in ("aria-label", "alt", "title") if oz.get(k)]

    def handle_endtag(self, etiket):
        if etiket not in self.BOS and self.yigin:
            self.yigin.pop()

    def handle_data(self, veri):
        if not self._atla():
            self.parcalar.append(veri)


def test_en_home_has_no_turkish_letters(cikti):
    html = _oku(cikti, ANA["en"])
    okur = _Metin()
    okur.feed(html)
    metin = " ".join(okur.parcalar)
    assert "One memory, every agent." in metin and "Türkçe" not in metin   # the parser sees the text, skips lang="tr"
    assert re.findall(r"[ğışİĞŞ]", metin) == [], [w for w in metin.split() if re.search(r"[ğışİĞŞ]", w)]


def test_en_memory_has_no_turkish_letters(cikti):
    # Includes the helper table: every row's name must have an English form when it carries Turkish words.
    okur = _Metin()
    okur.feed(_oku(cikti, "en/memory/index.html"))
    metin = " ".join(okur.parcalar)
    assert "Memory" in metin
    harf = r"[ğışİĞŞüöçÜÖÇ]"
    assert re.findall(harf, metin) == [], [w for w in metin.split() if re.search(harf, w)]


def test_products_strip_lists_only_hafiza(cikti):
    for dil, dosya in ANA.items():
        bolum = _bolum(_oku(cikti, dosya), '<section id="urunler"')
        ogeler = re.findall(r"<li\b.*?</li>", bolum, re.S)
        assert len(ogeler) == 1, dosya
        (oge,) = ogeler
        urun = build.metin_yukle()[dil]["urunler"]["hafiza"]
        assert urun["ad"] in oge and html_lib.escape(urun["cumle"], quote=True) in oge, dosya
        (href,) = re.findall(r'<a\b[^>]*href="([^"]+)"', oge)
        assert _cozumle(cikti, dosya, href) == (cikti / SAYFA_DOSYALARI[("hafiza", dil)]).resolve()
        assert re.search(r'<img class="ia" src="[^"]*logo/council-amblem\.svg"', oge)
        assert re.search(r'<img class="ik" src="[^"]*logo/council-amblem-koyu\.svg"', oge)


def test_home_weight_budget(cikti):
    """First load of the home page (HTML, CSS, JS, glyph subset, JSON; gzip; fonts and images excluded) <= 250 KB."""
    (varlik,) = (cikti / "varlik").iterdir()
    for dosya in ANA.values():
        yuk = [(cikti / dosya).read_bytes()]
        yuk += [p.read_bytes() for p in sorted(varlik.rglob("*")) if p.suffix in (".css", ".js", ".json")]
        toplam = sum(len(gzip.compress(b, mtime=0)) for b in yuk)
        assert toplam <= 250 * 1024, (dosya, toplam)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_site_js():
    r = subprocess.run(["node", "--test", str(KOK / "tests" / "js" / "site.test.mjs")],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr


def test_unknown_placeholder_stops_build():
    assert build._doldur("Öteki {yolda} özellik", {"yolda": 4}) == "Öteki 4 özellik"
    with pytest.raises(SystemExit, match=r"\{yok\}"):
        build._doldur("{yok}", {"yolda": 4})


def test_site_does_not_reuse_brand_state_classes():
    # brand JS adds these at run time (s-kur/s-kurulum during the identity moment,
    # s-acik/s-etkin/...); a site class with the same name would pick up brand rules
    # and push site rules onto brand elements.
    durum = set()
    for js in (KOK / "brand" / "js").rglob("*.js"):
        for cagri in re.findall(r"classList\.(?:add|toggle|remove)\(([^)]*)\)", js.read_text(encoding="utf-8")):
            durum.update(re.findall(r'"(s-[a-z0-9_-]+)"', cagri))
    assert {"s-kur", "s-kurulum"} <= durum
    sablon = KOK / "site" / "sablon"
    for dosya in sorted(sablon.iterdir()):
        if dosya.suffix not in {".css", ".html", ".js"}:
            continue
        metin = dosya.read_text(encoding="utf-8")
        for ad in sorted(durum):
            assert not re.search(r"(?<![\w-])\.?" + re.escape(ad) + r"(?![\w-])", metin), f"{dosya.name}: {ad}"


# Hafıza product page (Task 6)

HAFIZA = {"tr": "hafiza/index.html", "en": "en/memory/index.html"}
BOLUM_IDLERI = {
    "tr": ["nasil-calisir", "kurulum", "ilk-bes-dakika", "hafizanin-ici", "olcumler", "neden-farkli", "yardimcilar", "sss",
           "belgeler"],
    "en": ["how-it-works", "setup", "first-five-minutes", "inside-the-memory", "measurements", "why-different",
           "supported-agents", "questions", "docs"],
}
ARAC_BLOK = re.compile(r"<!-- yardimcilar:bas -->(.*?)<!-- yardimcilar:son -->", re.S)


def _icerik():
    return _yukle("brand_icerik_t6", KOK / "brand" / "icerik.py")


def test_hafiza_section_order(cikti):
    for dil, dosya in HAFIZA.items():
        html = _oku(cikti, dosya)
        assert re.findall(r'<section id="([^"]+)"', html) == BOLUM_IDLERI[dil], dosya
        for k in BOLUM_IDLERI[dil]:
            assert f'aria-labelledby="{k}-b"' in html and f'<h2 id="{k}-b"' in html, (dosya, k)


def test_assistants_only_in_block(cikti):
    icerik = _icerik()
    veri = json.loads((KOK / "site" / "veri" / "yardimcilar.json").read_text(encoding="utf-8"))
    for dil, dosya in HAFIZA.items():
        html = _oku(cikti, dosya)
        bloklar = ARAC_BLOK.findall(html)
        assert len(bloklar) == 1 and bloklar[0].strip(), dosya
        assert html.count("<!-- yardimcilar:bas -->") == 1 and html.count("<!-- yardimcilar:son -->") == 1
        assert icerik.arac_adlari_bul(ARAC_BLOK.sub("", html)) == [], dosya
        assert {"claude", "hermes", "antigravity", "codex", "gemini"} <= set(icerik.arac_adlari_bul(bloklar[0])), dosya
        satirlar = re.findall(r"<tr>.*?</tr>", bloklar[0], re.S)[1:]   # the first row is the header
        assert len(satirlar) == len(veri), dosya
        for satir, o in zip(satirlar, veri, strict=True):
            ad = o["ad"] if isinstance(o["ad"], str) else o["ad"][dil]
            assert html_lib.escape(ad, quote=True) in satir and html_lib.escape(o["destek"][dil], quote=True) in satir
            assert f'data-durum="{o["durum"].replace("ı", "i")}"' in satir


def test_assistants_data_shape():
    veri = json.loads((KOK / "site" / "veri" / "yardimcilar.json").read_text(encoding="utf-8"))
    assert len(veri) == 5
    for o in veri:
        assert set(o) == {"ad", "destek", "durum"} and set(o["destek"]) == {"tr", "en"}
        assert o["durum"] in ("tam", "kullanımda", "denenmedi")


def test_tool_count_copy(cikti):
    temel, ogrenme = build.arac_sayilari()
    beklenen = {"tr": f"{temel} temel araç + {ogrenme} kişisel gelişim aracı (denemede)",
                "en": f"{temel} core tools + {ogrenme} personal-development tools (in trial)"}
    for dil, dosya in HAFIZA.items():
        bolum = _bolum(_oku(cikti, dosya), '<section id="' + BOLUM_IDLERI[dil][4] + '"')
        assert beklenen[dil] in html_lib.unescape(bolum), dosya
        assert build.surum() in bolum, dosya


def test_hafiza_has_no_scene(cikti):
    for dosya in HAFIZA.values():
        html = _oku(cikti, dosya)
        assert not re.search(r'class="[^"]*\bs-(?:cs|tur)\b', html), dosya
        assert "data-denetim-sahne" not in html, dosya
        assert "data-bicim" not in html, dosya


def test_copy_buttons_are_not_kor(cikti):
    for dil, dosya in HAFIZA.items():
        html = _oku(cikti, dosya)
        assert "c-dugme--kor" not in html, dosya
        dugmeler = re.findall(r'<button type="button" class="c-dugme c-dugme--k c-dugme--hayalet"([^>]*)>', html)
        assert len(dugmeler) == 3, dosya
        for oz in dugmeler:
            hedef = re.search(r'data-kopyala="([^"]+)"', oz).group(1)
            assert re.search(rf'<pre><code id="{hedef}">', html), (dosya, hedef)
            assert re.search(r'data-tamam="[^"]+"', oz) and re.search(r'data-hata="[^"]+"', oz) and " hidden" in oz


def test_install_ways_verbatim(cikti):
    yollar = {"kur-cumlesi": KUR_CUMLESI,
              "kur-unix": "curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh",
              "kur-windows": "irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex"}
    for dil, dosya in HAFIZA.items():
        html = _oku(cikti, dosya)
        bolum = _bolum(html, f'<section id="{BOLUM_IDLERI[dil][1]}"')
        kodlar = dict(re.findall(r'<pre><code id="([^"]+)">(.*?)</code></pre>', bolum, re.S))
        for ad, beklenen in yollar.items():
            beklenen = beklenen[dil] if isinstance(beklenen, dict) else beklenen
            assert html_lib.unescape(kodlar[ad]) == beklenen, (dosya, ad)
        for secenek in ("--no-auto-update", "--no-import", "--from", "--port"):
            assert f"<code>{secenek}" in bolum, (dosya, secenek)


def test_hafiza_hero_emblem(cikti):
    for dil, dosya in HAFIZA.items():
        html = _oku(cikti, dosya)
        (emblem,) = re.findall(r'<div class="s-hf-amblem" data-yazi-kur>(<svg .*?</svg>)</div>', html, re.S)
        assert 'viewBox="0 0 400 400"' in emblem
        assert [r for r in re.findall(r'data-kur="([^"]+)"', emblem)] == ["isaret", "kor", "c", "isaret"]
        assert 'data-kur="yazi"' not in emblem and "data-metin" not in emblem
        kaynak = (KOK / "brand" / "logo" / "council-logo-kur.html").read_text(encoding="utf-8")
        for parca in re.findall(r'<(?:circle|path)[^>]*data-kur="(?:kor|c)"[^>]*/?>', kaynak):
            assert parca.replace("ust-kesik", "amblem-kesik") in emblem, parca   # derived from the logo fragment, not copied by hand
        ids = re.findall(r'\bid="([^"]+)"', html)
        assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]
        assert re.search(r'<h1 class="yazi-baslik-xl" data-yazi-kur data-glifler="[^"]+">' +
                         re.escape(build.metin_yukle()[dil]["sayfalar"]["hafiza"]["h1"]) + "</h1>", html), dosya
        assert html.index('class="s-hf-amblem"') < html.index("<h1")


def test_how_it_works_drawing(cikti):
    for dil, dosya in HAFIZA.items():
        bolum = _bolum(_oku(cikti, dosya), f'<section id="{BOLUM_IDLERI[dil][0]}"')
        (svg,) = re.findall(r'<svg class="s-akis".*?</svg>', bolum, re.S)
        assert svg.count("s-kor") == 1
        assert svg.count("Oturum" if dil == "tr" else "Session") == 3
        assert "currentColor" in svg
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(|filter|<linearGradient|<radialGradient", svg)
        assert len(re.findall(r"<li\b", bolum)) == 3


def test_measurements_dated(cikti):
    from_readme = {"tr": ("4,8 ms", "44 sorunun %84'ü", "yaklaşık 70 MB", "Örnek küçüktür"),
                   "en": ("4.8 ms", "84% of 44 questions", "about 70 MB", "The sample is small")}
    for dil, dosya in HAFIZA.items():
        bolum = _bolum(_oku(cikti, dosya), f'<section id="{BOLUM_IDLERI[dil][4]}"')
        assert "2026-11-16" in bolum, dosya
        for parca in from_readme[dil]:
            assert html_lib.escape(parca, quote=True) in bolum or parca in bolum, (dosya, parca)
        assert len(re.findall(r"<tr>", bolum)) == 7, dosya   # header + six measurements


def test_hafiza_misc_sections(cikti):
    for dil, dosya in HAFIZA.items():
        html = _oku(cikti, dosya)
        ilk = _bolum(html, f'<section id="{BOLUM_IDLERI[dil][2]}"')
        assert len(re.findall(r"<li\b", ilk)) == 4, dosya
        ic = _bolum(html, f'<section id="{BOLUM_IDLERI[dil][3]}"')
        for ad in ("core.md", "rules.md", "threads.md", "sessions.md", "projects/", "knowledge/", "imported/", "log/"):
            assert ad in ic, (dosya, ad)
        sss = _bolum(html, f'<section id="{BOLUM_IDLERI[dil][7]}"')
        assert len(re.findall(r"<details>\s*<summary\b", sss)) >= 6, dosya
        belge = _bolum(html, f'<section id="{BOLUM_IDLERI[dil][8]}"')
        yollar = re.findall(r'href="(https://github\.com/musalkeremlboz/council/blob/main/[^"]+)"', belge)
        assert any(y.endswith("/INSTALL.md") for y in yollar) and any(y.endswith("docs/setup.md") for y in yollar), dosya
        assert len(re.findall(r"<li\b", _bolum(html, f'<section id="{BOLUM_IDLERI[dil][5]}"'))) == 6, dosya


def test_hafiza_tree_is_keyboard_scrollable(cikti):
    for dil, dosya in HAFIZA.items():
        html = _oku(cikti, dosya)
        etiket = build.metin_yukle()[dil]["hafiza"]["ic"]["agac_etiket"]
        m = re.search(r'<pre class="s-agac"([^>]*)>', html)
        assert m, dosya
        assert 'tabindex="0"' in m.group(1), dosya
        assert f'aria-label="{html_lib.escape(etiket, quote=True)}"' in m.group(1), dosya
    css = (KOK / "site" / "sablon" / "site.css").read_text(encoding="utf-8")
    assert re.search(r"\.s-agac:focus-visible\s*\{[^}]*outline:[^}]*var\(--", css)

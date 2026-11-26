"""The built site in headless Chrome (skipped without Chrome), plus the files around it: sitemap, robots, share images."""
import html as html_lib
import importlib.util
import json
import re
import struct
import sys
import tempfile
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
BRAND = KOK / "brand"
SAYFALAR = ("index.html", "en/index.html", "hafiza/index.html", "en/memory/index.html")
ANA = ("index.html", "en/index.html")


def _yukle(ad: str, yol: Path):
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


build = _yukle("site_build_tarayici", KOK / "site" / "build.py")
sys.path.insert(0, str(BRAND))
denetle = _yukle("denetle_tarayici", BRAND / "denetle.py")
chrome = pytest.mark.skipif(denetle.chrome_yolu() is None, reason="Chrome is not installed")


@pytest.fixture(scope="module")
def cikti(tmp_path_factory) -> Path:
    hedef = tmp_path_factory.mktemp("cikti")
    assert build.main(["--cikti", str(hedef)]) == 0
    return hedef


def test_sitemap_lists_four_pages(cikti):
    xml = (cikti / "sitemap.xml").read_text(encoding="utf-8")
    adresler = re.findall(r"<url>\s*<loc>([^<]+)</loc>", xml)
    assert adresler == ["https://council.systems/", "https://council.systems/en/",
                        "https://council.systems/hafiza/", "https://council.systems/en/memory/"]
    assert 'xmlns:xhtml="http://www.w3.org/1999/xhtml"' in xml
    for blok in re.findall(r"<url>.*?</url>", xml, re.S):
        assert len(re.findall(r'<xhtml:link rel="alternate" hreflang="(?:tr|en)" href="https://council.systems/[^"]*"/>', blok)) == 2
        assert 'hreflang="x-default"' in blok


def test_robots(cikti):
    assert (cikti / "robots.txt").read_text(encoding="utf-8") == (
        "User-agent: *\nAllow: /\nSitemap: https://council.systems/sitemap.xml\n")


def _boyut(png: Path) -> tuple[int, int]:
    veri = png.read_bytes()
    assert veri[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", veri[16:24])


def test_share_images_committed_and_copied(cikti):
    for dil in build.DILLER:
        kayitli = KOK / "site" / "cikti" / f"paylas-{dil}.png"
        assert _boyut(kayitli) == (1200, 630)
        assert (cikti / f"paylas-{dil}.png").read_bytes() == kayitli.read_bytes()
    assert (KOK / "site" / "sablon" / "paylas.svg").is_file()


def test_share_tagline_fits_between_margins():
    """The tagline of each language ends before the right margin (1200 - 96), measured with the font's advances."""
    ttlib = pytest.importorskip("fontTools.ttLib")
    yazi = ttlib.TTFont(KOK / "brand" / "font" / "CouncilHalka.woff2")
    harita, olcu, birim = yazi.getBestCmap(), yazi["hmtx"], yazi["head"].unitsPerEm
    metin = build.metin_yukle()
    for dil in build.DILLER:
        slogan = metin[dil]["site"]["slogan"]
        genislik = sum(olcu[harita[ord(c)]][0] for c in slogan) / birim * build.SLOGAN_BOYUT[dil]
        assert 96 + genislik <= 1200 - 96, (dil, genislik)


@chrome
@pytest.mark.parametrize("sayfa", SAYFALAR)
@pytest.mark.parametrize("genislik", (375, 1280))
def test_no_horizontal_overflow(cikti, sayfa, genislik):
    assert denetle.tasma_var_mi(cikti / sayfa, genislik) is False


@chrome
@pytest.mark.parametrize("sayfa", SAYFALAR)
def test_identity_moment_builds_the_wordmark(cikti, sayfa):
    """The header holds the wordmark only (no mark): the identity moment draws it, then the source markup returns."""
    sira, ayni = denetle.kimlik_ani(cikti / sayfa)
    assert sira == "yazi"
    assert ayni is True


@chrome
@pytest.mark.parametrize("sayfa", SAYFALAR)
@pytest.mark.parametrize("genislik", (375, 1280))
def test_no_hidden_text_without_js_or_with_reduced_motion(cikti, sayfa, genislik):
    assert denetle.gizli_say(cikti / sayfa, genislik, azalt=True, js=True) == 0
    assert denetle.gizli_say(cikti / sayfa, genislik, azalt=False, js=False) == 0


# Home page (Kurul Masası) in headless Chrome: layouts, seats, keyboard
# The page is measured by a script appended to a copy of it (next to the original, so the relative links hold): it
# opens each section through its seat, waits for the fade, and records overflow and which sections are shown.

OLCUM = """<script>(async () => {
  const bekle = (ms) => new Promise((r) => setTimeout(r, ms));
  if (document.readyState !== "complete") await new Promise((r) => addEventListener("load", r));
  for (let i = 0; i < 100 && !document.documentElement.classList.contains("masa-js"); i++) await bekle(100);   // masa.js is imported late
  await bekle(800);
  const kok = document.documentElement, o = { js: kok.classList.contains("masa-js"), bolumler: [], klavye: [] };
  const sekmeler = [...document.querySelectorAll("[role=tab]")];
  const sec = () => document.querySelector("[role=tab][aria-selected=true]").id;
  const tus = (hedef, k) => hedef.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true }));
  for (const sekme of sekmeler) {
    sekme.click();
    await bekle(900);
    const b = document.getElementById(sekme.getAttribute("aria-controls")), r = b.getBoundingClientRect();
    o.bolumler.push({
      id: b.id,
      acik: b.hasAttribute("data-acik") && !b.hidden && getComputedStyle(b).visibility === "visible" && r.width > 0,
      kapali: [...document.querySelectorAll(".sahne")].filter((x) => x !== b && (!x.hidden || x.hasAttribute("data-acik"))).length,
      bolumTasma: b.scrollWidth > b.clientWidth + 1,
      belgeTasma: kok.scrollWidth > innerWidth,
      secili: sekme.getAttribute("aria-selected"),
    });
  }
  const m = document.querySelector(".masa").getBoundingClientRect();
  o.masa = m.left >= 0 && m.right <= innerWidth && m.top >= 0 && m.bottom <= innerHeight;
  o.tabindex = sekmeler.map((x) => x.tabIndex).join(",");
  const adim = async (hedef, k) => { tus(hedef, k); await bekle(60); o.klavye.push(sec() + (document.activeElement.id || "")); };
  await adim(document.body, "1"); await adim(document.body, "3"); await adim(document.body, "PageDown"); await adim(document.body, "PageUp");
  await adim(document.querySelector("#r3"), "ArrowRight"); await adim(document.querySelector("#r4"), "End"); await adim(document.querySelector("#r5"), "Home");
  kok.dataset.olcum = JSON.stringify(o);
})()</script>"""


def _ana_olc(sayfa: Path, genislik: int, yukseklik: int, azalt: bool = False) -> dict:
    kopya = sayfa.with_name(".ana-olcum.html")
    kopya.write_text(sayfa.read_text(encoding="utf-8").replace("</body>", OLCUM + "</body>"), encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory() as profil:
            adres = kopya.resolve().as_uri()
            if genislik < denetle.ASGARI:   # Chrome opens no window narrower than 500 px: measure inside an iframe
                sarmal = Path(profil) / "sarmal.html"
                sarmal.write_text(
                    f'<!doctype html><meta charset="utf-8"><style>body{{margin:0}}iframe{{border:0;display:block}}</style>'
                    f'<iframe id="f" width="{genislik}" height="{yukseklik}" src="{adres}"></iframe>'
                    "<script>setInterval(()=>{try{const d=f.contentDocument.documentElement.dataset;"
                    "if(d.olcum)document.documentElement.dataset.olcum=d.olcum}catch(e){}},100)</script>", encoding="utf-8")
                adres = sarmal.as_uri()
            r = denetle._calistir([f"--window-size={max(genislik, denetle.ASGARI)},{yukseklik}", "--virtual-time-budget=14000",
                                   "--dump-dom", adres, *(["--force-prefers-reduced-motion"] if azalt else [])], Path(profil))
    finally:
        kopya.unlink(missing_ok=True)
    bulunan = re.search(r'data-olcum="([^"]*)"', r.stdout)
    assert bulunan, f"no measurement (exit {r.returncode}): {r.stderr[-300:]}"
    return json.loads(html_lib.unescape(bulunan.group(1)))


BOYUTLAR = ((375, 812), (812, 375), (820, 1180), (1180, 820), (950, 1150), (1280, 800), (1920, 1080))


def _kontrol(o: dict) -> None:
    assert o["js"] is True
    assert [b["id"] for b in o["bolumler"]] == ["giris", "canli", "nasil", "kurul", "yardimcilar"]
    for b in o["bolumler"]:
        assert b["acik"] is True and b["secili"] == "true", b   # clicking the seat shows its section
        assert b["kapali"] == 0, b                              # and no other section is open or shown
        assert b["bolumTasma"] is False and b["belgeTasma"] is False, b   # no horizontal overflow, in the section or the page
    assert o["masa"] is True                                    # the seat row sits inside the window
    assert o["tabindex"] == "-1,-1,-1,-1,0"                      # one tab stop (the selected seat) after the clicks
    # keys 1 and 3, PageDown, PageUp (selection only), then arrow, End and Home on a seat (focus follows)
    assert o["klavye"] == ["r1", "r3", "r4", "r3", "r4r4", "r5r5", "r1r1"]


@chrome
@pytest.mark.parametrize("genislik,yukseklik", BOYUTLAR)
def test_home_layouts_have_no_overflow_and_seats_open_sections(cikti, genislik, yukseklik):
    _kontrol(_ana_olc(cikti / "index.html", genislik, yukseklik))


@chrome
@pytest.mark.parametrize("genislik,yukseklik", ((375, 812), (1280, 800)))
def test_english_home_layouts(cikti, genislik, yukseklik):
    _kontrol(_ana_olc(cikti / "en" / "index.html", genislik, yukseklik))


@chrome
def test_home_seats_with_reduced_motion(cikti):
    _kontrol(_ana_olc(cikti / "index.html", 1280, 800, azalt=True))

"""The built site in headless Chrome (skipped without Chrome), plus the files around it: sitemap, robots, share images."""
import importlib.util
import re
import struct
import sys
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

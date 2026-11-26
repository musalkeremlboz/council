"""Content and link checks of the site: its sources under site/ and a fresh build (brand/icerik.py word lists)."""
import importlib.util
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

KOK = Path(__file__).resolve().parent.parent
SITE = KOK / "site"
METIN_UZANTI = {".md", ".json", ".css", ".js", ".mjs", ".py", ".html", ".svg", ".txt", ".xml", ".sh"}
IZINLI_ARAC = SITE / "veri" / "yardimcilar.json"
YARDIMCILAR = re.compile(r"<!-- yardimcilar:bas -->.*?<!-- yardimcilar:son -->", re.S)
RENK = re.compile(r"(?<![&\w])#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(", re.I)
SITE_URL_IZINLI = re.compile(
    r'<link rel="(?:canonical|alternate)"[^>]*>|<meta property="og:(?:url|image)"[^>]*>')
SAHNE = re.compile(r'class="(?:[^"]*\s)?s-(?:cs|tur)(?![\w-])[^"]*"')


def _yukle(ad: str, yol: Path):
    spec = importlib.util.spec_from_file_location(ad, yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


icerik = _yukle("brand_icerik", KOK / "brand" / "icerik.py")
build = _yukle("site_build_denetim", SITE / "build.py")


@pytest.fixture(scope="module")
def cikti(tmp_path_factory) -> Path:
    hedef = tmp_path_factory.mktemp("cikti")
    assert build.main(["--cikti", str(hedef)]) == 0
    return hedef


def _metinler(klasor: Path):
    return [p for p in sorted(klasor.rglob("*"))
            if p.is_file() and p.suffix in METIN_UZANTI and "__pycache__" not in p.parts]


def _kaynaklar() -> list[Path]:
    """site/ sources: everything but the committed output (it is compared with a fresh build below)."""
    return [p for p in _metinler(SITE) if "cikti" not in p.relative_to(SITE).parts]


def _sayfalar(cikti: Path) -> list[Path]:
    return sorted(cikti.rglob("*.html"))


def _uretilen_metin(yol: Path) -> str:
    metin = yol.read_text(encoding="utf-8")
    return YARDIMCILAR.sub("", metin) if yol.suffix == ".html" else metin


def test_scan_sees_sources_and_pages(cikti):
    adlar = {p.relative_to(SITE).as_posix() for p in _kaynaklar()}
    assert {"build.py", "sablon/sayfa.html", "metin/tr.json", "metin/en.json", "veri/urunler.json"} <= adlar
    assert len(_sayfalar(cikti)) == 4


def test_no_tool_names_outside_assistants_block(cikti):
    bulunan = [f"{p.relative_to(SITE)}: {ad}" for p in _kaynaklar() if p != IZINLI_ARAC
               for ad in icerik.arac_adlari_bul(p.read_text(encoding="utf-8"))]
    bulunan += [f"cikti/{p.relative_to(cikti)}: {ad}" for p in _metinler(cikti)
                for ad in icerik.arac_adlari_bul(_uretilen_metin(p))]
    assert bulunan == []


def test_no_personal_words(cikti):
    bulunan = [f"{p.relative_to(SITE)}: {ad}" for p in _kaynaklar()
               for ad in icerik.kisisel_bul(p.read_text(encoding="utf-8"))]
    bulunan += [f"cikti/{p.relative_to(cikti)}: {ad}" for p in _metinler(cikti)
                for ad in icerik.kisisel_bul(p.read_text(encoding="utf-8"))]
    assert bulunan == []


def _sahip() -> str:
    satir = re.search(r"^Copyright \(c\) \d{4} (.+)$", (KOK / "LICENSE").read_text(encoding="utf-8"), re.M)
    assert satir, "LICENSE has no copyright line"
    return satir.group(1).strip()


def test_owner_full_name_absent(cikti):
    ad = icerik.duz(_sahip())
    assert " " in ad
    bulunan = [str(p) for p in [*_kaynaklar(), *_metinler(cikti)] if ad in icerik.duz(p.read_text(encoding="utf-8"))]
    assert bulunan == []


def test_no_color_literals(cikti):
    kaynak = [p for p in _kaynaklar() if p.relative_to(SITE).parts[0] in ("sablon", "metin", "veri")]
    assert kaynak
    bulunan = [f"{p.relative_to(SITE)}: {m}" for p in kaynak for m in RENK.findall(p.read_text(encoding="utf-8"))]
    bulunan += [f"cikti/{p.relative_to(cikti)}: {m}" for p in _sayfalar(cikti)
                if "varlik" not in p.relative_to(cikti).parts
                for m in RENK.findall(p.read_text(encoding="utf-8"))]
    assert bulunan == []


def _goreli(adres: str) -> bool:
    return not urlsplit(adres).scheme and not adres.startswith("//")


def test_no_external_resources(cikti):
    for sayfa in _sayfalar(cikti):
        html = sayfa.read_text(encoding="utf-8")
        for etiket in re.findall(r"<(?:link|script|img|source|iframe|video|audio|embed|object)\b[^>]*>", html):
            if re.search(r'rel="(?:canonical|alternate)"', etiket):
                continue
            for adres in re.findall(r'\b(?:href|src|srcset|data)="([^"]+)"', etiket):
                assert _goreli(adres), (sayfa, etiket)
        for adres in re.findall(r"url\(\s*['\"]?([^'\")]+)", html):
            assert _goreli(adres), (sayfa, adres)
        assert "@import" not in html
        assert "council.systems" not in SITE_URL_IZINLI.sub("", html), sayfa
    stiller = [p for p in _metinler(cikti) if p.suffix == ".css"] + [p for p in _kaynaklar() if p.suffix == ".css"]
    assert stiller
    for css in stiller:
        metin = css.read_text(encoding="utf-8")
        for adres in re.findall(r"url\(\s*['\"]?([^'\")]+)", metin):
            assert _goreli(adres), (css, adres)
        for adres in re.findall(r"@import\s+(?:url\()?\s*['\"]?([^'\")\s;]+)", metin):
            assert _goreli(adres), (css, adres)


def _baglantilar(html: str) -> list[str]:
    return re.findall(r'<a\b[^>]*?\bhref="([^"]*)"', html)


def test_outbound_links_only_github(cikti):
    disari = []
    for sayfa in _sayfalar(cikti):
        for href in _baglantilar(sayfa.read_text(encoding="utf-8")):
            if not _goreli(href):
                disari.append(href)
                assert href.startswith(("https://github.com/", "https://raw.githubusercontent.com/")), (sayfa, href)
    assert disari


def test_internal_links_resolve(cikti):
    for sayfa in _sayfalar(cikti):
        for href in _baglantilar(sayfa.read_text(encoding="utf-8")):
            if not _goreli(href):
                continue
            parca = urlsplit(href)
            hedef = (sayfa.parent / parca.path) if parca.path else sayfa
            if parca.path.endswith("/") or hedef.is_dir():
                hedef = hedef / "index.html"
            assert hedef.is_file(), (sayfa, href)
            if parca.fragment:
                assert f'id="{parca.fragment}"' in hedef.read_text(encoding="utf-8"), (sayfa, href)


def test_scene_count(cikti):
    for ad, yollar in build.SAYFALAR.items():
        for yol in yollar.values():
            html = (cikti / yol / "index.html").read_text(encoding="utf-8")
            sayi = len(SAHNE.findall(html))
            assert sayi <= (2 if ad == "ana" else 0), (yol, sayi)


def test_committed_output_is_current(cikti):
    def dosyalar(k: Path) -> dict[str, bytes]:   # a CRLF checkout of the committed text files still counts as current
        return {p.relative_to(k).as_posix(): p.read_bytes().replace(b"\r\n", b"\n") if p.suffix in METIN_UZANTI
                else p.read_bytes() for p in sorted(k.rglob("*")) if p.is_file()}

    taze, kayitli = dosyalar(cikti), dosyalar(SITE / "cikti")
    assert sorted(taze) == sorted(kayitli), "site/cikti/ is stale: run python site/build.py"
    assert [y for y in taze if taze[y] != kayitli[y]] == [], "site/cikti/ is stale: run python site/build.py"


def test_no_kasa(cikti):
    """Kasa is archived: not in any published text file (pages, copied CSS/JS/SVG, JSON, sitemap) nor any file name."""
    metin = [p for p in sorted(cikti.rglob("*")) if p.is_file() and p.suffix in METIN_UZANTI]
    assert any(p.suffix == ".js" for p in metin) and any(p.suffix == ".html" for p in metin)   # scope sanity
    bulunan = [str(p) for p in metin if "kasa" in icerik.duz(p.read_text(encoding="utf-8"))]
    bulunan += [str(p) for p in cikti.rglob("*") if "kasa" in icerik.duz(p.name)]
    assert bulunan == []

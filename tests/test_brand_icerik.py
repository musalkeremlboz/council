"""Content scan of brand/: no AI-tool names, no personal examples, and the README names only real tokens."""
import importlib.util
import json
import re
from pathlib import Path

BRAND = Path(__file__).resolve().parent.parent / "brand"
ICERIK = BRAND / "icerik.py"
README = BRAND / "README.md"
METIN = {".md", ".json", ".css", ".js", ".mjs", ".py", ".html", ".svg", ".txt"}
IZIN = "claude.ai tasarım sistemi sayfası"


def _icerik_yukle():
    """Load brand/icerik.py by path (brand is not a package)."""
    spec = importlib.util.spec_from_file_location("brand_icerik", ICERIK)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


icerik = _icerik_yukle()
# A backticked name counts as a token name when it starts with a token family word.
TOKEN_BICIMI = re.compile(
    r"^(zemin|yuzey|murekkep|cizgi|kor|basari|uyari|hata|pasif|ton|kose|sure|egri|ara|baslik|govde|etiket|font|kod)(-[a-z0-9]+)*$"
)


def _dosyalar():
    return [p for p in BRAND.rglob("*") if p.is_file() and p.suffix in METIN and p != ICERIK]


def test_icerik_module_matches_rules():
    assert icerik.arac_adlari_bul("Claude ve HERMES") == ["claude", "hermes"]
    assert icerik.kisisel_bul("DİŞÇİ randevusu") == ["randevu", "dişçi"]
    assert icerik.kisisel_bul("") == []


def test_no_tool_names():
    bulunan = []
    for yol in _dosyalar():
        metin = yol.read_text(encoding="utf-8").lower()
        if yol == README:
            metin = metin.replace(IZIN, "")
        bulunan += [f"{yol.relative_to(BRAND)}: {ad}" for ad in icerik.arac_adlari_bul(metin)]
    assert bulunan == []


def test_no_personal_examples():
    bulunan = []
    for yol in _dosyalar():
        metin = yol.read_text(encoding="utf-8")
        bulunan += [f"{yol.relative_to(BRAND)}: {ad}" for ad in icerik.kisisel_bul(metin)]
    assert bulunan == []


def _token_adlari():
    t = json.loads((BRAND / "tokens.json").read_text(encoding="utf-8"))
    adlar = set()
    for aile in t.values():
        adlar |= {x["name"] for x in aile.get("tokens", [])}
    adlar |= {f"font-{k}" for k in t["type"]["families"]}
    adlar |= {s["name"] for g in t["type"]["groups"] for s in g["styles"]}
    return adlar


def test_readme_names_existing_tokens():
    metin = README.read_text(encoding="utf-8")
    adaylar = {a for a in re.findall(r"`([^`\s]+)`", metin) if TOKEN_BICIMI.match(a)}
    assert adaylar, "README names no tokens"
    assert sorted(adaylar - _token_adlari()) == []

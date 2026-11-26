"""Content scan of brand/: no AI-tool names, no personal examples, and the README names only real tokens."""
import json
import re
from pathlib import Path

BRAND = Path(__file__).resolve().parent.parent / "brand"
README = BRAND / "README.md"
METIN = {".md", ".json", ".css", ".js", ".mjs", ".py", ".html", ".svg", ".txt"}
ARAC_ADLARI = ("claude", "hermes", "antigravity", "chatgpt", "codex", "gemini")
KISISEL = ("randevu", "dişçi", "vize", "sınav", "borç", "maaş")
IZIN = "claude.ai tasarım sistemi sayfası"
# A backticked name counts as a token name when it starts with a token family word.
TOKEN_BICIMI = re.compile(
    r"^(zemin|yuzey|murekkep|cizgi|kor|basari|uyari|hata|pasif|ton|kose|sure|egri|ara|baslik|govde|etiket|font|kod)(-[a-z0-9]+)*$"
)


def _dosyalar():
    return [p for p in BRAND.rglob("*") if p.is_file() and p.suffix in METIN]


def _duz(metin: str) -> str:
    """Lowercase with the Turkish dotted/dotless i folded together, so "DİŞÇİ" and "dişçi" both match."""
    return metin.replace("İ", "i").replace("I", "i").replace("ı", "i").lower()


def test_no_tool_names():
    bulunan = []
    for yol in _dosyalar():
        metin = yol.read_text(encoding="utf-8").lower()
        if yol == README:
            metin = metin.replace(IZIN, "")
        bulunan += [f"{yol.relative_to(BRAND)}: {ad}" for ad in ARAC_ADLARI if ad in metin]
    assert bulunan == []


def test_no_personal_examples():
    bulunan = []
    for yol in _dosyalar():
        metin = _duz(yol.read_text(encoding="utf-8"))
        bulunan += [f"{yol.relative_to(BRAND)}: {ad}" for ad in KISISEL if _duz(ad) in metin]
    assert bulunan == []


def _token_adlari():
    t = json.loads((BRAND / "tokens.json").read_text(encoding="utf-8"))
    adlar = set()
    for aile in t.values():
        for anahtar in ("tokens", "families", "groups"):
            adlar |= {x["name"] for x in aile.get(anahtar, [])}
    return adlar


def test_readme_names_existing_tokens():
    metin = README.read_text(encoding="utf-8")
    adaylar = {a for a in re.findall(r"`([^`\s]+)`", metin) if TOKEN_BICIMI.match(a)}
    assert adaylar, "README names no tokens"
    assert sorted(adaylar - _token_adlari()) == []

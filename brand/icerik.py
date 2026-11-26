"""Word lists for content scans: AI-tool names and personal words that must stay out of brand/ and site/."""

ARAC_ADLARI = ("claude", "hermes", "antigravity", "chatgpt", "codex", "gemini")
KISISEL = ("randevu", "dişçi", "vize", "sınav", "borç", "maaş")


def duz(metin: str) -> str:
    """Lowercase with the Turkish dotted/dotless i folded together, so "DİŞÇİ" and "dişçi" both match."""
    return metin.replace("İ", "i").replace("I", "i").replace("ı", "i").lower()


def arac_adlari_bul(metin: str) -> list[str]:
    """Tool names found in the text (case-insensitive), in ARAC_ADLARI order."""
    kucuk = metin.lower()
    return [ad for ad in ARAC_ADLARI if ad in kucuk]


def kisisel_bul(metin: str) -> list[str]:
    """Personal words found in the text (Turkish-i folded), in KISISEL order."""
    duzlenmis = duz(metin)
    return [ad for ad in KISISEL if duz(ad) in duzlenmis]

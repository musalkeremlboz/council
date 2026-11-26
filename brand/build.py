"""tokens.json'dan CSS değişkenlerini üretir ve renk karşıtlığını denetler; örnek sayfanın glif alt kümesini yazar."""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

BRAND = Path(__file__).resolve().parent
TOKENS = BRAND / "tokens.json"
CSS_OUT = BRAND / "css" / "tokens.css"

HEADER = "/* COUNCIL — generated from tokens.json */"

GLIFLER = BRAND / "font" / "glifler.json"
ORNEK = BRAND / "ornek" / "index.html"
ORNEK_GLIFLER = BRAND / "ornek" / "glifler.json"
HEP = ("space", "question")   # yazi-kur.js: sözcük arası ve bilinmeyen harf

# (metin tokeni, zemin tokeni, en düşük oran)
CONTRAST_PAIRS: list[tuple[str, str, float]] = (
    [(fg, bg, 4.5)
     for fg in ("murekkep", "murekkep-2", "murekkep-3", "kor-metin", "basari", "uyari", "hata")
     for bg in ("zemin", "yuzey")]
    + [("kor-ustu", "kor", 4.5), ("kor-ustu", "kor-bas", 4.5),
       ("pasif-yazi", "pasif-zemin", 4.5),
       ("cizgi-guclu", "zemin", 3.0)]
)


def load_tokens(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _lin(channel: int) -> float:
    s = channel / 255
    return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg: str, bg: str) -> float:
    """WCAG 2.x karşıtlık oranı (hex girdi)."""
    a, b = _luminance(fg), _luminance(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def contrast_failures(tokens: dict) -> list[str]:
    colors = {t["name"]: t["value"] for t in tokens["color"]["tokens"]}
    themes = [t["id"] for t in tokens["color"]["themes"]]
    out = []
    for fg, bg, minimum in CONTRAST_PAIRS:
        for theme in themes:
            f, b = colors[fg][theme], colors[bg][theme]
            if f.startswith("rgb") or b.startswith("rgb"):
                continue
            ratio = contrast(f, b)
            if ratio < minimum:
                out.append(f"{theme}: {fg} {f} / {bg} {b} = {ratio:.2f} < {minimum}")
    return out


def _color_lines(tokens: dict, theme: str, indent: str) -> list[str]:
    return [f"{indent}--{t['name']}: {t['value'][theme]};" for t in tokens["color"]["tokens"]]


def css_from_tokens(tokens: dict) -> str:
    lines = [HEADER, ":root {"]
    lines += _color_lines(tokens, "light", "  ")
    for fam in ("spacing", "radius", "motion"):
        lines += [f"  --{t['name']}: {t['value']};" for t in tokens[fam]["tokens"]]
    lines += [f"  --font-{k}: {v};" for k, v in tokens["type"]["families"].items()]
    lines.append("}")
    lines.append("@media (prefers-color-scheme: dark) {")
    lines.append('  :root:not([data-theme="light"]) {')
    lines += _color_lines(tokens, "dark", "    ")
    lines += ["  }", "}"]
    lines.append(':root[data-theme="dark"] {')
    lines += _color_lines(tokens, "dark", "  ")
    lines.append("}")
    for g in tokens["type"]["groups"]:
        for st in g["styles"]:
            lines.append(f".yazi-{st['name']} {{")
            lines.append(f"  font-family: var(--font-{st.get('family', g['family'])});")
            lines.append(f"  font-size: {st['fontSize']};")
            lines.append(f"  line-height: {st['lineHeight']};")
            lines.append(f"  font-weight: {st['fontWeight']};")
            if st.get("letterSpacing"):
                lines.append(f"  letter-spacing: {st['letterSpacing']};")
            lines.append("}")
    return "\n".join(lines) + "\n"


class _Kurulanlar(HTMLParser):
    """[data-yazi-kur] öğelerinin metni (svg içi hariç) ve içlerindeki data-metin değerleri."""
    BOS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.metinler: list[str] = []
        self._yigin: list[tuple[str, bool, bool]] = []   # (etiket, kurulan mı, svg içinde mi)

    def _icinde(self):
        return any(k for _, k, _ in self._yigin), any(s for _, _, s in self._yigin)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        kurulan, svg = self._icinde()
        kurulan = kurulan or "data-yazi-kur" in a
        if kurulan and a.get("data-metin"):
            self.metinler.append(a["data-metin"])
        if tag not in self.BOS:
            self._yigin.append((tag, kurulan, svg or tag == "svg"))

    def handle_startendtag(self, tag, attrs):
        a = dict(attrs)
        if self._icinde()[0] and a.get("data-metin"):
            self.metinler.append(a["data-metin"])

    def handle_endtag(self, tag):
        while self._yigin:
            if self._yigin.pop()[0] == tag:
                break

    def handle_data(self, data):
        kurulan, svg = self._icinde()
        if kurulan and not svg and data.strip():
            self.metinler.append(data)


def kurulan_metinler(html: str) -> list[str]:
    p = _Kurulanlar()
    p.feed(html)
    return p.metinler


def _tr_buyuk(metin: str) -> str:
    return metin.replace("i", "İ").replace("ı", "I").upper()


def glif_altkumesi(veri: dict, metinler: list[str]) -> dict:
    """glifler.json'un yalnız bu metinlerde (ve büyük harfli hâllerinde) geçen harfleri: sahne yalnız kullandığını yükler."""
    harfler = set()
    for m in metinler:
        harfler |= set(m) | set(_tr_buyuk(m))
    harita = {ch: ad for ch, ad in veri["harita"].items() if ch in harfler}
    adlar = set(harita.values()) | set(HEP)
    return {**{k: v for k, v in veri.items() if k not in ("harita", "glifler")},
            "harita": harita,
            "glifler": {ad: g for ad, g in veri["glifler"].items() if ad in adlar}}


def ornek_glifleri() -> str:
    veri = json.loads(GLIFLER.read_text(encoding="utf-8"))
    alt = glif_altkumesi(veri, kurulan_metinler(ORNEK.read_text(encoding="utf-8")))
    return json.dumps(alt, ensure_ascii=False, separators=(",", ":")) + "\n"


def main() -> int:
    tokens = load_tokens(TOKENS)
    failures = contrast_failures(tokens)
    if failures:
        print("Karşıtlık hatası:", *failures, sep="\n  ", file=sys.stderr)
        return 1
    CSS_OUT.parent.mkdir(parents=True, exist_ok=True)
    CSS_OUT.write_text(css_from_tokens(tokens), encoding="utf-8")
    ORNEK_GLIFLER.write_text(ornek_glifleri(), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

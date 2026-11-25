"""tokens.json'dan CSS değişkenlerini üretir ve renk karşıtlığını denetler."""
import json
import sys
from pathlib import Path

BRAND = Path(__file__).resolve().parent
TOKENS = BRAND / "tokens.json"
CSS_OUT = BRAND / "css" / "tokens.css"

HEADER = "/* COUNCIL — generated from tokens.json */"

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
    lines += [f"  --{t['name']}: {t['value']};" for t in tokens["type"]["families"]]
    lines.append("}")
    lines.append("@media (prefers-color-scheme: dark) {")
    lines.append('  :root:not([data-theme="light"]) {')
    lines += _color_lines(tokens, "dark", "    ")
    lines += ["  }", "}"]
    lines.append(':root[data-theme="dark"] {')
    lines += _color_lines(tokens, "dark", "  ")
    lines.append("}")
    for g in tokens["type"]["groups"]:
        lines.append(f".yazi-{g['name']} {{")
        lines.append(f"  font-family: var(--{g['font']});")
        lines.append(f"  font-size: {g['size']};")
        lines.append(f"  line-height: {g['line']};")
        lines.append(f"  font-weight: {g['weight']};")
        if g["tracking"]:
            lines.append(f"  letter-spacing: {g['tracking']};")
        lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    tokens = load_tokens(TOKENS)
    failures = contrast_failures(tokens)
    if failures:
        print("Karşıtlık hatası:", *failures, sep="\n  ", file=sys.stderr)
        return 1
    CSS_OUT.parent.mkdir(parents=True, exist_ok=True)
    CSS_OUT.write_text(css_from_tokens(tokens), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())

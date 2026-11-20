"""Draws the README artwork: hero, "how it works" diagram and section headings.

Everything follows the COUNCIL brand rules: full rings, flat cuts, one stroke weight per drawing,
and the accent colour (kor) reserved for one thing only: the memory.

Run:  python docs/assets/build.py   (needs fonttools; display text is written as outlines of
brand/font/CouncilHalka.ttf, because GitHub cannot load a custom font)
"""
import math
import pathlib

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

HERE = pathlib.Path(__file__).parent
FONT = TTFont(HERE.parent.parent / "brand" / "font" / "CouncilHalka.ttf")
GLYPHS, CMAP, HMTX = FONT.getGlyphSet(), FONT.getBestCmap(), FONT["hmtx"]

KOR = "#E8421F"
THEMES = {  # name -> ink, quiet text, memory label
    "acik": ("#111416", "#5A6066", "#C2330F"),
    "koyu": ("#F4F5F3", "#9BA1A6", "#FF7A5C"),
}
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
WAVE = "M-56 0A56 56 0 0 1 56 0A56 56 0 0 0 168 0"  # the logo's wave, in logo units


def halka(text, cap, x=0, baseline=0, fill="#000", track=60):
    """`text` set in Council Halka as outlines, cap height `cap`. Returns (svg, width)."""
    s, pen_x, parts = cap / 700, 0, []
    for ch in text:
        name = CMAP[ord(ch)]
        pen = SVGPathPen(GLYPHS)
        GLYPHS[name].draw(pen)
        if d := pen.getCommands():
            parts.append(f'<path transform="translate({pen_x} 0)" d="{d}"/>')
        pen_x += HMTX[name][0] + track
    width = (pen_x - track) * s
    return (f'<g fill="{fill}" transform="translate({x:.1f} {baseline:.1f}) scale({s:.5f} -{s:.5f})">'
            + "".join(parts) + "</g>"), width


def label(x, y, text, fill, size=26, anchor="start", weight=600, spacing=2.4):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{SANS}" font-size="{size}" font-weight="{weight}" '
            f'letter-spacing="{spacing}" text-anchor="{anchor}" fill="{fill}">{text}</text>')


def arc(cx, cy, r, a0, a1):
    """Clockwise arc on screen from angle a0 to a1 (degrees, 0 = right, 90 = down)."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{x0:.2f} {y0:.2f}A{r} {r} 0 {large} 1 {x1:.2f} {y1:.2f}"


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" '
            f'aria-label="{title}"><title>{title}</title>{body}</svg>\n')


# ---------------------------------------------------------------- hero

HERO = {
    "tr": dict(lines=("TEK HAFIZA.", "HER YARDIMCI."), memory="HAFIZA",
               seats=("TELEFON", "HERMES", "SUNUCU", "CLAUDE CODE", "CLAUDE.AI", "ANTIGRAVITY"),
               title="COUNCIL: tek hafıza, her yardımcı. Altı yardımcı ve cihaz aynı hafızanın çevresinde."),
    "en": dict(lines=("ONE MEMORY.", "EVERY AGENT."), memory="MEMORY",
               seats=("PHONE", "HERMES", "SERVER", "CLAUDE CODE", "CLAUDE.AI", "ANTIGRAVITY"),
               title="COUNCIL: one memory, every agent. Six agents and devices around the same memory."),
}


def hero(lang, theme):
    t, (ink, quiet, memo) = HERO[lang], THEMES[theme]
    w, h, cx, cy = 1600, 600, 1150, 300
    k = 220 / 168  # logo units -> figure units: the C of the logo becomes a table with six seats
    stroke = 28 * k
    out = []
    # left: wordmark and the statement
    word, _ = halka("COUNCIL", 104, 0, 292, ink)
    out.append(word)
    for i, line in enumerate(t["lines"]):
        g, _ = halka(line, 38, 2, 384 + i * 64, ink if i == 0 else quiet)
        out.append(g)
    # right: the table. Seats are the outer ring cut in six; the memory is the kor ring in the middle.
    # every gap is as wide as the wave plus the same clearance the wave gets where it crosses the memory ring
    gap = math.degrees((28 + 2 * 10) * k / 220)
    out.append(f'<g fill="none" stroke="{ink}" stroke-width="{stroke:.2f}">')
    for i in range(6):
        out.append(f'<path d="{arc(cx, cy, 220, i * 60 + gap / 2, (i + 1) * 60 - gap / 2)}"/>')
    out.append("</g>")
    out.append(
        f'<defs><mask id="kesik" maskUnits="userSpaceOnUse" x="{cx - 260}" y="{cy - 260}" width="520" height="520">'
        f'<rect x="{cx - 260}" y="{cy - 260}" width="520" height="520" fill="#fff"/>'
        f'<path transform="translate({cx} {cy}) scale({k:.5f})" d="{WAVE}" fill="none" stroke="#000" stroke-width="48"/>'
        f'</mask></defs>'
        f'<circle cx="{cx}" cy="{cy}" r="{112 * k:.2f}" fill="none" stroke="{KOR}" stroke-width="{stroke:.2f}" mask="url(#kesik)"/>'
        f'<path transform="translate({cx} {cy}) scale({k:.5f})" d="{WAVE}" '
        f'fill="none" stroke="{ink}" stroke-width="28"/>'
    )
    out.append(label(cx - 22, cy + 62, t["memory"], memo, size=23, anchor="middle", weight=700, spacing=3))
    for i, name in enumerate(t["seats"]):
        a = math.radians(i * 60 + 30)
        c, s = math.cos(a), math.sin(a)
        r = 220 + stroke / 2 + 24
        x, y = cx + r * c, cy + r * s
        anchor = "middle" if abs(c) < 0.3 else ("start" if c > 0 else "end")
        y += 9 if abs(c) >= 0.3 else (28 if s > 0 else -8)
        out.append(label(x, y, name, quiet, anchor=anchor))
    return svg(w, h, "".join(out), t["title"])


# ---------------------------------------------------------------- how it works

FLOW = {
    "tr": dict(
        memory="HAFIZA",
        sessions=(("MAC", "Claude Code"), ("TELEFON", "claude.ai"), ("SUNUCU", "Hermes")),
        steps=(("1 · BAŞLARKEN OKUR", ("kim olduğun, kuralların,", "açık işler, son oturumlar")),
               ("2 · HER MESAJDA", ("yalnız konuyla ilgili notlar",)),
               ("3 · BİTİNCE YAZAR", ("oturum kartı, kararlar,", "değişen notlar"))),
        title="Üç oturum, üç cihaz, tek hafıza: her oturum hafızadan okuyarak başlar, hafızaya yazarak biter.",
    ),
    "en": dict(
        memory="MEMORY",
        sessions=(("MAC", "Claude Code"), ("PHONE", "claude.ai"), ("SERVER", "Hermes")),
        steps=(("1 · STARTS BY READING", ("who you are, your rules,", "open threads, latest sessions")),
               ("2 · WITH EVERY MESSAGE", ("only the notes that matter",)),
               ("3 · ENDS BY WRITING", ("session card, decisions,", "changed notes"))),
        title="Three sessions, three devices, one memory: each session starts by reading it and ends by writing to it.",
    ),
}


def flow(lang, theme):
    t, (ink, quiet, memo) = FLOW[lang], THEMES[theme]
    w, h, y0, r, sw = 1600, 640, 318, 200, 22
    xs = (410, 850, 1290)  # centres of the three sessions; they meet on the memory line
    wave = (f"M{xs[0] - r} {y0}A{r} {r} 0 0 1 {xs[0] + r} {y0}A{r} {r} 0 0 0 {xs[1] + r} {y0}"
            f"A{r} {r} 0 0 1 {xs[2] + r} {y0}")
    out = [
        f'<defs><mask id="gecit" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}">'
        f'<rect width="{w}" height="{h}" fill="#fff"/>'
        f'<path d="{wave}" fill="none" stroke="#000" stroke-width="{sw + 18}" stroke-linecap="square"/></mask></defs>',
        f'<path d="M40 {y0}H{w - 40}" stroke="{KOR}" stroke-width="{sw}" mask="url(#gecit)"/>',
        f'<path d="{wave}" fill="none" stroke="{ink}" stroke-width="{sw}"/>',
        label(40, y0 - 30, t["memory"], memo, size=23, weight=700, spacing=3),
    ]
    for i, (x, (device, agent)) in enumerate(zip(xs, t["sessions"])):
        up = i % 2 == 0
        yy = y0 - 92 if up else y0 + 84
        out.append(label(x, yy, device, ink, size=27, anchor="middle", weight=700, spacing=3))
        out.append(label(x, yy + 36, agent, quiet, size=25, anchor="middle", weight=400, spacing=0.2))
    # the three moments, told on the middle session
    (t1, d1), (t2, d2), (t3, d3) = t["steps"]
    x1 = xs[1] - r + 34
    out.append(label(x1, y0 - 96, t1, ink, size=23, weight=700, spacing=2))
    for j, line in enumerate(d1):
        out.append(label(x1, y0 - 62 + j * 32, line, quiet, size=25, weight=400, spacing=0.2))
    out.append(label(xs[1], y0 + r + 62, t2, ink, size=23, anchor="middle", weight=700, spacing=2))
    for j, line in enumerate(d2):
        out.append(label(xs[1], y0 + r + 96 + j * 32, line, quiet, size=25, anchor="middle", weight=400, spacing=0.2))
    x3 = xs[1] + r + 34
    out.append(label(x3, y0 + 62, t3, ink, size=23, weight=700, spacing=2))
    for j, line in enumerate(d3):
        out.append(label(x3, y0 + 96 + j * 32, line, quiet, size=25, weight=400, spacing=0.2))
    return svg(w, h, "".join(out), t["title"])


# ---------------------------------------------------------------- section headings

HEADINGS = {
    "tr": {"ne-ise-yarar": "NE İŞE YARAR", "nasil-calisir": "NASIL ÇALIŞIR", "neden-farkli": "NEDEN FARKLI",
           "kurulum": "KURULUM", "ilk-bes-dakika": "İLK 5 DAKİKA", "hafizanin-ici": "HAFIZANIN İÇİ",
           "sik-sorulanlar": "SIK SORULANLAR", "belgeler": "BELGELER VE KATKI"},
    "en": {"what-it-does": "WHAT IT DOES", "how-it-works": "HOW IT WORKS", "why-different": "WHY IT IS DIFFERENT",
           "setup": "SETUP", "first-five-minutes": "FIRST 5 MINUTES", "inside-the-memory": "INSIDE THE MEMORY",
           "questions": "QUESTIONS", "docs": "DOCS AND CONTRIBUTING"},
}


def heading(text, n, theme):
    ink = THEMES[theme][0]
    cap, pad = 28, 6
    cut = 64  # each section's ring is cut at its own angle
    start = n * 45 - 90 + cut / 2
    ring = (f'<path d="{arc(pad + 14, pad + 14, 11, start, start + 360 - cut)}" fill="none" '
            f'stroke="{ink}" stroke-width="6"/>')
    word, width = halka(text, cap, pad + 28 + 18, pad + cap, ink, track=70)
    return svg(pad + 28 + 18 + width + pad, cap + 2 * pad, ring + word, text)


def main():
    for lang in ("tr", "en"):
        for theme in THEMES:
            (HERE / f"kapak-{lang}-{theme}.svg").write_text(hero(lang, theme))
            (HERE / f"akis-{lang}-{theme}.svg").write_text(flow(lang, theme))
            for n, (slug, text) in enumerate(HEADINGS[lang].items()):
                (HERE / f"baslik-{slug}-{theme}.svg").write_text(heading(text, n, theme))


if __name__ == "__main__":
    main()

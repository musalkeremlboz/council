"""Draws the README artwork: hero, the animated "how it works" diagram and section headings.

Everything follows the COUNCIL brand rules: full rings, flat cuts, one stroke weight per drawing,
and the accent colour (kor) reserved for one thing only: the memory.

Run:  python docs/assets/build.py   (needs fonttools; display text is written as outlines of
brand/font/CouncilHalka.ttf, because GitHub cannot load a custom font)
"""
import math
import pathlib
import random

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

# The outer ring is the road to 1.0.0: six basic features, clockwise from the top. The first is the
# memory itself. A segment is filled as soon as its feature ships; DONE says how many are filled.
# A feature without a name yet (None) gets a placeholder where its name will be written.
DONE = 1
HERO = {
    "tr": dict(lines=("TEK HAFIZA.", "HER YARDIMCI."),
               systems=("HAFIZA", None, None, None, None, None),
               title="COUNCIL: tek hafıza, her yardımcı. Halkada altı temel özellik var. İlki, hafıza, tamam. "
                     "Öteki beşi yolda; adları eklendiklerinde yazılacak."),
    "en": dict(lines=("ONE MEMORY.", "EVERY AGENT."),
               systems=("MEMORY", None, None, None, None, None),
               title="COUNCIL: one memory, every agent. Six basic features on the ring. The first, memory, is "
                     "complete. The other five are on the way; their names will be written when they are added."),
}

# A name that is not written yet: a row of short bars, like covered text. It rests, then flickers through
# other arrangements for a moment and settles on a new one, the way a line being worked on would.
REST, BLINK = 2.7, 0.09
PERIOD = 2 * REST + 6 * BLINK
SHOWN = {  # arrangement -> the stretches of the period during which it is the one on screen
    "a": [(0, REST), (2 * REST + 3 * BLINK, 2 * REST + 4 * BLINK), (2 * REST + 5 * BLINK, PERIOD)],
    "b": [(REST + BLINK, REST + 2 * BLINK), (REST + 3 * BLINK, 2 * REST + 3 * BLINK)],
    "c": [(REST, REST + BLINK), (REST + 2 * BLINK, REST + 3 * BLINK), (2 * REST + 4 * BLINK, 2 * REST + 5 * BLINK)],
}


def placeholder_css():
    rules = []
    for key, spans in SHOWN.items():
        marks = sorted({0.0, PERIOD} | {t for span in spans for t in span})
        frames = "".join(f"{t / PERIOD * 100:.2f}%{{opacity:{int(any(a <= t < b for a, b in spans))}}}" for t in marks)
        rules.append(f"@keyframes yer-{key}{{{frames}}}.yer-{key}{{animation:yer-{key} {PERIOD:.2f}s step-end infinite}}")
    # without animation only the first arrangement shows
    return (".yer-b,.yer-c{opacity:0}" + "".join(rules)
            + "@media (prefers-reduced-motion:reduce){.yer-a,.yer-b,.yer-c{animation:none!important}}")


def placeholder(x, y, anchor, n, fill):
    rng, out = random.Random(7 + n), []
    for key in "abc":
        widths = [rng.choice((16, 24, 34, 46, 60)) for _ in range(rng.choice((3, 3, 4)))]
        total = sum(widths) + 9 * (len(widths) - 1)
        left = x - {"start": 0, "middle": total / 2, "end": total}[anchor]
        bars = []
        for width in widths:
            bars.append(f'<rect x="{left:.1f}" y="{y - 16:.1f}" width="{width}" height="12"/>')
            left += width + 9
        out.append(f'<g class="yer-{key}" style="animation-delay:-{n * 1.37:.2f}s" fill="{fill}">{"".join(bars)}</g>')
    return "".join(out)


def band(cx, cy, r, width, a0, a1):
    """Outline of a ring segment of the given width, from angle a0 to a1 (clockwise on screen)."""
    def pt(radius, a):
        return f"{cx + radius * math.cos(math.radians(a)):.2f} {cy + radius * math.sin(math.radians(a)):.2f}"
    ro, ri = r + width / 2, r - width / 2
    return f"M{pt(ro, a0)}A{ro:.2f} {ro:.2f} 0 0 1 {pt(ro, a1)}L{pt(ri, a1)}A{ri:.2f} {ri:.2f} 0 0 0 {pt(ri, a0)}Z"


def hero(lang, theme):
    t, (ink, quiet, memo) = HERO[lang], THEMES[theme]
    w, h, cx, cy = 1600, 600, 1150, 300
    k = 220 / 168  # logo units -> figure units
    stroke = 28 * k
    out = []
    word, _ = halka("COUNCIL", 104, 0, 292, ink)
    out.append(word)
    for i, line in enumerate(t["lines"]):
        g, _ = halka(line, 38, 2, 384 + i * 64, ink if i == 0 else quiet)
        out.append(g)
    # every gap is as wide as the wave plus the same clearance the wave gets where it crosses the memory ring
    gap = math.degrees((28 + 2 * 10) * k / 220)
    line_w = 3.5
    for n, name in enumerate(t["systems"]):
        mid = 270 + n * 60  # the first system sits at the top
        a0, a1 = mid - 30 + gap / 2, mid + 30 - gap / 2
        if n < DONE:
            out.append(f'<path d="{band(cx, cy, 220, stroke, a0, a1)}" fill="{ink}"/>')
        else:
            inset = math.degrees(line_w / 2 / 220)
            out.append(f'<path d="{band(cx, cy, 220, stroke - line_w, a0 + inset, a1 - inset)}" fill="none" '
                       f'stroke="{quiet}" stroke-width="{line_w}"/>')
        c, s = math.cos(math.radians(mid)), math.sin(math.radians(mid))
        r = 220 + stroke / 2 + 24
        x, y = cx + r * c, cy + r * s
        anchor = "middle" if abs(c) < 0.3 else ("start" if c > 0 else "end")
        y += 9 if abs(c) >= 0.3 else (28 if s > 0 else -8)
        if name:
            out.append(label(x, y, name, ink if n < DONE else quiet, anchor=anchor, weight=700 if n < DONE else 600))
        else:
            out.append(placeholder(x, y, anchor, n, quiet))
    out.append(
        f'<defs><mask id="kesik" maskUnits="userSpaceOnUse" x="{cx - 260}" y="{cy - 260}" width="520" height="520">'
        f'<rect x="{cx - 260}" y="{cy - 260}" width="520" height="520" fill="#fff"/>'
        f'<path transform="translate({cx} {cy}) scale({k:.5f})" d="{WAVE}" fill="none" stroke="#000" stroke-width="48"/>'
        f'</mask></defs>'
        f'<circle cx="{cx}" cy="{cy}" r="{112 * k:.2f}" fill="none" stroke="{KOR}" stroke-width="{stroke:.2f}" mask="url(#kesik)"/>'
        f'<path transform="translate({cx} {cy}) scale({k:.5f})" d="{WAVE}" fill="none" stroke="{ink}" stroke-width="28"/>'
    )
    return svg(w, h, f"<style>{placeholder_css()}</style>" + "".join(out), t["title"])


# ---------------------------------------------------------------- how it works (animated)

FLOW = {
    "tr": dict(
        memory="HAFIZA",
        sessions=(("1. OTURUM", "dün"), ("2. OTURUM", "bugün"), ("3. OTURUM", "yarın")),
        steps=(("1 · BAŞLARKEN OKUR", ("kim olduğun, kuralların,", "açık işler, son oturumlar")),
               ("2 · HER MESAJDA", ("yalnız konuyla ilgili notlar",)),
               ("3 · BİTİNCE YAZAR", ("oturum kartı, kararlar,", "değişen notlar"))),
        title="Üç oturum, tek hafıza: her oturum hafızadan okuyarak başlar, her mesajda ilgili notları alır, "
              "hafızaya yazarak biter. Sonraki oturum bir öncekinin bıraktığı yerden başlar.",
    ),
    "en": dict(
        memory="MEMORY",
        sessions=(("SESSION 1", "yesterday"), ("SESSION 2", "today"), ("SESSION 3", "tomorrow")),
        steps=(("1 · STARTS BY READING", ("who you are, your rules,", "open threads, latest sessions")),
               ("2 · WITH EVERY MESSAGE", ("only the notes that matter",)),
               ("3 · ENDS BY WRITING", ("session card, decisions,", "changed notes"))),
        title="Three sessions, one memory: each session starts by reading the memory, gets the relevant notes with "
              "every message, and ends by writing to it. The next session starts where the last one left off.",
    ),
}

LOOP = 14.0   # seconds for the whole animation
SESSION = 3.5  # seconds one session takes to draw
FADE = (12.9, 13.6)  # the finished picture fades out between these times, then the loop restarts


def keyframes(name, frames):
    """CSS @keyframes from [(seconds, "css declarations")]; the state before the first frame is the first frame's."""
    frames = sorted(frames)
    if frames[0][0] > 0:
        frames.insert(0, (0, frames[0][1]))
    if frames[-1][0] < LOOP:
        frames.append((LOOP, frames[-1][1]))
    return f"@keyframes {name}{{" + "".join(f"{t / LOOP * 100:.2f}%{{{css}}}" for t, css in frames) + "}"


def flow(lang, theme):
    t, (ink, quiet, memo) = FLOW[lang], THEMES[theme]
    w, h, y0, r, sw = 1600, 640, 318, 200, 22
    xs = (430, 430 + 2 * r, 430 + 4 * r)  # centres of the three sessions; each ends where the next begins
    wave = (f"M{xs[0] - r} {y0}A{r} {r} 0 0 1 {xs[0] + r} {y0}A{r} {r} 0 0 0 {xs[1] + r} {y0}"
            f"A{r} {r} 0 0 1 {xs[2] + r} {y0}")
    length = 1  # the path is drawn with pathLength="1", so dash offsets are fractions of the whole wave
    css, body = [], []

    def animate(cls, frames):
        css.append(keyframes(cls, frames) + f".{cls}{{animation:{cls} {LOOP}s linear infinite}}")
        return cls

    f0, f1 = FADE
    # the sessions draw themselves one after another, hold, fade, and start again
    animate("dalga", [(0, f"stroke-dashoffset:{length};opacity:1"),
                      *[((i + 1) * SESSION, f"stroke-dashoffset:{length * (2 - i) / 3:.4f};opacity:1") for i in range(3)],
                      (f0, "stroke-dashoffset:0;opacity:1"), (f1, "stroke-dashoffset:0;opacity:0")])

    def appear(cls, at):
        return animate(cls, [(0, "opacity:0"), (at, "opacity:0"), (at + 0.35, "opacity:1"),
                             (f0, "opacity:1"), (f1, "opacity:0")])

    body.append(
        f'<defs><mask id="gecit" maskUnits="userSpaceOnUse" x="0" y="0" width="{w}" height="{h}">'
        f'<rect width="{w}" height="{h}" fill="#fff"/>'
        f'<path d="{wave}" fill="none" stroke="#000" stroke-width="{sw + 18}" stroke-linecap="square"/></mask></defs>'
        f'<path d="M40 {y0}H{w - 40}" stroke="{KOR}" stroke-width="{sw}" mask="url(#gecit)"/>'
        f'<path class="dalga" d="{wave}" fill="none" stroke="{ink}" stroke-width="{sw}" pathLength="1" '
        f'stroke-dasharray="1 1"/>'
        + label(40, y0 - 30, t["memory"], memo, size=23, weight=700, spacing=3)
    )
    for i, (x, (title, sub)) in enumerate(zip(xs, t["sessions"])):
        up, start = i % 2 == 0, i * SESSION
        side = -1 if up else 1  # the session's arc lies above (-1) or below (+1) the memory line
        yy = y0 - 92 if up else y0 + 84
        body.append(f'<g class="{appear(f"ad{i}", start + 0.2)}">'
                    + label(x, yy, title, ink, size=27, anchor="middle", weight=700, spacing=3)
                    + label(x, yy + 36, sub, quiet, size=25, anchor="middle", weight=400, spacing=0.2) + "</g>")
        turn = -side  # screen-clockwise rotation carries a point from the left end over an upper arc
        # 1: what the session reads leaves the memory and rides the first stretch of the arc
        read = animate(f"oku{i}", [(0, "opacity:0;transform:rotate(0deg)"),
                                   (start + 0.02, "opacity:0;transform:rotate(0deg)"),
                                   (start + 0.03, "opacity:1;transform:rotate(0deg)"),
                                   (start + 35 / 180 * SESSION, f"opacity:1;transform:rotate({35 * turn}deg)"),
                                   (start + 35 / 180 * SESSION + 0.25, f"opacity:0;transform:rotate({35 * turn}deg)")])
        # 3: what the session learned rides the last stretch of the arc back into the memory
        write = animate(f"yaz{i}", [(0, f"opacity:0;transform:rotate({145 * turn}deg)"),
                                    (start + 145 / 180 * SESSION - 0.01, f"opacity:0;transform:rotate({145 * turn}deg)"),
                                    (start + 145 / 180 * SESSION, f"opacity:1;transform:rotate({145 * turn}deg)"),
                                    (start + SESSION, f"opacity:1;transform:rotate({180 * turn}deg)"),
                                    (start + SESSION + 0.3, f"opacity:0;transform:rotate({180 * turn}deg)")])
        body.append(f'<g transform="translate({x} {y0})">'
                    f'<g class="nokta {read}"><circle cx="{-r}" cy="0" r="14" fill="{KOR}"/></g>'
                    f'<g class="nokta {write}"><circle cx="{-r}" cy="0" r="14" fill="{ink}"/></g></g>')
        # 2: with each message, the notes that matter rise from the memory to the session
        for m, (dx, at) in enumerate(((-120, 1.25), (120, 2.05))):
            travel = side * (math.sqrt(r * r - dx * dx) - sw / 2 - 9)
            note = animate(f"not{i}{m}", [(0, "opacity:0;transform:translateY(0px)"),
                                          (start + at - 0.01, "opacity:0;transform:translateY(0px)"),
                                          (start + at, "opacity:1;transform:translateY(0px)"),
                                          (start + at + 0.55, f"opacity:1;transform:translateY({travel:.1f}px)"),
                                          (start + at + 0.75, f"opacity:0;transform:translateY({travel:.1f}px)")])
            body.append(f'<circle class="nokta {note}" cx="{x + dx}" cy="{y0}" r="9" fill="{KOR}"/>')
    # the three moments are named on the middle session, each as it happens
    (t1, d1), (t2, d2), (t3, d3) = t["steps"]
    x1, x3 = xs[1] - r + 34, xs[1] + r + 34
    step1 = label(x1, y0 - 96, t1, ink, size=23, weight=700, spacing=2) + "".join(
        label(x1, y0 - 62 + j * 32, line, quiet, size=25, weight=400, spacing=0.2) for j, line in enumerate(d1))
    step2 = label(xs[1], y0 + r + 62, t2, ink, size=23, anchor="middle", weight=700, spacing=2) + "".join(
        label(xs[1], y0 + r + 96 + j * 32, line, quiet, size=25, anchor="middle", weight=400, spacing=0.2)
        for j, line in enumerate(d2))
    step3 = label(x3, y0 + 62, t3, ink, size=23, weight=700, spacing=2) + "".join(
        label(x3, y0 + 96 + j * 32, line, quiet, size=25, weight=400, spacing=0.2) for j, line in enumerate(d3))
    body.append(f'<g class="{appear("adim1", SESSION)}">{step1}</g>'
                f'<g class="{appear("adim2", SESSION + 1.25)}">{step2}</g>'
                f'<g class="{appear("adim3", SESSION + 145 / 180 * SESSION)}">{step3}</g>')
    # without animation (reduced motion, or a viewer that ignores it) the finished picture is shown
    style = ("<style>.nokta{opacity:0}" + "".join(css)
             + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>")
    return svg(w, h, style + "".join(body), t["title"])


# ---------------------------------------------------------------- section headings

HEADINGS = {
    "tr": {"ne-ise-yarar": "NE İŞE YARAR", "nasil-calisir": "NASIL ÇALIŞIR", "neden-farkli": "NEDEN FARKLI",
           "kurulum": "KURULUM", "ilk-bes-dakika": "İLK 5 DAKİKA", "hafizanin-ici": "HAFIZANIN İÇİ",
           "sik-sorulanlar": "SIK SORULANLAR", "belgeler": "BELGELER VE KATKI",
           "yol-haritasi": "YOL HARİTASI", "desteklenen-yardimcilar": "DESTEKLENEN YARDIMCILAR"},
    "en": {"what-it-does": "WHAT IT DOES", "how-it-works": "HOW IT WORKS", "why-different": "WHY IT IS DIFFERENT",
           "setup": "SETUP", "first-five-minutes": "FIRST 5 MINUTES", "inside-the-memory": "INSIDE THE MEMORY",
           "questions": "QUESTIONS", "docs": "DOCS AND CONTRIBUTING",
           "roadmap": "ROADMAP", "supported-agents": "SUPPORTED AGENTS"},
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

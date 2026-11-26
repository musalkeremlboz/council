"""COUNCIL Halka: the COUNCIL display typeface, built from the logo's rules.

Every glyph is made of three primitives: straight bars, ring segments cut from
perfect circles, and slanted bars. One stroke weight, flat cut ends.

Run:  python build_font.py   (needs fonttools, skia-pathops, brotli)
Writes CouncilHalka.ttf, CouncilHalka.woff2 and glifler.json next to this file.
"""
import json
import math
import pathlib

from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from pathops import Path

FAMILY = "Council Halka"
VERSION = "0.2"
UPM = 1000
H = 700          # cap height, also the lowercase ascender
XH = 500         # x-height
DESC_LC = -200   # lowercase descender
S = 100          # stroke weight
ASC, DESC = 960, -260
PAREN = math.degrees(math.asin(0.8))  # half the arc of ( and ): they run from -100 to 700


class Glyph:
    def __init__(self, width, lsb=55, rsb=55):
        self.width, self.lsb, self.rsb = width, lsb, rsb
        self.path = Path()
        self.pen = self.path.getPen()
        self.ilkeller = []  # the primitives drawn so far, exported to glifler.json

    def bar(self, x, y, w, h):
        self.ilkeller.append({"t": "b", "x": x, "y": y, "w": w, "h": h})
        p = self.pen
        p.moveTo((x, y)); p.lineTo((x, y + h)); p.lineTo((x + w, y + h)); p.lineTo((x + w, y)); p.closePath()
        return self

    def poly(self, pts):
        self.ilkeller.append({"t": "p", "noktalar": [list(q) for q in pts]})
        area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
        if area > 0:
            pts = pts[::-1]
        p = self.pen
        p.moveTo(pts[0])
        for q in pts[1:]:
            p.lineTo(q)
        p.closePath()
        return self

    def _arc(self, cx, cy, r, a0, a1):
        """Cubic segments along a circle from angle a0 to a1 (degrees)."""
        n = max(1, math.ceil(abs(a1 - a0) / 90))
        step = math.radians(a1 - a0) / n
        k = 4 / 3 * math.tan(step / 4)
        a = math.radians(a0)
        for _ in range(n):
            b = a + step
            p0 = (cx + r * math.cos(a), cy + r * math.sin(a))
            p3 = (cx + r * math.cos(b), cy + r * math.sin(b))
            c1 = (p0[0] - k * r * math.sin(a), p0[1] + k * r * math.cos(a))
            c2 = (p3[0] + k * r * math.sin(b), p3[1] - k * r * math.cos(b))
            self.pen.curveTo(c1, c2, p3)
            a = b

    def ring(self, cx, cy, ro, a0=0, a1=360, s=S):
        """Ring segment, outer radius ro, from a0 to a1 counter-clockwise."""
        self.ilkeller.append({"t": "r", "cx": cx, "cy": cy, "r": ro, "a0": a0, "a1": a1, "s": s})
        ri = ro - s
        p = self.pen
        if a1 - a0 >= 360:
            p.moveTo((cx + ro, cy)); self._arc(cx, cy, ro, 0, -360); p.closePath()
            p.moveTo((cx + ri, cy)); self._arc(cx, cy, ri, 0, 360); p.closePath()
            return self
        r1, r0 = math.radians(a1), math.radians(a0)
        p.moveTo((cx + ro * math.cos(r1), cy + ro * math.sin(r1)))
        self._arc(cx, cy, ro, a1, a0)
        p.lineTo((cx + ri * math.cos(r0), cy + ri * math.sin(r0)))
        self._arc(cx, cy, ri, a0, a1)
        p.closePath()
        return self


def glyphs():
    g = {}
    R = H / 2  # 350: the full O

    def arch(w, bar_y=None):
        gl = Glyph(w).bar(0, 0, S, H - w / 2).bar(w - S, 0, S, H - w / 2).ring(w / 2, H - w / 2, w / 2, 0, 180)
        if bar_y is not None:
            gl.bar(0, bar_y, w, S)
        return gl

    g["A"] = arch(600, 210)
    g["B"] = (Glyph(350, 55, 35).bar(0, 0, S, H).bar(0, 600, 150, S).bar(0, 300, 150, S).bar(0, 0, 150, S)
              .ring(150, 500, 200, -90, 90).ring(150, 200, 200, -90, 90))
    g["C"] = Glyph(600, 35, 20).ring(R, R, R, 45, 315)
    g["D"] = Glyph(550, 55, 35).bar(0, 0, S, H).bar(0, 600, 200, S).bar(0, 0, 200, S).ring(200, R, R, -90, 90)
    g["E"] = Glyph(430, 55, 30).bar(0, 0, S, H).bar(0, 600, 430, S).bar(0, 300, 380, S).bar(0, 0, 430, S)
    g["F"] = Glyph(430, 55, 20).bar(0, 0, S, H).bar(0, 600, 430, S).bar(0, 300, 380, S)
    g["G"] = Glyph(700, 35, 45).ring(R, R, R, 45, 360).bar(R, 250, R, S)
    g["H"] = Glyph(600).bar(0, 0, S, H).bar(500, 0, S, H).bar(0, 300, 600, S)
    g["I"] = Glyph(100).bar(0, 0, S, H)
    g["J"] = Glyph(350, 25, 55).ring(175, 175, 175, 180, 360).bar(250, 175, S, 525)
    g["K"] = (Glyph(520, 55, 15).bar(0, 0, S, H)
              .poly([(60, 330), (195, 330), (520, 700), (385, 700)])
              .poly([(60, 370), (195, 370), (520, 0), (385, 0)]))
    g["L"] = Glyph(400, 55, 25).bar(0, 0, S, H).bar(0, 0, 400, S)
    g["M"] = (Glyph(900).bar(0, 0, S, 450).bar(400, 0, S, 450).bar(800, 0, S, 450)
              .ring(250, 450, 250, 0, 180).ring(650, 450, 250, 0, 180))
    g["N"] = arch(600)
    g["O"] = Glyph(700, 35, 35).ring(R, R, R)
    g["P"] = (Glyph(350, 55, 30).bar(0, 0, S, H).bar(0, 600, 150, S).bar(0, 300, 150, S)
              .ring(150, 500, 200, -90, 90))
    g["Q"] = Glyph(700, 35, 35).ring(R, R, R).poly([(400, 215), (535, 215), (715, 0), (580, 0)])
    g["R"] = (Glyph(370, 55, 15).bar(0, 0, S, H).bar(0, 600, 150, S).bar(0, 300, 150, S)
              .ring(150, 500, 200, -90, 90).poly([(120, 330), (255, 330), (385, 0), (250, 0)]))
    g["S"] = Glyph(400, 35, 35).ring(200, 500, 200, 30, 270).ring(200, 200, 200, -150, 90)
    g["T"] = Glyph(500, 20, 20).bar(0, 600, 500, S).bar(200, 0, S, 600)
    g["U"] = Glyph(600).bar(0, 300, S, 400).bar(500, 300, S, 400).ring(300, 300, 300, 180, 360)
    g["V"] = (Glyph(600, 10, 10).poly([(0, 700), (128, 700), (364, 0), (236, 0)])
              .poly([(472, 700), (600, 700), (364, 0), (236, 0)]))
    g["W"] = (Glyph(900).bar(0, 250, S, 450).bar(400, 250, S, 450).bar(800, 250, S, 450)
              .ring(250, 250, 250, 180, 360).ring(650, 250, 250, 180, 360))
    g["X"] = (Glyph(560, 15, 15).poly([(0, 700), (135, 700), (560, 0), (425, 0)])
              .poly([(425, 700), (560, 700), (135, 0), (0, 0)]))
    g["Y"] = (Glyph(600).bar(0, 500, S, 200).bar(500, 500, S, 200).ring(300, 500, 300, 180, 360)
              .bar(250, 0, S, 300))
    g["Z"] = (Glyph(520, 25, 25).bar(0, 600, 520, S).bar(0, 0, 520, S)
              .poly([(375, 600), (520, 600), (145, 100), (0, 100)]))

    def with_marks(base, *marks):
        src = g[base]
        gl = Glyph(src.width, src.lsb, src.rsb)
        src.path.draw(gl.pen)
        gl.ilkeller = [dict(i) for i in src.ilkeller]
        for m in marks:
            m(gl)
        return gl

    dot = lambda x: (lambda gl: gl.bar(x, 800, S, S))
    tick = lambda x: (lambda gl: gl.bar(x, -210, S, 130))
    breve = lambda x: (lambda gl: gl.ring(x, 930, 135, 180, 360, 70))

    g["Ccedilla"] = with_marks("C", tick(300))
    g["Scedilla"] = with_marks("S", tick(150))
    g["Gbreve"] = with_marks("G", breve(350))
    g["Idotaccent"] = with_marks("I", dot(0))
    g["Odieresis"] = with_marks("O", dot(185), dot(415))
    g["Udieresis"] = with_marks("U", dot(135), dot(365))

    g["zero"] = (Glyph(500, 40, 40).bar(0, 250, S, 200).bar(400, 250, S, 200)
                 .ring(250, 450, 250, 0, 180).ring(250, 250, 250, 180, 360))
    g["one"] = Glyph(250, 40, 60).bar(150, 0, S, H).bar(0, 600, 250, S)
    # The slanted stroke leaves the bowl along its tangent, so the two join without a gap.
    g["two"] = (Glyph(500, 40, 40).ring(250, 450, 250, -55.95, 180)
                .poly([(334.0, 325.7), (390.0, 242.9), (178.5, 100), (0, 100)]).bar(0, 0, 500, S))
    g["three"] = Glyph(400, 35, 40).ring(200, 500, 200, -90, 150).ring(200, 200, 200, -150, 90)
    g["four"] = (Glyph(520, 25, 35).bar(360, 0, S, H).bar(0, 200, 520, S)
                 .poly([(275, 700), (410, 700), (135, 300), (0, 300)]))
    g["five"] = (Glyph(450, 45, 40).bar(40, 600, 380, S).bar(40, 350, S, 350).bar(40, 350, 185, S)
                 .ring(225, 225, 225, -150, 90))
    g["six"] = Glyph(460, 35, 35).ring(230, 230, 230).ring(500, 230, 500, 110, 180)
    g["seven"] = Glyph(480, 25, 20).bar(0, 600, 480, S).poly([(335, 600), (480, 600), (195, 0), (50, 0)])
    g["eight"] = Glyph(400, 40, 40).ring(200, 500, 200).ring(200, 200, 200)
    g["nine"] = Glyph(460, 35, 35).ring(230, 470, 230).ring(-40, 470, 500, -70, 0)

    g["space"] = Glyph(260, 0, 0)
    g["period"] = Glyph(100, 50, 50).bar(0, 0, S, S)
    g["comma"] = Glyph(100, 50, 50).bar(0, 0, S, S).poly([(40, 0), (100, 0), (60, -150), (0, -150)])
    g["colon"] = Glyph(100, 50, 50).bar(0, 0, S, S).bar(0, 400, S, S)
    g["hyphen"] = Glyph(300, 50, 50).bar(0, 300, 300, S)
    g["periodcentered"] = Glyph(100, 80, 80).bar(0, 300, S, S)
    g["exclam"] = Glyph(100, 55, 55).bar(0, 0, S, S).bar(0, 220, S, 480)
    g["slash"] = Glyph(420, 15, 15).poly([(285, 700), (420, 700), (135, 0), (0, 0)])
    g["question"] = (Glyph(400, 35, 35).ring(200, 500, 200, -90, 180).bar(150, 220, S, 180)
                     .bar(150, 0, S, S))

    lowercase(g, with_marks, tick)
    punctuation(g)
    return g


def lowercase(g, with_marks, tick):
    """a–z and the Turkish lowercase: x-height XH, ascenders to H, descenders to DESC_LC."""
    r = XH / 2                                 # 250: the full o
    breve = lambda x: (lambda gl: gl.ring(x, 735, 135, 180, 360, 70))  # the capital breve, lowered onto XH
    bowl = lambda gl: gl.ring(r, r, r)
    # g, j, y: the stem ending at x turns through a quarter ring into a flat foot on the descender
    foot = lambda gl, x: gl.bar(x - S, -50, S, XH + 50).ring(x - 150, -50, 150, 270, 360).bar(0, DESC_LC, x - 150, S)
    dot = lambda x: (lambda gl: gl.bar(x, 600, S, S))
    # the e's ring starts where its outline crosses the top of the bar, and the bar ends there too: no step
    e_top = math.degrees(math.asin(S / 2 / r))
    e_end = r + math.sqrt(r * r - (S / 2) ** 2)

    g["a"] = bowl(Glyph(500, 30, 50)).bar(400, 0, S, XH)
    g["b"] = bowl(Glyph(500, 50, 30)).bar(0, 0, S, H)
    g["c"] = Glyph(500, 30, 20).ring(r, r, r, 45, 315)
    g["d"] = bowl(Glyph(500, 30, 50)).bar(400, 0, S, H)
    g["e"] = Glyph(500, 30, 25).ring(r, r, r, e_top, 315).bar(50, r - S / 2, e_end - 50, S)
    g["f"] = Glyph(356, 20, 10).bar(100, 0, S, 550).ring(250, 550, 150, 45, 180).bar(0, 400, 300, S)
    g["g"] = foot(bowl(Glyph(500, 30, 50)), 500)
    g["h"] = Glyph(500, 50, 50).bar(0, 0, S, H).bar(400, 0, S, r).ring(r, r, r, 0, 180)
    g["dotlessi"] = Glyph(100, 50, 50).bar(0, 0, S, XH)
    g["i"] = dot(0)(Glyph(100, 50, 50).bar(0, 0, S, XH))
    g["j"] = dot(150)(foot(Glyph(250, 20, 50), 250))
    g["k"] = (Glyph(450, 50, 15).bar(0, 0, S, H)
              .poly([(60, 230), (195, 230), (450, 500), (315, 500)])
              .poly([(60, 270), (195, 270), (450, 0), (315, 0)]))
    g["l"] = Glyph(150, 50, 15).bar(0, 150, S, H - 150).ring(150, 150, 150, 180, 270)
    g["m"] = (Glyph(800, 50, 50).bar(0, 0, S, XH).bar(350, 0, S, 275).bar(700, 0, S, 275)
              .ring(225, 275, 225, 0, 180).ring(575, 275, 225, 0, 180))
    g["n"] = Glyph(500, 50, 50).bar(0, 0, S, XH).bar(400, 0, S, r).ring(r, r, r, 0, 180)
    g["o"] = bowl(Glyph(500, 30, 30))
    g["p"] = bowl(Glyph(500, 50, 30)).bar(0, DESC_LC, S, XH - DESC_LC)
    g["q"] = bowl(Glyph(500, 30, 50)).bar(400, DESC_LC, S, XH - DESC_LC)
    g["r"] = Glyph(375, 50, 15).bar(0, 0, S, XH).ring(r, r, r, 60, 180)
    g["s"] = Glyph(300, 30, 30).ring(150, 350, 150, 30, 270).ring(150, 150, 150, -150, 90)
    g["t"] = Glyph(300, 20, 15).bar(100, 150, S, 500).bar(0, 400, 300, S).ring(250, 150, 150, 180, 270)
    g["u"] = Glyph(500, 50, 50).bar(0, r, S, r).bar(400, 0, S, XH).ring(r, r, r, 180, 360)
    g["v"] = (Glyph(440, 10, 10).poly([(0, 500), (120, 500), (280, 0), (160, 0)])
              .poly([(320, 500), (440, 500), (280, 0), (160, 0)]))
    g["w"] = (Glyph(800, 50, 50).bar(0, 225, S, 275).bar(350, 225, S, 275).bar(700, 225, S, 275)
              .ring(225, 225, 225, 180, 360).ring(575, 225, 225, 180, 360))
    g["x"] = (Glyph(420, 15, 15).poly([(0, 500), (125, 500), (420, 0), (295, 0)])
              .poly([(295, 500), (420, 500), (125, 0), (0, 0)]))
    g["y"] = foot(Glyph(500, 50, 50).bar(0, r, S, r).ring(r, r, r, 180, 360), 500)
    g["z"] = (Glyph(420, 25, 25).bar(0, 400, 420, S).bar(0, 0, 420, S)
              .poly([(270, 400), (420, 400), (150, 100), (0, 100)]))

    g["ccedilla"] = with_marks("c", tick(200))
    g["gbreve"] = with_marks("g", breve(250))
    g["odieresis"] = with_marks("o", dot(85), dot(315))
    g["scedilla"] = with_marks("s", tick(100))
    g["udieresis"] = with_marks("u", dot(85), dot(315))


def punctuation(g):
    g["ampersand"] = (Glyph(560, 30, 20).ring(230, 545, 155).ring(230, 220, 220, 90, 405)
                      .poly([(105, 470), (240, 470), (560, 0), (425, 0)]))
    g["at"] = (Glyph(800, 35, 35).ring(400, 300, 400, 30, 330).ring(400, 300, 175)
               .bar(475, 125, S, 350))
    g["numbersign"] = (Glyph(560, 25, 25).bar(120, 0, S, H).bar(340, 0, S, H)
                       .bar(0, 180, 560, S).bar(0, 420, 560, S))
    g["percent"] = (Glyph(700, 25, 25).ring(150, 550, 150).ring(550, 150, 150)
                    .poly([(565, 700), (700, 700), (135, 0), (0, 0)]))
    g["plus"] = Glyph(400, 40, 40).bar(0, 300, 400, S).bar(150, 150, S, 400)
    g["equal"] = Glyph(400, 40, 40).bar(0, 200, 400, S).bar(0, 400, 400, S)
    g["parenleft"] = Glyph(260, 50, 30).ring(500, 300, 500, 180 - PAREN, 180 + PAREN)
    g["parenright"] = Glyph(260, 30, 50).ring(-240, 300, 500, -PAREN, PAREN)
    g["quotedbl"] = Glyph(280, 50, 50).bar(0, 500, S, 200).bar(180, 500, S, 200)
    g["quotesingle"] = Glyph(100, 50, 50).bar(0, 500, S, 200)
    g["semicolon"] = (Glyph(100, 50, 50).bar(0, 0, S, S).poly([(40, 0), (100, 0), (60, -150), (0, -150)])
                      .bar(0, 400, S, S))
    g["ellipsis"] = Glyph(500, 50, 50).bar(0, 0, S, S).bar(200, 0, S, S).bar(400, 0, S, S)
    g["arrowright"] = (Glyph(600, 40, 40).bar(0, 300, 530, S)
                       .poly([(209, 600), (350, 600), (600, 350), (459, 350)])
                       .poly([(209, 100), (350, 100), (600, 350), (459, 350)]))


CMAP = {
    **{ord(c): c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"},
    ord("İ"): "Idotaccent", ord("ı"): "dotlessi",
    ord("Ç"): "Ccedilla", ord("ç"): "ccedilla", ord("Ş"): "Scedilla", ord("ş"): "scedilla",
    ord("Ğ"): "Gbreve", ord("ğ"): "gbreve", ord("Ö"): "Odieresis", ord("ö"): "odieresis",
    ord("Ü"): "Udieresis", ord("ü"): "udieresis",
    **{ord(str(i)): n for i, n in enumerate(
        ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])},
    ord(" "): "space", ord("."): "period", ord(","): "comma", ord(":"): "colon",
    ord("-"): "hyphen", ord("·"): "periodcentered", ord("!"): "exclam", ord("/"): "slash",
    ord("?"): "question", ord("&"): "ampersand", ord("@"): "at", ord("#"): "numbersign",
    ord("%"): "percent", ord("+"): "plus", ord("="): "equal", ord("("): "parenleft",
    ord(")"): "parenright", ord('"'): "quotedbl", ord("'"): "quotesingle", ord(";"): "semicolon",
    ord("\u2026"): "ellipsis", ord("\u2192"): "arrowright",
}

# Pair adjustments in font units, closing the gaps that open where a bar or an arm overhangs
# a ring or a stem ("LA", "To", "ro"). Accented letters kern like their base letter.
KERN: dict[tuple[str, str], int] = {
    **{("L", b): v for b, v in {"T": -100, "V": -90, "Y": -90, "W": -50, "A": -40, "O": -40, "C": -40,
                                "G": -40, "Q": -40, "U": -40, "quotesingle": -100, "quotedbl": -100}.items()},
    ("T", "A"): -50, ("A", "T"): -50, ("F", "A"): -50, ("P", "A"): -40, ("V", "A"): -30, ("A", "V"): -30,
    **{(a, b): -40 for a in "TX" for b in "OCGQ"}, **{("K", b): -60 for b in "OCGQ"},
    **{(a, b): -40 for a in "OQ" for b in "TX"},
    **{("T", b): -80 for b in "acegoqs"}, **{("T", b): -60 for b in "mnpruvwxyz"},
    **{(a, b): -50 for a in "FV" for b in "aceo"}, **{("P", b): -40 for b in "aceo"},
    **{("Y", b): -40 for b in "aceo"}, ("V", "u"): -30,
    **{("r", b): -40 for b in "acegoqs"}, **{("f", b): -30 for b in "aceo"}, **{("k", b): -40 for b in "aceo"},
    **{(a, b): v for a, v in {"T": -80, "F": -80, "P": -70, "V": -60, "Y": -80, "r": -80}.items()
       for b in ("period", "comma", "ellipsis")},
}
MARKED = {"Ccedilla": "C", "Scedilla": "S", "Gbreve": "G", "Idotaccent": "I", "Odieresis": "O",
          "Udieresis": "U", "ccedilla": "c", "scedilla": "s", "gbreve": "g", "odieresis": "o",
          "udieresis": "u", "dotlessi": "i"}


def kern_feature():
    """The KERN table as a feature file, with each accented letter taking its base letter's pairs."""
    pairs = dict(KERN)
    for (a, b), v in KERN.items():
        for la in [a] + [m for m, base in MARKED.items() if base == a]:
            for rb in [b] + [m for m, base in MARKED.items() if base == b]:
                pairs.setdefault((la, rb), v)
    rules = "".join(f"  pos {a} {b} {v};\n" for (a, b), v in sorted(pairs.items()))
    return "languagesystem DFLT dflt;\nlanguagesystem latn dflt;\nfeature kern {\n" + rules + "} kern;\n"


def replay(ilkeller, width=0, lsb=0, rsb=0):
    """A Glyph redrawn from exported primitives, through the same bar/ring/poly code path."""
    gl = Glyph(width, lsb, rsb)
    for i in ilkeller:
        if i["t"] == "b":
            gl.bar(i["x"], i["y"], i["w"], i["h"])
        elif i["t"] == "r":
            gl.ring(i["cx"], i["cy"], i["r"], i["a0"], i["a1"], i["s"])
        else:
            gl.poly([tuple(q) for q in i["noktalar"]])
    return gl


def ttglyph(gl):
    """The TrueType glyph for a Glyph: merged outline, shifted by its left side bearing."""
    from fontTools.pens.transformPen import TransformPen
    path = Path()
    gl.path.draw(path.getPen())
    path.simplify(fix_winding=True)
    shifted = Path()
    path.draw(TransformPen(shifted.getPen(), (1, 0, 0, 1, gl.lsb, 0)))
    tt = TTGlyphPen(None)
    shifted.draw(Cu2QuPen(tt, max_err=0.6, reverse_direction=True))
    return tt.glyph()


def num(v):
    return int(v) if float(v).is_integer() else v


def geometry(src):
    """glifler.json content: every glyph's primitives, for the web scenes that redraw the letters."""
    def clean(i):
        if i["t"] == "p":
            return {"t": "p", "noktalar": [[num(x), num(y)] for x, y in i["noktalar"]]}
        return {k: (v if k == "t" else num(v)) for k, v in i.items()}
    return {
        "surum": VERSION, "birim": UPM, "cizgi": S, "buyuk": H, "x": XH,
        "harita": {chr(cp): name for cp, name in CMAP.items()},
        "glifler": {name: {"genislik": round(gl.width + gl.lsb + gl.rsb), "sol": gl.lsb,
                           "ilkeller": [clean(i) for i in gl.ilkeller]}
                    for name, gl in src.items()},
    }


def build(out_dir):
    src = glyphs()
    order = [".notdef"] + list(src)
    glyf, metrics = {}, {}
    notdef = Glyph(500).bar(0, 0, 500, H)
    notdef.poly([(S, S), (500 - S, S), (500 - S, H - S), (S, H - S)][::-1])
    for name, gl in [(".notdef", notdef)] + list(src.items()):
        glyf[name] = ttglyph(gl)
        metrics[name] = (round(gl.width + gl.lsb + gl.rsb), gl.lsb)

    fb = FontBuilder(UPM, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(CMAP)
    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ASC, descent=DESC)
    fb.setupNameTable({"familyName": FAMILY, "styleName": "Regular", "fullName": FAMILY,
                       "psName": "CouncilHalka-Regular", "version": "Version " + VERSION})
    fb.setupOS2(sTypoAscender=ASC, sTypoDescender=DESC, sTypoLineGap=0, usWinAscent=ASC,
                usWinDescent=-DESC, sCapHeight=H, sxHeight=XH, usWeightClass=500)
    fb.setupPost()
    addOpenTypeFeaturesFromString(fb.font, kern_feature())
    out = pathlib.Path(out_dir)
    fb.font.save(out / "CouncilHalka.ttf")
    fb.font.flavor = "woff2"
    fb.font.save(out / "CouncilHalka.woff2")
    (out / "glifler.json").write_text(
        json.dumps(geometry(src), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return len(order)


if __name__ == "__main__":
    print("glyphs:", build(pathlib.Path(__file__).parent))

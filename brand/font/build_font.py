"""COUNCIL Halka: the COUNCIL display typeface, built from the logo's rules.

Every glyph is made of three primitives: straight bars, ring segments cut from
perfect circles, and slanted bars. One stroke weight, flat cut ends.

Run:  python build_font.py   (needs fonttools, skia-pathops, brotli)
Writes CouncilHalka.ttf and CouncilHalka.woff2 next to this file.
"""
import math
import pathlib

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from pathops import Path

FAMILY = "Council Halka"
VERSION = "0.1"
UPM = 1000
H = 700          # cap height
S = 100          # stroke weight
ASC, DESC = 960, -260


class Glyph:
    def __init__(self, width, lsb=55, rsb=55):
        self.width, self.lsb, self.rsb = width, lsb, rsb
        self.path = Path()
        self.pen = self.path.getPen()

    def bar(self, x, y, w, h):
        p = self.pen
        p.moveTo((x, y)); p.lineTo((x, y + h)); p.lineTo((x + w, y + h)); p.lineTo((x + w, y)); p.closePath()
        return self

    def poly(self, pts):
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
    return g


CMAP = {
    **{ord(c): c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    **{ord(c.lower()): c for c in "ABCDEFGHJKLMNOPQRSTUVWXYZ"},
    ord("i"): "Idotaccent", ord("ı"): "I", ord("İ"): "Idotaccent",
    ord("Ç"): "Ccedilla", ord("ç"): "Ccedilla", ord("Ş"): "Scedilla", ord("ş"): "Scedilla",
    ord("Ğ"): "Gbreve", ord("ğ"): "Gbreve", ord("Ö"): "Odieresis", ord("ö"): "Odieresis",
    ord("Ü"): "Udieresis", ord("ü"): "Udieresis",
    **{ord(str(i)): n for i, n in enumerate(
        ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"])},
    ord(" "): "space", ord("."): "period", ord(","): "comma", ord(":"): "colon",
    ord("-"): "hyphen", ord("·"): "periodcentered", ord("!"): "exclam", ord("/"): "slash",
    ord("?"): "question",
}


def build(out_dir):
    src = glyphs()
    order = [".notdef"] + list(src)
    glyf, metrics = {}, {}
    notdef = Glyph(500).bar(0, 0, 500, H)
    notdef.poly([(S, S), (500 - S, S), (500 - S, H - S), (S, H - S)][::-1])
    for name, gl in [(".notdef", notdef)] + list(src.items()):
        path = Path()
        gl.path.draw(path.getPen())
        path.simplify(fix_winding=True)
        shifted = Path()
        from fontTools.pens.transformPen import TransformPen
        path.draw(TransformPen(shifted.getPen(), (1, 0, 0, 1, gl.lsb, 0)))
        tt = TTGlyphPen(None)
        shifted.draw(Cu2QuPen(tt, max_err=0.6, reverse_direction=True))
        glyf[name] = tt.glyph()
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
                usWinDescent=-DESC, sCapHeight=H, sxHeight=H, usWeightClass=500)
    fb.setupPost()
    out = pathlib.Path(out_dir)
    fb.font.save(out / "CouncilHalka.ttf")
    fb.font.flavor = "woff2"
    fb.font.save(out / "CouncilHalka.woff2")
    return len(order)


if __name__ == "__main__":
    print("glyphs:", build(pathlib.Path(__file__).parent))

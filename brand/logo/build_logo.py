"""Writes the COUNCIL logo set as SVG, with the wordmark as outlines.

Run after brand/font/build_font.py:  python build_logo.py   (needs fonttools)
"""
import pathlib
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from amblem import WAVE, amblem_svg  # noqa: E402

HERE = pathlib.Path(__file__).parent
FONT = HERE.parent / "font" / "CouncilHalka.ttf"

INK, PAPER, KOR = "#111416", "#F4F5F3", "#E8421F"
SCALE = 0.28        # font units to logo units: stroke 100 becomes 28, same as the emblem
TRACK = 60          # extra advance between letters, font units
GAP = 70            # space between emblem box and wordmark, logo units


def emblem(ink, accent, uid):
    return amblem_svg("hafiza", ink, accent, uid)


def wordmark(text="COUNCIL"):
    font = TTFont(FONT)
    glyphs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    x, parts = 0, []
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        parts.append(f'<path transform="translate({x} 0)" d="{pen.getCommands()}"/>')
        x += hmtx[name][0] + TRACK
    return "".join(parts), x - TRACK


def svg(width, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 400" role="img" aria-label="{label}">'
            f'{body}</svg>\n')


def main(out=HERE):
    letters, advance = wordmark()
    total = round(400 + GAP + advance * SCALE + 18)
    for suffix, ink, accent in (("", INK, KOR), ("-koyu", PAPER, KOR), ("-tek-renk", INK, INK)):
        (out / f"council-amblem{suffix}.svg").write_text(svg(400, emblem(ink, accent, "kesik"), "COUNCIL"))
        word = (f'<g fill="{ink}" transform="translate({400 + GAP} 298) scale({SCALE} -{SCALE})">{letters}</g>')
        (out / f"council-logo{suffix}.svg").write_text(svg(total, emblem(ink, accent, "kesik") + word, "COUNCIL"))
    for suffix, ink, accent in (("", INK, KOR), ("-koyu", PAPER, KOR)):
        (out / f"council-amblem-kasa{suffix}.svg").write_text(svg(400, amblem_svg("kasa", ink, accent, "kesik"), "COUNCIL Kasa"))
    favicon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="14 14 372 372">'
        f'<style>.i{{stroke:{INK}}}@media (prefers-color-scheme:dark){{.i{{stroke:{PAPER}}}}}</style>'
        '<defs><mask id="kesik" maskUnits="userSpaceOnUse" x="0" y="0" width="400" height="400">'
        '<rect width="400" height="400" fill="#fff"/>'
        f'<path transform="translate(200 200)" d="{WAVE}" fill="none" stroke="#000" stroke-width="48"/></mask></defs>'
        '<g fill="none" stroke-width="28">'
        f'<circle cx="200" cy="200" r="112" stroke="{KOR}" mask="url(#kesik)"/>'
        '<path class="i" transform="translate(200 200) rotate(45)" d="M168 0A168 168 0 1 1 0 -168"/>'
        f'<path class="i" transform="translate(200 200)" d="{WAVE}"/></g></svg>\n'
    )
    (out / "favicon.svg").write_text(favicon)
    print("logo width:", total)


if __name__ == "__main__":
    main()

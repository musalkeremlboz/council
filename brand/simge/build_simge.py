"""Icon set: 24-unit grid, stroke 2, butt caps. Primitives are lines and ring arcs only."""
import importlib.util
import math
import pathlib

BURASI = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("amblem", BURASI.parent / "logo" / "amblem.py")
amblem = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(amblem)

BASLIK = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="2" stroke-linecap="butt" stroke-linejoin="miter" aria-hidden="true">')


def L(x1, y1, x2, y2):
    return {"t": "cizgi", "x1": x1, "y1": y1, "x2": x2, "y2": y2}


def A(cx, cy, r, a0=0, a1=360):
    """Ring arc, degrees clockwise from the +x axis (y points down)."""
    return {"t": "yay", "cx": cx, "cy": cy, "r": r, "a0": a0, "a1": a1}


def kutu(x0, y0, x1, y1):
    """Rectangle outline; horizontals overhang by 1 so butt caps close the corners."""
    return [L(x0 - 1, y0, x1 + 1, y0), L(x0 - 1, y1, x1 + 1, y1), L(x0, y0, x0, y1), L(x1, y0, x1, y1)]


def ok(x1, y1, x2, y2, kol=6):
    """Arrow: shaft plus two 45-degree head bars (axis-aligned shaft only)."""
    dx, dy = (x2 > x1) - (x2 < x1), (y2 > y1) - (y2 < y1)
    bx, by = x2 - dx * kol, y2 - dy * kol
    if dx:
        bars = [L(bx, y2 - kol, x2, y2), L(bx, y2 + kol, x2, y2)]
    else:
        bars = [L(x2 - kol, by, x2, y2), L(x2 + kol, by, x2, y2)]
    return [L(x1, y1, x2, y2)] + bars


SIMGELER = {
    "menu": [L(4, 6, 20, 6), L(4, 12, 20, 12), L(4, 18, 20, 18)],
    "kapat": [L(5, 5, 19, 19), L(19, 5, 5, 19)],
    "ara": [A(10, 10, 6), L(14.5, 14.5, 20, 20)],
    "ayarlar": [L(3, 7, 9, 7), A(12, 7, 3), L(15, 7, 21, 7), L(3, 17, 6, 17), A(9, 17, 3), L(12, 17, 21, 17)],
    "telefon": kutu(7, 3, 17, 21) + [L(10, 18, 14, 18)],
    "bilgisayar": kutu(3, 4, 21, 16) + [L(12, 16, 12, 20), L(8, 20, 16, 20)],
    "sunucu": kutu(4, 3, 20, 10) + kutu(4, 14, 20, 21) + [L(7, 6.5, 9, 6.5), L(7, 17.5, 9, 17.5)],
    "not": kutu(5, 3, 19, 21) + [L(9, 9, 15, 9), L(9, 13, 15, 13), L(9, 17, 13, 17)],
    "gecmis": [A(12, 12, 8, -140, 170), L(2.5, 9, 8, 9), L(5, 4, 5, 9), L(12, 7, 12, 12), L(12, 12, 16, 12)],
    "baglanti": [A(7, 12, 4, 90, 270), L(7, 8, 11, 8), L(7, 16, 11, 16),
                 A(17, 12, 4, 270, 450), L(13, 8, 17, 8), L(13, 16, 17, 16), L(9, 12, 15, 12)],
    "indir": ok(12, 3, 12, 16) + [L(4, 20, 20, 20)],
    "kopyala": kutu(9, 8, 20, 21) + [L(4, 3, 4, 17), L(3, 3, 14, 3), L(3, 17, 8, 17)],
    "uyari": [L(12, 3, 22, 20), L(12, 3, 2, 20), L(1, 20, 23, 20), L(12, 9, 12, 14), L(12, 16.5, 12, 18)],
    "bilgi": [A(12, 12, 9), L(12, 11, 12, 17), L(12, 7, 12, 8.5)],
    "onay": [L(4, 12, 9, 17), L(9, 17, 20, 6)],
    "ekle": [L(12, 4, 12, 20), L(4, 12, 20, 12)],
    "sil": [L(3, 6, 21, 6), L(9, 3, 15, 3)] + kutu(6, 9, 18, 21)[1:] + [L(10, 12, 10, 18), L(14, 12, 14, 18)],
    "duzenle": [L(8, 16, 16, 8), L(12, 20, 20, 12), L(16, 8, 20, 12), L(8, 16, 4, 20), L(4, 20, 12, 20)],
    "disari": [L(12, 12, 20, 4), L(14, 4, 21, 4), L(20, 4, 20, 11),
               L(3, 6, 10, 6), L(4, 6, 4, 20), L(3, 20, 18, 20), L(18, 14, 18, 20)],
    "geri": ok(20, 12, 4, 12),
    "ileri": ok(4, 12, 20, 12),
    "yukari": ok(12, 20, 12, 4),
    "asagi": ok(12, 4, 12, 20),
    "anahtar": [A(7, 12, 4), L(11, 12, 21, 12), L(17, 12, 17, 16), L(21, 11, 21, 15)],
    "ogrenme": kutu(3, 5, 21, 19) + [L(12, 5, 12, 19), L(6, 9, 9, 9), L(15, 9, 18, 9)],
    "yardimci": kutu(3, 4, 21, 16) + [L(7, 17, 7, 21), L(7, 21, 11, 17), L(8, 10, 16, 10)],
    "takvim": kutu(3, 5, 21, 21) + [L(3, 10, 21, 10), L(8, 2, 8, 7), L(16, 2, 16, 7)],
    "paylas": [A(6, 12, 3), A(18, 6, 3), A(18, 18, 3), L(8.6, 10.5, 15.4, 7.5), L(8.6, 13.5, 15.4, 16.5)],
}
# The two marker icons come straight from the emblem family (the Kasa marker is the vault lock).
MARKA = {"hafiza": "hafiza", "kilit": "kasa"}
for _ad in MARKA:
    SIMGELER[_ad] = []


def _s(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def _oge(p):
    if p["t"] == "cizgi":
        return f'<line x1="{_s(p["x1"])}" y1="{_s(p["y1"])}" x2="{_s(p["x2"])}" y2="{_s(p["y2"])}"/>'
    cx, cy, r = p["cx"], p["cy"], p["r"]
    if p["a1"] - p["a0"] >= 360:
        return f'<circle cx="{_s(cx)}" cy="{_s(cy)}" r="{_s(r)}"/>'
    nokta = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = nokta(p["a0"]), nokta(p["a1"])
    buyuk = 1 if p["a1"] - p["a0"] > 180 else 0
    return f'<path d="M{_s(x0)} {_s(y0)}A{_s(r)} {_s(r)} 0 {buyuk} 1 {_s(x1)} {_s(y1)}"/>'


def svg(ad):
    if ad in MARKA:
        return amblem.isaret_simgesi(MARKA[ad]) + "\n"
    return BASLIK + "".join(_oge(p) for p in SIMGELER[ad]) + "</svg>\n"


def yaz(hedef):
    hedef = pathlib.Path(hedef)
    hedef.mkdir(parents=True, exist_ok=True)
    yollar = []
    for ad in SIMGELER:
        yol = hedef / f"{ad}.svg"
        yol.write_text(svg(ad))
        yollar.append(yol)
    return yollar


if __name__ == "__main__":
    yaz(BURASI)

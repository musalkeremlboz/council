"""Headless checks of a page with Chrome (default: the living example page): horizontal overflow and screenshots.
The page opts in to measuring with brand/js/denetim.js (?denetim=1).

    python brand/denetle.py <output folder> [--sayfa PATH ...]
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ORNEK = Path(__file__).resolve().parent / "ornek" / "index.html"
MAC_CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# ES modules and fetch from file:// need this in headless Chrome.
ASGARI = 500   # narrowest window headless Chrome opens
ORTAK = ["--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files"]


def chrome_yolu() -> str | None:
    if Path(MAC_CHROME).exists():
        return MAC_CHROME
    for ad in ("google-chrome", "chromium"):
        yol = shutil.which(ad)
        if yol:
            return yol
    return None


def _calistir(args: list[str], profil: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [chrome_yolu(), *ORTAK, f"--user-data-dir={profil}", *args],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
    )


def _sarmal(adres: str, genislik: int, yukseklik: int, klasor: Path, kaydir: int = 0) -> str:
    """Headless Chrome's window is never narrower than 500px, so a narrower layout is shown in an iframe of that width.
    It also scrolls the page by `kaydir` px (a tall window repeats its tiles in screenshots).
    The wrapper copies the page's data-tasma, so dump-dom reads it the same way."""
    yol = klasor / "sarmal.html"
    yol.write_text(
        '<!doctype html><meta charset="utf-8"><style>body{margin:0}iframe{border:0;display:block}</style>'
        f'<iframe id="f" width="{genislik}" height="{yukseklik}" src="{adres}"></iframe>'
        f'<script>f.onload=()=>f.contentWindow.scrollTo(0,{kaydir});'
        'setInterval(()=>{try{const d=f.contentDocument.documentElement.dataset;'
        'if(d.tasma){document.documentElement.dataset.tasma=d.tasma;document.documentElement.dataset.yukseklik=d.yukseklik;document.documentElement.dataset.sahney=d.sahney}}catch(e){}},100)</script>', encoding="utf-8")
    return yol.as_uri()


def _olc(sayfa: Path, genislik: int) -> dict[str, str]:
    adres = f"{sayfa.resolve().as_uri()}?denetim=1"
    with tempfile.TemporaryDirectory() as profil, tempfile.TemporaryDirectory() as gecici:
        if genislik < ASGARI:
            adres = _sarmal(adres, genislik, 900, Path(gecici))
        r = _calistir([f"--window-size={max(genislik, ASGARI)},900", "--virtual-time-budget=4000", "--dump-dom", adres],
                      Path(profil))
    olcum = dict(re.findall(r'data-(tasma|yukseklik|sahney|kurulum|ayni)="([\w-]+)"', r.stdout))
    if "tasma" not in olcum:
        raise RuntimeError(f"data-tasma not found (exit {r.returncode}): {r.stderr[-400:]}")
    return olcum


def tasma_var_mi(sayfa: Path, genislik: int) -> bool:
    return _olc(sayfa, genislik)["tasma"] == "true"


def kimlik_ani(sayfa: Path, genislik: int = 1280) -> tuple[str, bool]:
    """The order the logo parts started building in (e.g. "kor-c-yazi-isaret", "yok" if nothing was built)
    and whether every [data-yazi-kur] element ended with its source markup."""
    olcum = _olc(sayfa, genislik)
    return olcum.get("kurulum", ""), olcum.get("ayni") == "true"


def ekran_goruntusu(sayfa: Path, cikti: Path, genislik: int, tema: str, azalt: bool, js: bool,
                    yukseklik: int = 900, kaydir: int = 0) -> Path:
    """tema: "light" or "dark" (follows prefers-color-scheme); kaydir: scroll offset in px."""
    args = [f"--window-size={max(genislik, ASGARI)},{yukseklik}",
            f"--blink-settings=preferredColorScheme={0 if tema == 'dark' else 1}"]
    if js:
        args.append("--virtual-time-budget=4000")
    if azalt:
        args.append("--force-prefers-reduced-motion")
    cikti.parent.mkdir(parents=True, exist_ok=True)
    kopya = None
    if not js:
        # Headless Chrome writes no screenshot with scriptEnabled=false and ignores --disable-javascript,
        # so the no-JS view is a copy of the page without its scripts, next to the original (relative links hold).
        kopya = sayfa.with_name(f".{sayfa.stem}-jssiz.html")
        kopya.write_text(re.sub(r"<script\b.*?</script>", "", sayfa.read_text(encoding="utf-8"), flags=re.S), encoding="utf-8")
        sayfa = kopya
    try:
        with tempfile.TemporaryDirectory() as profil, tempfile.TemporaryDirectory() as gecici:
            adres = sayfa.resolve().as_uri()
            if genislik < ASGARI or kaydir:
                adres = _sarmal(adres, genislik, yukseklik, Path(gecici), kaydir)
            r = _calistir([*args, f"--screenshot={cikti}", adres], Path(profil))
    finally:
        if kopya:
            kopya.unlink(missing_ok=True)
    if not cikti.exists():
        raise RuntimeError(f"no screenshot written: {r.stderr[-400:]}")
    return cikti


def png_yap(svg: Path, png: Path, genislik: int, yukseklik: int) -> Path:
    """Headless Chrome screenshot of an SVG file at exactly genislik x yukseklik (Chrome's 500px minimum window
    width is worked around by the same iframe wrapper the page checks use)."""
    png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as profil, tempfile.TemporaryDirectory() as gecici:
        sayfa = Path(gecici) / "svg.html"
        sayfa.write_text(
            '<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:transparent}'
            f'img{{display:block;width:{genislik}px;height:{yukseklik}px}}</style>'
            f'<img src="{svg.resolve().as_uri()}" alt="">', encoding="utf-8")
        r = _calistir([f"--window-size={genislik},{yukseklik}", "--default-background-color=00000000",
                       f"--screenshot={png}", sayfa.as_uri()], Path(profil))
    if not png.exists():
        raise RuntimeError(f"no screenshot written: {r.stderr[-400:]}")
    return png


def _argumanlar(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="denetle.py", description="Headless Chrome checks of a page.")
    ap.add_argument("klasor", type=Path, help="output folder for the screenshots")
    ap.add_argument("--sayfa", type=Path, action="append", help="page to check (repeatable); default: the example page")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if chrome_yolu() is None:
        print("Chrome not found", file=sys.stderr)
        return 1
    arg = _argumanlar(argv)
    klasor = arg.klasor.expanduser()
    for sayfa in arg.sayfa or [ORNEK]:
        on = "" if sayfa == ORNEK else f"{sayfa.resolve().parent.name}-"
        for genislik in (375, 1280):
            for tema in ("light", "dark"):
                print(ekran_goruntusu(sayfa, klasor / f"{on}{genislik}-{tema}.png", genislik, tema, False, True))
            # The static variants: the top of the page, then 900px slices from the scenes down, so the scene frames show up.
            olcum = _olc(sayfa, genislik)
            kaydirmalar = [0, *range(int(olcum["sahney"]), int(olcum["yukseklik"]), 900)]
            for ad, azalt, js in (("azaltilmis", True, True), ("jssiz", False, False)):
                for no, y in enumerate(kaydirmalar):
                    print(ekran_goruntusu(sayfa, klasor / f"{on}{genislik}-{ad}-{no}.png", genislik, "light", azalt, js, 900, y))
            print("tasma", genislik, tasma_var_mi(sayfa, genislik))
    return 0


if __name__ == "__main__":
    sys.exit(main())

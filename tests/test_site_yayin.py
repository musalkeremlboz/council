"""site/yayinla.sh and site/dogrula.sh: local-target publish, pruning, dirty-tree refusal, page checks."""
import functools
import http.server
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

KOK = Path(__file__).resolve().parent.parent
SITE = KOK / "site"


def _git(depo: Path, *arg: str) -> None:
    subprocess.run(["git", "-C", str(depo), *arg], check=True, capture_output=True)


@pytest.fixture()
def depo(tmp_path: Path) -> Path:
    """A throwaway git repo holding a copy of yayinla.sh and a tiny site/cikti/."""
    d = tmp_path / "depo"
    (d / "site" / "cikti").mkdir(parents=True)
    shutil.copy(SITE / "yayinla.sh", d / "site" / "yayinla.sh")
    (d / "site" / "cikti" / "index.html").write_text("<p>ana</p>")
    _git(d, "init", "-q")
    _git(d, "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
    _git(d, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "x")
    return d


def _yayinla(depo: Path, hedef: Path, **ortam: str) -> subprocess.CompletedProcess:
    env = {**os.environ, **ortam}
    return subprocess.run(["sh", str(depo / "site" / "yayinla.sh"), str(hedef)],
                          capture_output=True, text=True, env=env)


def test_iki_yayin_iki_surum_guncel_en_yeniyi_gosterir(depo, tmp_path):
    hedef = tmp_path / "hedef"
    hedef.mkdir()
    assert _yayinla(depo, hedef, SURUM="a1").returncode == 0
    assert _yayinla(depo, hedef, SURUM="b2").returncode == 0
    assert sorted(p.name for p in (hedef / "surumler").iterdir()) == ["a1", "b2"]
    assert (hedef / "guncel").is_symlink()
    assert os.readlink(hedef / "guncel") == "surumler/b2"
    assert (hedef / "guncel" / "index.html").read_text() == "<p>ana</p>"


def test_dort_yayindan_sonra_yalniz_uc_surum_kalir(depo, tmp_path):
    hedef = tmp_path / "hedef"
    hedef.mkdir()
    for ad in ("s1", "s2", "s3", "s4"):
        assert _yayinla(depo, hedef, SURUM=ad).returncode == 0
    kalan = sorted(p.name for p in (hedef / "surumler").iterdir())
    assert kalan == ["s2", "s3", "s4"]
    assert os.readlink(hedef / "guncel") == "surumler/s4"


def test_kirli_site_klasoru_reddedilir(depo, tmp_path):
    hedef = tmp_path / "hedef"
    hedef.mkdir()
    (depo / "site" / "cikti" / "index.html").write_text("<p>degisti</p>")
    sonuc = _yayinla(depo, hedef, SURUM="k1")
    assert sonuc.returncode != 0
    assert not (hedef / "surumler").exists()
    assert not (hedef / "guncel").exists()


def test_hedef_verilmezse_hata(depo):
    sonuc = subprocess.run(["sh", str(depo / "site" / "yayinla.sh")], capture_output=True, text=True)
    assert sonuc.returncode != 0


@pytest.fixture()
def sunucu():
    isleyici = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE / "cikti"))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), isleyici)
    isleyici.func.log_message = lambda *a, **k: None
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def test_dogrula_sayfalar_gecer(sunucu):
    sonuc = subprocess.run(["sh", str(SITE / "dogrula.sh"), sunucu], capture_output=True, text=True,
                           env={**os.environ, "DOGRULA_SAYFALAR_YALNIZ": "1"})
    assert sonuc.returncode == 0, sonuc.stdout + sonuc.stderr
    assert len(sonuc.stdout.strip().splitlines()) == 5


def test_dogrula_eksik_sayfada_basarisiz(sunucu):
    """Without the page-only switch the service routes do not exist on a plain file server."""
    sonuc = subprocess.run(["sh", str(SITE / "dogrula.sh"), sunucu], capture_output=True, text=True)
    assert sonuc.returncode != 0
    assert "FAIL" in sonuc.stdout

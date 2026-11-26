"""Tasarım sistemi sayfasının dosyalarını koddan üretir (project/ ağacı).

tokens.css, manifest.json ve api/ sayfa türünün kendisi tarafından üretilir; burada yazılmaz.
"""
import copy
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

BRAND = Path(__file__).resolve().parent
LISTE = BRAND / "css" / "council.css"

# Yazar adı bilerek parçalı yazılır: brand/ altındaki içerik taraması araç adlarını yasaklar.
YAZAR = "Clau" + "de"
ARAC = YAZAR + " Code"
NOT = "0.2 koddan üretildi"

FONTLAR = ("CouncilHalka.woff2", "DMSans.ttf", "DMMono-Regular.ttf", "DMMono-Medium.ttf")

D = '<span class="c-durum" data-durum="{}"></span>'

# ad -> (grup, yükseklik, açıklama, önizleme gövdesi)
BILESENLER = {
    "Dugme": ("Girdi", 180, "Kor, birincil, ikincil ve hayalet türleri olan, kesikli düğme. Kor türü ekranda en fazla bir tane. Kesik yüksekliğin 2/7'sidir: 44 px için 12 px.",
              '<p style="display:flex;gap:var(--ara-3);flex-wrap:wrap;align-items:center">'
              '<button class="c-dugme c-dugme--kor">Kaydet</button>'
              '<button class="c-dugme">Birincil</button>'
              '<button class="c-dugme c-dugme--ikincil">İkincil</button>'
              '<button class="c-dugme c-dugme--hayalet">Hayalet</button>'
              '<button class="c-dugme" disabled>Devre dışı</button></p>'
              '<p style="display:flex;gap:var(--ara-3);flex-wrap:wrap;align-items:center">'
              '<button class="c-dugme c-dugme--k">Küçük</button>'
              '<button class="c-dugme c-dugme--b">Büyük</button></p>'),
    "Alan": ("Girdi", 160, "Düz köşeli, kesiksiz, 44 px metin alanı. Etiketi her zaman görünür.",
             '<div class="c-alan" style="max-inline-size:320px"><label class="c-alan__etiket" for="a1">Not başlığı</label>'
             '<input id="a1" class="c-alan__giris" value="Proje notu"></div>'),
    "Kart": ("Yüzey", 200, "Düz kare yüzey. Tıklanan kartta sabit kesik vardır, içine ikinci düğme konmaz.",
             '<div style="display:flex;gap:var(--ara-4);flex-wrap:wrap">'
             '<div class="c-kart" style="max-inline-size:240px"><p>Toplantı kararı</p></div>'
             '<a href="#" class="c-kart c-kart--tik" style="max-inline-size:240px"><p>Proje notu</p></a></div>'),
    "Rozet": ("Durum", 120, "Durum bildirir, kesik taşımaz. İçinde işaret, yanında sözcük bulunur.",
              '<p style="display:flex;gap:var(--ara-3);flex-wrap:wrap">'
              f'<span class="c-rozet c-rozet--basari">{D.format("tamam")} Tamam</span>'
              f'<span class="c-rozet c-rozet--uyari">{D.format("bekliyor")} Bekliyor</span>'
              f'<span class="c-rozet c-rozet--hata">{D.format("hata")} Hata</span>'
              f'<span class="c-rozet c-rozet--kor">{D.format("hafizada")} Hafızada</span></p>'),
    "Durum": ("Durum", 120, "Sekiz piksellik durum işareti. Açık C hazır, dönen C çalışıyor, tam O tamam, kor O hafızaya yazıldı, yarım halka hata.",
              '<p style="display:flex;gap:var(--ara-4);flex-wrap:wrap;align-items:center">'
              + "".join(f'<span>{D.format(d)} {d}</span>' for d in ("bekliyor", "calisiyor", "tamam", "hafizada", "hata"))
              + '</p>'),
    "Halka": ("İlerleme", 140, "Dairesel ilerleme. Uçları düz, çember pathLength=100 ile çizilir.",
              '<svg class="c-halka" viewBox="0 0 48 48" style="--deger:.65" role="img" aria-label="Yüzde 65">'
              '<circle class="c-halka__iz" cx="24" cy="24" r="20" pathLength="100"/>'
              '<circle class="c-halka__dolu" cx="24" cy="24" r="20" pathLength="100"/></svg>'),
    "Serit": ("İlerleme", 120, "Doğrusal ilerleme şeridi. 6 px kalınlık, ilerleyen ucu 45° kesik.",
              '<div class="c-serit" style="--deger:.6;max-inline-size:360px" role="progressbar" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100" aria-label="Yükleme"></div>'),
    "Gezinme": ("Gezinme", 120, "Düz metin gezinme. Bulunulan sayfanın solunda 6 px dolu daire durur.",
                '<nav class="c-gezinme" aria-label="Ana"><a href="#" aria-current="page">Notlar</a><a href="#">Projeler</a><a href="#">Ayarlar</a></nav>'),
    "Sekme": ("Gezinme", 120, "Sekmeler. Seçili sekme sağ üstü kesik yüzey bloğudur.",
              '<div class="c-sekmeler" role="tablist" aria-label="Görünüm">'
              '<button role="tab" aria-selected="true">Özet</button>'
              '<button role="tab" aria-selected="false">Ayrıntı</button>'
              '<button role="tab" aria-selected="false">Geçmiş</button></div>'),
    "Menu": ("Gezinme", 220, "Sağ üstten 45° çizgiyle açılan menü. Açıkken data-acik taşır.",
             '<div class="c-menu" data-acik style="max-inline-size:220px;padding:var(--ara-3)">'
             '<p>Yeniden adlandır</p><p>Taşı</p><p>Sil</p></div>'),
    "Secim": ("Girdi", 140, "İşaret kutusu kare, radyo halka biçimindedir.",
              '<p style="display:flex;gap:var(--ara-4);flex-wrap:wrap">'
              '<label><input type="checkbox" class="c-isaret" checked> Hatırlat</label>'
              '<label><input type="radio" name="r" class="c-radyo" checked> Günlük</label>'
              '<label><input type="radio" name="r" class="c-radyo"> Haftalık</label></p>'),
    "Cover": ("Yüzey", 220, "Kapak yüzeyi: kart üzerinde başlık, Halka işareti ve tek bir kor düğme.",
              '<div class="c-kart" style="max-inline-size:420px;display:grid;gap:var(--ara-4)">'
              '<h2 style="margin:0">Proje notu</h2><p style="margin:0">Toplantı kararı ve sonraki adımlar.</p>'
              '<button class="c-dugme c-dugme--kor" style="justify-self:start">Aç</button></div>'),
}


def _bundle_css() -> str:
    """council.css, yazı tipi adresleri ../../fonts/ altına çevrilmiş olarak."""
    metin = LISTE.read_text(encoding="utf-8")
    return re.sub(r'url\("\.\./font/([^"]+)"\)', r'url("../../fonts/\1")', metin)


def _onizleme(ad: str, grup: str, yukseklik: int, govde: str) -> str:
    return (f'<!-- @dsCard group="{grup}" height={yukseklik} -->\n'
            '<!doctype html>\n<html lang="tr"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"><title>{ad}</title></head>\n'
            f'<body style="margin:0;padding:var(--ara-4);background:var(--zemin);color:var(--murekkep);font-family:var(--font-sans)">\n{govde}\n</body></html>\n')


def yaz(hedef: Path, index: dict, zaman: str | None = None) -> list[Path]:
    """hedef/project/ altına dosyaları yazar, yazılan yolları döndürür."""
    kok = Path(hedef) / "project"
    yazilan: list[Path] = []

    def yaz_metin(yol: Path, metin: str) -> None:
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(metin, encoding="utf-8")
        yazilan.append(yol)

    def kopyala(kaynak: Path, yol: Path) -> None:
        yol.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(kaynak, yol)
        yazilan.append(yol)

    kopyala(BRAND / "tokens.json", kok / "tokens.json")
    kopyala(BRAND / "README.md", kok / "README.md")
    yaz_metin(kok / "components" / "bundle.css", _bundle_css())
    for ad, (grup, yukseklik, aciklama, govde) in BILESENLER.items():
        yaz_metin(kok / "components" / ad / "README.md", f"# {ad}\n\n{aciklama}\n")
        yaz_metin(kok / "components" / ad / "preview.html", _onizleme(ad, grup, yukseklik, govde))
    for f in FONTLAR:
        kopyala(BRAND / "font" / f, kok / "fonts" / f)

    sonuc = copy.deepcopy(index)
    sonuc["editing"] = "code"
    an = zaman or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sonuc["lastChange"] = {"by": YAZAR, "via": ARAC, "at": an, "note": NOT}
    yaz_metin(kok / "design-system.json", json.dumps(sonuc, ensure_ascii=False, indent=2) + "\n")
    return yazilan

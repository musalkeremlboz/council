// Sayfa denetim kancası: yalnız ?denetim=1 ile çalışır, sonuçları <html> üzerine data-* olarak yazar.
// data-tasma (yatay taşma), data-yukseklik, data-sahney, data-kurulum (logo parçalarının kurulum sırası),
// data-ayni (kimlik anı sonunda kaynak işaretleme geri geldi mi), data-gizli (<main> içinde yazı taşıyıp
// visibility:hidden ya da opacity:0 olan, yani yerini tutup görünmeyen öğe sayısı; azaltılmış harekette ve betiksiz 0 olmalı).
// display:none sayılmaz. Kurul turu karelerinin çizimi (.s-tur__gorsel) sayılmaz: her kare yalnız kendi adımını
// gösterir, öteki adımların yazıları o karede bilerek görünmez; kare metinleri (paneller) sayılır.
const CIZIM = ".s-tur__gorsel";
const yaziVar = (e) => [...e.childNodes].some((n) => n.nodeType === 3 && n.nodeValue.trim() !== "");

export function gizliSay(doc = document) {
  const pencere = doc.defaultView;
  const gizli = (e) => {
    if (pencere.getComputedStyle(e).visibility === "hidden") return true;
    for (let o = e; o && o !== doc.body; o = o.parentElement) if (pencere.getComputedStyle(o).opacity === "0") return true;
    return false;
  };
  return [...doc.querySelectorAll("main *")].filter((e) => yaziVar(e) && e.checkVisibility() && !e.closest(CIZIM) && gizli(e)).length;
}

export function denetimKur(doc = document) {
  const pencere = doc.defaultView;
  if (new URLSearchParams(pencere.location.search).get("denetim") !== "1") return;
  const kok = doc.documentElement;
  const kaynak = pencere.fetch(pencere.location.href.split("?")[0]).then((r) => r.text())
    .then((t) => new pencere.DOMParser().parseFromString(t, "text/html"));
  const logo = doc.querySelector("[data-denetim-logo]");
  const baslangic = new Map();
  if (logo) {
    new pencere.MutationObserver(() => {
      for (const p of logo.querySelectorAll(".s-ciz")) {
        const rol = p.closest("[data-kur]")?.dataset.kur, d = Number(p.style.getPropertyValue("--d"));
        if (rol) baslangic.set(rol, Math.min(d, baslangic.get(rol) ?? Infinity));
      }
    }).observe(logo, { subtree: true, childList: true, attributes: true });
  }
  pencere.addEventListener("load", () => {
    const olc = () => {
      kok.dataset.tasma = String(kok.scrollWidth > pencere.innerWidth);
      kok.dataset.yukseklik = String(kok.scrollHeight);
      kok.dataset.gizli = String(gizliSay(doc));
      kok.dataset.sahney = String(doc.querySelector("[data-denetim-sahne]")?.offsetTop ?? 0);
    };
    (doc.fonts ? doc.fonts.ready : Promise.resolve()).then(() => setTimeout(olc, 600));
    setTimeout(async () => {   // kimlik anı en fazla 1,8 sn sürer
      const asil = [...(await kaynak).querySelectorAll("[data-yazi-kur]")];
      kok.dataset.kurulum = [...baslangic].sort((a, b) => a[1] - b[1]).map(([rol]) => rol).join("-") || "yok";
      kok.dataset.ayni = String([...doc.querySelectorAll("[data-yazi-kur]")].every((e, i) => e.innerHTML === asil[i]?.innerHTML));
    }, 2400);
  });
}

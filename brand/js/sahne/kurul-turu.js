// Kurul turu (sahne, "Nasıl çalışır"). Kaydırma sahnenin zamanıdır: ziyaretçi durunca sahne de durur.
// C altı parçaya (6 × 45°) ayrılır; her parça COUNCIL'in bir temel özelliğidir ve bugünkü durumu
// ozellikler.json'dan okunur. Kor yalnız ortadaki O'dadır; taşınan not zemin renginde bir kesiktir.
// Hareket azaltılmışsa altı duran kare; JS yoksa duran amblem ve altı açıklama alt alta.
//
// İşaretleme:
//   <section class="s-tur" aria-label="…"><div class="s-tur__sahne">
//     <figure class="s-tur__gorsel"><svg class="s-tur__svg" viewBox="-120 -70 640 540" role="img" aria-label="…">duran amblem</svg></figure>
//     <div class="s-tur__metin"><div class="s-tur__paneller"><article class="s-tur__panel">…</article> × 6</div></div>
//   </div></section>
//   Sonraki öğe "Hikâyeyi atla" bağlantısının hedefidir.

import { hareketAzaltildi, azaltmaIzle, yaklas, cizimDongusu, gorunurlukBekcisi, kokuIsaretle } from "./ortak.js";

const NS = "http://www.w3.org/2000/svg";
const DALGA = "M-56 0A56 56 0 0 1 56 0A56 56 0 0 0 168 0";   // iki yarım daire, merkezden C'nin ağzına
const L = 2 * Math.PI * 56, D = 30, BIT_YOL = L - D - 64;    // dalganın boyu, taşınan kesiğin boyu, yolu
const VB = [-120, -70, 640, 540];                             // görüş alanı sabit: yakınlaşma yok
const SINIRLAR = [0.10, 0.27, 0.47, 0.64, 0.82];
const KARELER = [0.05, 0.26, 0.46, 0.63, 0.80, 1];           // duran kareler
const CIZGILER = [1.1, 0.45, 0.5, 0.45, 1.6, 0.45, 0.8, 0.45]; // henüz yazılmamış adın çizgileri (yazı boyu cinsinden)

const kis = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const sm = (a, b, p) => { const t = kis((p - a) / (b - a)); return t * t * (3 - 2 * t); };
const rad = (a) => a * Math.PI / 180;
const f = (v) => Math.round(v * 100) / 100;
const nk = (r, a) => [f(200 + r * Math.cos(rad(a))), f(200 + r * Math.sin(rad(a)))];
const M = (r, a) => `M${nk(r, a).join(" ")}`;
const yay = (r, a, yon) => `A${r} ${r} 0 0 ${yon} ${nk(r, a).join(" ")}`;

export const bolumBul = (p) => SINIRLAR.filter((s) => p >= s).length;
export const koltukAcilari = (i) => [45 + 45 * i, 90 + 45 * i];
// Etiket yazısı hiç sönükleşmez (4.5:1): yalnız girer ve kapanıştaki dolumdan önce çekilir.
export const etiketOpak = (i, p) => sm(0.13 + 0.01 * i, 0.18 + 0.01 * i, p) * (1 - sm(0.83, 0.86, p));

// Parçanın doluluğu. Bugünkü hâl: tamam dolu, denemede yarı, yolda boş. Son bölümde altısı sırayla dolar:
// bu bir gelecek önizlemesidir ("henüz değil").
export function doluluk(o, i, p) {
  if (o.durum === "tamam") return 1;
  const v = o.durum === "denemede" ? 0.5 : 0;
  return v + (1 - v) * sm(0.86 + 0.012 * i, 0.90 + 0.012 * i, p);
}

// DOM'a yalnız değişen değer yazılır.
function yaz(e, k, v) {
  const s = e.__s || (e.__s = {});
  if (s[k] === v) return;
  s[k] = v;
  if (v === null) e.removeAttribute(k); else e.setAttribute(k, v);
}
function oge(ad, at, ust) {
  const e = document.createElementNS(NS, ad);
  for (const k in at) e.setAttribute(k, at[k]);
  return ust.appendChild(e);
}
const div = (sinif, ust) => { const e = document.createElement("div"); e.className = sinif; return ust ? ust.appendChild(e) : e; };

function kayitKur(oz) {
  const say = (d) => oz.filter((o) => o.durum === d).length;
  const satirlar = [
    [[0.37, 0.47, "telefon → hafıza · “toplantı kararı” · yazıldı"], [0.58, 0.64, "yardımcı öğrendi → beceri kaydedildi"],
      [0.68, 0.82, `${say("yolda")} özellik yolda · adları henüz yazılmadı`], [0.86, 1.01, `altısı dolduğunda → sürüm 1.0.0`]],
    [[0.44, 0.47, "hafıza → bilgisayar · okundu"], [0.61, 0.64, "tek satır haber · istersen geri alınır"],
      [0.74, 0.82, "testi ve ölçümü geçen eklenir"], [0.92, 1.01, `henüz değil · bugün ${say("tamam")} dolu, ${say("denemede")} denemede`]],
  ];
  const el = div("s-tur__kayit");
  el.setAttribute("aria-hidden", "true");
  const liste = [];
  for (const satir of satirlar) {
    const s = div("s-tur__satir", el);
    for (const [a, b, metin] of satir) {
      const sp = s.appendChild(document.createElement("span"));
      sp.textContent = metin;
      liste.push({ el: sp, a, b });
    }
  }
  return { el, liste };
}

let sayac = 0;
// Bir SVG'ye sahneyi kurar; { olc, ciz(p) } döndürür.
function sahne(svg, oz, kayit) {
  const id = `tur-kesik-${++sayac}`;
  svg.replaceChildren();
  svg.setAttribute("viewBox", VB.join(" "));
  const maske = oge("mask", { id, maskUnits: "userSpaceOnUse", x: -200, y: -200, width: 800, height: 800 }, oge("defs", {}, svg));
  oge("rect", { x: -200, y: -200, width: 800, height: 800, fill: "white" }, maske);
  const mDalga = oge("path", { d: DALGA, fill: "none", stroke: "black", "stroke-width": 48 }, maske);
  const g = oge("g", { fill: "none", "stroke-width": 28 }, svg);
  oge("circle", { cx: 200, cy: 200, r: 112, class: "s-kor", mask: `url(#${id})` }, g);
  const c = oge("path", { class: "s-mur", transform: "translate(200 200) rotate(45)", d: "M168 0A168 168 0 1 1 0 -168" }, g);
  const cer = oz.map(() => oge("path", { class: "s-tur__cer" }, g));
  const kol = oz.map(() => oge("path", { class: "s-mur" }, g));
  const dalga = oge("path", { class: "s-mur", d: DALGA }, g);
  const bit = oge("path", { class: "s-tur__bit", d: DALGA, "stroke-width": 32, "stroke-dasharray": `${D} ${f(L)}` }, g);
  const lg = oge("g", { class: "s-tur__etiketler", "dominant-baseline": "middle" }, svg);
  const etiket = oz.map((o) => {
    const grp = oge("g", { opacity: 0 }, lg);
    const ad = oge(o.ad ? "text" : "path", o.ad ? {} : { class: "s-tur__yer" }, grp);   // ad yoksa yerinde çizgiler
    if (o.ad) ad.textContent = o.ad;
    const st = oge("text", { class: "s-tur__ikincil" }, grp);
    st.textContent = o.durum;
    return { grp, ad, st };
  });
  const kapi = oge("text", { class: "s-tur__ikincil", "text-anchor": "start", opacity: 0 }, lg);
  kapi.textContent = "cihazlar";

  let w = VB[2], h = VB[3], px = 13, fs = -1, ara = -1;

  // Etiket yerleri yalnız yazı boyuna bağlı: boyut değişince bir kez hesaplanır.
  const yerlestir = () => {
    yaz(lg, "font-size", fs);
    const lh = 1.3 * fs;
    etiket.forEach((lb, i) => {
      const [a0, a1] = koltukAcilari(i), a = (a0 + a1) / 2, co = Math.cos(rad(a)), si = Math.sin(rad(a));
      const [x, y] = nk(190 + fs * (0.45 + 0.6 * Math.abs(si)), a);
      const yon = co > 0.25 ? "start" : co < -0.25 ? "end" : "middle";
      const y1 = si >= 0 ? y : y - lh, y2 = si >= 0 ? y + lh : y;   // ad ve durum halkadan dışarı doğru
      if (lb.ad.tagName === "path") {
        const W = 5.4 * fs, x0 = yon === "start" ? x : yon === "end" ? x - W : x - W / 2;
        yaz(lb.ad, "d", `M${f(x0)} ${f(y1 + 0.05 * fs)}h${f(W)}`);
        yaz(lb.ad, "stroke-width", f(0.36 * fs));
        yaz(lb.ad, "stroke-dasharray", CIZGILER.map((v) => f(v * fs)).join(" "));
      } else {
        yaz(lb.ad, "x", x); yaz(lb.ad, "y", f(y1)); yaz(lb.ad, "text-anchor", yon);
      }
      yaz(lb.st, "x", x); yaz(lb.st, "y", f(y2)); yaz(lb.st, "text-anchor", yon);
    });
    const [kx, ky] = nk(190 + fs * 0.45, 0);
    yaz(kapi, "x", kx); yaz(kapi, "y", ky);
  };

  const olc = () => {
    const r = svg.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) { w = r.width; h = r.height; }
    px = innerWidth < 761 ? 12 : 13;
  };

  const ciz = (p) => {
    const yeni = f(px / Math.min(w / VB[2], h / VB[3]));
    if (yeni !== fs) { fs = yeni; yerlestir(); }

    // C'de ince yarıklar açılır; yollar yalnız aralık değişince yazılır.
    const z = sm(0.10, 0.16, p) - sm(0.92, 0.97, p), yeniAra = f(4 * z), acik = yeniAra >= 0.04;
    if (yeniAra !== ara) {
      ara = yeniAra;
      yaz(c, "display", acik ? "none" : null);
      kol.forEach((s, i) => {
        const [k0, k1] = koltukAcilari(i), a0 = k0 + ara / 2, a1 = k1 - ara / 2, d = 0.55;
        if (acik) {
          yaz(s, "d", M(168, a0) + yay(168, a1, 1));
          // boş parçanın çerçevesi dolu hâlinin (r 154–182) içinde kalır, dolunca altında kaybolur
          yaz(cer[i], "d", M(180.5, a0 + d) + yay(180.5, a1 - d, 1) + "L" + nk(155.5, a1 - d).join(" ") + yay(155.5, a0 + d, 0) + "Z");
          s.uz = 168 * rad(a1 - a0);
        }
        yaz(s, "display", acik ? null : "none");
      });
    }

    // Dalga bir tam tur atar: ağız → denemedeki parça → yoldaki parçaların üstünden → ağız.
    const th = 125 * sm(0.48, 0.54, p) + 167.5 * sm(0.65, 0.78, p) + 67.5 * sm(0.83, 0.90, p);
    const tr = `translate(200 200) rotate(${f(th)})`;
    for (const e of [dalga, mDalga, bit]) yaz(e, "transform", tr);

    // Sırası gelen özellik öne çıkar, ötekilerin parçaları geri çekilir.
    const one = {
      tamam: sm(0.28, 0.31, p) - sm(0.46, 0.49, p),
      denemede: sm(0.47, 0.50, p) - sm(0.63, 0.66, p),
      yolda: sm(0.64, 0.67, p) - sm(0.81, 0.84, p),
    };
    const sonuk = kis(one.tamam + one.denemede + one.yolda);
    const kipir = fs * (p * 20 + 9 * sm(0.64, 0.82, p));   // çizgiler yalnız kaydırınca kıpırdar
    oz.forEach((o, i) => {
      const op = f(1 - 0.55 * sonuk * (1 - (one[o.durum] || 0)));
      const dl = 1 - sm(0.16 + 0.008 * i, 0.21 + 0.008 * i, p) * (1 - doluluk(o, i, p));   // bölünen C bugüne boşalır
      if (acik) {
        yaz(kol[i], "opacity", op);
        yaz(kol[i], "stroke-dasharray", dl > 0.999 ? null : `${f(kol[i].uz * dl)} ${f(kol[i].uz + 40)}`);
        yaz(cer[i], "display", dl > 0.999 ? "none" : null);
        yaz(cer[i], "opacity", f(op * kis((1 - dl) * 6)));
      } else {
        yaz(cer[i], "display", "none");
      }
      const lb = etiket[i];
      yaz(lb.grp, "opacity", f(etiketOpak(i, p)));
      if (lb.ad.tagName === "path") yaz(lb.ad, "stroke-dashoffset", f(-(kipir + i * 1.7 * fs)));
    });
    yaz(kapi, "opacity", f(one.tamam));

    // Taşınan not: dalga boyunca kayan tek bir kesik (yazma, okuma, öğrenilenin kaydı).
    let bs = -1, bt = 0;
    if (p >= 0.31 && p <= 0.38) { bt = sm(0.31, 0.38, p); bs = BIT_YOL * (1 - bt); }
    else if (p >= 0.39 && p <= 0.45) { bt = sm(0.39, 0.45, p); bs = BIT_YOL * bt; }
    else if (p >= 0.54 && p <= 0.59) { bt = sm(0.54, 0.59, p); bs = BIT_YOL * bt; }
    yaz(bit, "display", bs < 0 ? "none" : null);
    if (bs >= 0) { yaz(bit, "stroke-dashoffset", f(-bs)); yaz(bit, "opacity", f(Math.min(1, bt * 6, (1 - bt) * 6))); }

    for (const k of kayit) {
      const on = p >= k.a && p < k.b;
      if (k.el.classList.contains("s-acik") !== on) k.el.classList.toggle("s-acik", on);
    }
  };

  return { olc, ciz };
}

// "Hikâyeyi atla": bölümden sonraki öğeye gider.
function atlaKur(bolum) {
  const hedef = bolum.nextElementSibling || bolum.parentElement?.nextElementSibling;
  if (!hedef) return null;
  if (!hedef.id) hedef.id = `${bolum.id || "kurul-turu"}-sonrasi`;
  if (!hedef.hasAttribute("tabindex")) hedef.tabIndex = -1;
  const a = document.createElement("a");
  a.className = "s-tur__atla c-baglanti";
  a.href = `#${hedef.id}`;
  a.textContent = "Hikâyeyi atla";
  bolum.prepend(a);
  return a;
}

function canli(bolum, oz) {
  const svg = bolum.querySelector(".s-tur__svg");
  const duran = [...svg.childNodes], vb = svg.getAttribute("viewBox");
  const paneller = [...bolum.querySelectorAll(".s-tur__panel")];
  const kayit = kayitKur(oz);
  svg.after(kayit.el);
  const adimlar = document.createElement("ol");
  adimlar.className = "s-tur__adimlar";
  adimlar.setAttribute("aria-hidden", "true");
  adimlar.innerHTML = paneller.map(() => '<li><svg viewBox="0 0 20 20"><path class="s-tur__c" d="M14.95 14.95A7 7 0 1 1 14.95 5.05"/>' +
    '<circle class="s-tur__o" cx="10" cy="10" r="7"/></svg></li>').join("");   // açık C bekliyor, tam O bitti
  paneller[0]?.parentElement.before(adimlar);
  const atla = atlaKur(bolum);
  bolum.classList.add("s-canli");
  const sc = sahne(svg, oz, kayit.liste);

  const goster = (k) => {
    paneller.forEach((e, i) => e.classList.toggle("s-etkin", i === k));
    [...adimlar.children].forEach((li, i) => { li.className = i < k ? "s-gecmis" : i === k ? "s-simdi" : ""; });
  };
  let cur = 0, cizilen = -1, bolumNo = -1, ilk = true, toplam = 1;
  const dongu = cizimDongusu(() => {
    const hedef = kis(-bolum.getBoundingClientRect().top / toplam);   // kare başına tek ölçüm
    cur = ilk ? hedef : yaklas(cur, hedef, 0.2, 0.0008);
    ilk = false;
    if (cur !== cizilen) {
      sc.ciz(cur);
      cizilen = cur;
      const k = bolumBul(cur);
      if (k !== bolumNo) { goster(k); bolumNo = k; }
    }
    return cur !== hedef;   // yalnız yetişene kadar
  });
  const tetik = () => dongu.baslat();
  const boyut = () => { toplam = Math.max(1, bolum.offsetHeight - innerHeight); sc.olc(); cizilen = -1; dongu.baslat(); };
  const birak = gorunurlukBekcisi(bolum, {
    gir: () => { addEventListener("scroll", tetik, { passive: true }); addEventListener("resize", boyut, { passive: true }); boyut(); },
    cik: () => { removeEventListener("scroll", tetik); removeEventListener("resize", boyut); dongu.durdur(); },
  });
  sc.ciz(0);
  goster(0);

  return () => {
    birak();
    removeEventListener("scroll", tetik);
    removeEventListener("resize", boyut);
    dongu.durdur();
    bolum.classList.remove("s-canli");
    paneller.forEach((e) => e.classList.remove("s-etkin"));
    kayit.el.remove();
    adimlar.remove();
    atla?.remove();
    svg.replaceChildren(...duran);
    if (vb) svg.setAttribute("viewBox", vb);
  };
}

// Hareket azaltılmış: aynı sahne, altı anahtar anda, alt alta.
function durgun(bolum, oz) {
  const paneller = [...bolum.querySelectorAll(".s-tur__panel")];
  const liste = div("s-tur__kareler");
  const kareler = KARELER.map((p, k) => {
    const kare = div("s-tur__kare", liste);
    const fig = kare.appendChild(document.createElement("figure"));
    fig.className = "s-tur__gorsel";
    const svg = oge("svg", { class: "s-tur__svg", role: "img", "aria-label": `Kurul turu, adım ${k + 1} / ${KARELER.length}` }, fig);
    const kayit = kayitKur(oz);
    fig.append(kayit.el);
    if (paneller[k]) kare.append(paneller[k].cloneNode(true));
    return { sc: sahne(svg, oz, kayit.liste), p };
  });
  bolum.classList.add("s-durgun");
  bolum.append(liste);
  const ciz = () => kareler.forEach(({ sc, p }) => { sc.olc(); sc.ciz(p); });
  ciz();
  let no = 0;
  const boyut = () => { if (!no) no = requestAnimationFrame(() => { no = 0; ciz(); }); };
  addEventListener("resize", boyut, { passive: true });
  return () => {
    removeEventListener("resize", boyut);
    cancelAnimationFrame(no);
    liste.remove();
    bolum.classList.remove("s-durgun");
  };
}

// Sahneyi kurar; hareket tercihi sayfa açıkken değişirse hemen öteki hâline geçer. Temizleyici döndürür.
export function baslat(bolum, ozellikler) {
  kokuIsaretle(bolum.ownerDocument);
  let birak = () => {};
  const kur = (az) => { birak(); birak = (az ? durgun : canli)(bolum, ozellikler); };
  kur(hareketAzaltildi());
  const birakAz = azaltmaIzle(kur);
  return () => { birakAz(); birak(); };
}

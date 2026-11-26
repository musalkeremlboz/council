// Kendini kuran yazı (kimlik anı). Harfler Council Halka'nın kendi ilkellerinden (glifler.json) kurulur:
// çubuklar uzar, yaylar tam dairelerinden kesilerek çizilir, eğik çubuklar en son yerine oturur.
// Oturum başına bir kez, yalnız açılışta. Kurulum bitince öğenin asıl içeriği geri konur: son görüntü
// yazı tipinin (ve logonun asıl SVG'sinin) kendisidir. JS yoksa ya da hareket azaltılmışsa hiçbir şey gizlenmez.
//
// İşaretleme:
//   <h1 data-yazi-kur data-glifler="../font/glifler.json">Birçok üye, tek hafıza</h1>
//   <div data-yazi-kur><svg …>                  logo ya da amblem; parçalar bu sırayla kurulur:
//     <circle data-kur="kor" …/>                 kor O
//     <path data-kur="c" …/>                     C
//     <path data-kur="isaret" …/>                dalga; maskedeki kopyası da data-kur="isaret" taşır.
//                                                Kasa'nın anahtar deliği burada çizgi olarak verilir
//                                                (daire r 17, kalınlık 34; gövde x 200, 182→258, kalınlık 28).
//     <g data-kur="yazi" data-metin="COUNCIL" data-ara="60" transform="… scale(k -k)">…</g>   logo yazısı
//   </svg></div>
// Başlık logodan sonra başlar (data-gecikme ile değiştirilebilir).

import { hareketAzaltildi, azaltmaIzle, kokuIsaretle } from "./ortak.js";

// ms. Başlık en geç `okunur` anında tamamdır; kimlik anı `en` sınırını geçmez. Glifler sayfa açıldıktan
// `gec` ms sonra hâlâ gelmemişse kurulum yapılmaz: ziyaretçinin okumaya başladığı başlık silinmez.
export const SURE = { ciz: 420, harf: 40, ilke: 60, yazi: 420, okunur: 1200, en: 1800, gec: 400 };
const PARCA = { kor: 0, c: 120, isaret: 300 };   // önce kor O, sonra C, en son dalga
const LOGO_YAZI = 160;
const UST = 960, ALT = -260;                       // yazı tipinin çıkış ve inişi (build_font.py ASC, DESC)
const SIRA = { b: 0, r: 1, p: 2 };                 // kurulum sırası: çubuklar, halkalar, eğik çubuklar
const ANAHTAR = "council-kuruldu";
let uid = 0;

const n = (v) => Math.round(v * 10) / 10;
const rad = (a) => a * Math.PI / 180;

// Bir glifin ilkelleri → kendi orta çizgisi boyunca düz uçlu çizgiler. ox: glifin ilerleme kutusunun solu.
// y çevrilir: yazı tipinde y yukarı, SVG'de aşağı (H = büyük harf boyu, y=H üst çizgi olur).
export function glifYollari(glif, ox, H = 700) {
  const x0 = ox + glif.sol;
  const P = (x, y) => `${n(x0 + x)} ${n(H - y)}`;
  return glif.ilkeller
    .map((pr, i) => [pr, i])
    .sort((a, b) => SIRA[a[0].t] - SIRA[b[0].t] || a[1] - b[1])
    .map(([pr], sira) => ({ sira, ...yol(pr, P, H) }));
}

function yol(pr, P, H) {
  if (pr.t === "b") {
    const dik = pr.h >= pr.w;
    const [a, b] = dik
      ? [[pr.x + pr.w / 2, pr.y], [pr.x + pr.w / 2, pr.y + pr.h]]
      : [[pr.x, pr.y + pr.h / 2], [pr.x + pr.w, pr.y + pr.h / 2]];
    return { t: "b", d: `M${P(...a)}L${P(...b)}`, uzunluk: n(dik ? pr.h : pr.w), kalinlik: n(dik ? pr.w : pr.h) };
  }
  if (pr.t === "r") {
    const rc = pr.r - pr.s / 2;
    const [a0, a1] = pr.a1 - pr.a0 >= 360 ? [90, 450] : [pr.a0, pr.a1];   // tam halka tepeden başlar
    const parca = Math.ceil((a1 - a0) / 120);
    const nokta = (a) => P(pr.cx + rc * Math.cos(rad(a)), pr.cy + rc * Math.sin(rad(a)));
    let d = "M" + nokta(a0);
    for (let k = 1; k <= parca; k++) d += `A${n(rc)} ${n(rc)} 0 0 0 ${nokta(a0 + (a1 - a0) * k / parca)}`;
    return { t: "r", d, uzunluk: n(rc * rad(a1 - a0)), kalinlik: pr.s };
  }
  // Eğik çubuk: ekseni boyunca ilerleyen geniş çizgi, glifin kendi dörtgeniyle kırpılır;
  // yatay uç kesikleri böylece yerine oturur.
  const q = pr.noktalar;
  const orta = (u, v) => [(u[0] + v[0]) / 2, (u[1] + v[1]) / 2];
  let a = orta(q[0], q[1]), b = orta(q[2], q[3]);
  const da = Math.abs(a[1] - H / 2), db = Math.abs(b[1] - H / 2);
  // harfin ortasına yakın uçtan başla (K'nın kolları gövdeden dışarı uzar); eşitse yukarıdan
  if (db < da - 1 || (Math.abs(db - da) <= 1 && b[1] > a[1])) [a, b] = [b, a];
  const L = Math.hypot(b[0] - a[0], b[1] - a[1]), ux = (b[0] - a[0]) / L, uy = (b[1] - a[1]) / L;
  let mn = Infinity, mx = -Infinity, en = 0;
  for (const [x, y] of q) {
    const dx = x - a[0], dy = y - a[1], pj = dx * ux + dy * uy;
    mn = Math.min(mn, pj); mx = Math.max(mx, pj); en = Math.max(en, Math.abs(dy * ux - dx * uy));
  }
  const u0 = mn - 4, u1 = mx + 4;
  return {
    t: "p",
    d: `M${P(a[0] + ux * u0, a[1] + uy * u0)}L${P(a[0] + ux * u1, a[1] + uy * u1)}`,
    uzunluk: n(u1 - u0),
    kalinlik: n(2 * en + 8),
    kirp: q.map(([x, y]) => P(x, y).replace(" ", ",")).join(" "),
  };
}

// Her harfin her ilkesinin başlama anı (ms). Harfler sırayla, ilkeler kısa aralıklarla;
// uzun başlıkta aralıklar daralır, son çizgi `okunur` anında biter.
export function zamanla(ilkeller, gecikme = 0) {
  const kalan = Math.max(0, SURE.okunur - SURE.ciz - gecikme);
  const enCok = Math.max(1, ...ilkeller) - 1;
  const ilke = Math.min(SURE.ilke, kalan / 2 / Math.max(1, enCok));
  const harf = Math.min(SURE.harf, (kalan - enCok * ilke) / Math.max(1, ilkeller.length - 1));
  return ilkeller.map((k, i) => Array.from({ length: k }, (_, j) => Math.floor(gecikme + i * harf + j * ilke)));
}

const kesikler = (u, d, s) => `stroke-dasharray="${u} ${n(u + 2)}" style="--u:${u};--d:${d};--s:${s}"`;

const planla = (glifler, gecikme) => zamanla(glifler.map((g) => g.ilkeller.length), gecikme);

// Harf dizisini çizgilere çevirir: { ic, en (genişlik), son (ms) }. z: zamanla()'nın bu harflere düşen kısmı.
function dizi(glifler, veri, ara, z) {
  let x = 0, ic = "", tanim = "", son = 0;
  glifler.forEach((g, i) => {
    for (const y of glifYollari(g, x, veri.buyuk)) {
      const d = z[i][y.sira];
      let kirp = "";
      if (y.kirp) {
        const id = `yk${++uid}`;
        tanim += `<clipPath id="${id}"><polygon points="${y.kirp}"/></clipPath>`;
        kirp = ` clip-path="url(#${id})"`;
      }
      ic += `<path class="s-ciz" d="${y.d}" stroke-width="${y.kalinlik}"${kirp} ${kesikler(y.uzunluk, d, SURE.ciz)}/>`;
      son = Math.max(son, d + SURE.ciz);
    }
    x += g.genislik + (i < glifler.length - 1 ? ara : 0);
  });
  return { ic: (tanim ? `<defs>${tanim}</defs>` : "") + ic, en: x, son };
}

const glifi = (veri) => (ch) => veri.glifler[veri.harita[ch]] || veri.glifler.question;
const kacir = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function yaziyiKur(el, veri, gecikme) {
  const asil = el.textContent.replace(/\s+/g, " ").trim();
  if (!asil) return -1;
  const cs = getComputedStyle(el);
  const metin = cs.textTransform === "uppercase" ? asil.toLocaleUpperCase(el.closest("[lang]")?.lang || "tr") : asil;
  const fs = parseFloat(cs.fontSize), B = veri.birim;
  const ara = (parseFloat(cs.letterSpacing) || 0) / fs * B;
  const lh = parseFloat(cs.lineHeight) / fs || (UST - ALT) / B;
  const boy = lh * B, ust = veri.buyuk - UST - (boy - (UST - ALT)) / 2;   // satır kutusu yazı tipininkiyle aynı
  const kelimeler = metin.split(" ").map((k) => Array.from(k).map(glifi(veri)));
  const z = planla(kelimeler.flat(), gecikme);   // zaman bütün başlık için birlikte planlanır
  let i = 0, son = 0;
  const svgler = kelimeler.map((g) => {
    const r = dizi(g, veri, ara, z.slice(i, i += g.length));
    son = Math.max(son, r.son);
    return `<svg viewBox="0 ${n(ust)} ${n(r.en)} ${n(boy)}" style="width:${(r.en / B).toFixed(3)}em;height:${lh.toFixed(3)}em"` +
      ` fill="none" stroke="currentColor" focusable="false">${r.ic}</svg>`;
  });
  const bosluk = (veri.glifler.space.genislik + 2 * ara) / B;
  const yasla = { center: "center", right: "flex-end", end: "flex-end" }[cs.textAlign] || "flex-start";
  el.innerHTML = `<span class="s-gizli">${kacir(asil)}</span><span class="s-yazi" aria-hidden="true"` +
    ` style="column-gap:${bosluk.toFixed(3)}em;justify-content:${yasla}">${svgler.join("")}</span>`;
  return son;
}

export function amblemiKur(svg, veri, gecikme) {
  let son = 0;
  for (const p of svg.querySelectorAll("[data-kur]")) {
    const rol = p.dataset.kur;
    if (rol === "yazi") {
      const ara = Number(p.dataset.ara ?? 60);
      const g = Array.from(p.dataset.metin || "").map(glifi(veri));
      const r = dizi(g, veri, ara, planla(g, gecikme + LOGO_YAZI));
      const renk = getComputedStyle(p).fill;
      // grubun kendi dönüşümü yazı tipi koordinatında (y yukarı): çizgiler geri çevrilerek içine konur
      p.innerHTML = `<g transform="matrix(1 0 0 -1 0 ${veri.buyuk})" fill="none" stroke="${renk}">${r.ic}</g>`;
      son = Math.max(son, r.son);
    } else if (rol in PARCA && p.getTotalLength) {
      const d = gecikme + PARCA[rol];
      const u = n(p.getTotalLength());
      p.classList.add("s-ciz");
      p.setAttribute("stroke-dasharray", `${u} ${n(u + 2)}`);
      p.setAttribute("style", `--u:${u};--d:${d};--s:${SURE.ciz}`);
      son = Math.max(son, d + SURE.ciz);
    }
  }
  return son;
}

// Öğeyi kurar; bitince asıl içeriği geri koyar. Hareket azaltma açılırsa hemen bitirir.
export function kur(el, veri, { gecikme = 0 } = {}) {
  const eski = [...el.childNodes];
  const svg = el.querySelector("svg");
  let son;
  if (svg) {
    const kopya = svg.cloneNode(true);
    svg.replaceWith(kopya);
    son = amblemiKur(kopya, veri, gecikme);
  } else {
    son = yaziyiKur(el, veri, gecikme);
  }
  if (son < 0) return Promise.resolve();
  el.classList.add("s-kurulum");
  el.getBoundingClientRect();          // gizli ilk hâli uygula, sonra kur
  el.classList.add("s-kur");
  return new Promise((bitti) => {
    let birak = () => {};
    const bitir = () => {
      clearTimeout(zaman);
      birak();
      el.classList.remove("s-kurulum", "s-kur");
      el.replaceChildren(...eski);
      bitti();
    };
    const zaman = setTimeout(bitir, son + 40);
    birak = azaltmaIzle((a) => { if (a) bitir(); });
  });
}

let yuklenen = null, yuklenenUrl = "";
function glifleriYukle(url) {
  if (yuklenenUrl !== url) {
    yuklenenUrl = url;
    yuklenen = fetch(url).then((r) => { if (!r.ok) throw new Error(String(r.status)); return r.json(); });
  }
  return yuklenen;
}

const oturum = (yaz) => {
  try {
    if (yaz) sessionStorage.setItem(ANAHTAR, "1");
    return sessionStorage.getItem(ANAHTAR) === "1";
  } catch { return false; }
};

// Sayfadaki [data-yazi-kur] öğelerini bir kez kurar. Hareket azaltılmışsa, bu oturumda zaten kurulduysa,
// glifler yüklenemezse ya da geç gelirse (saat() > sinir; saat sayfanın açılışından beri geçen ms) öğeler
// olduğu gibi (yazı tipiyle) kalır.
export async function baslat(kok = document, { sinir = SURE.gec, saat = () => performance.now() } = {}) {
  const doc = kok.ownerDocument || kok;
  kokuIsaretle(doc);
  const ogeler = [...kok.querySelectorAll("[data-yazi-kur]")];
  const url = kok.querySelector("[data-glifler]")?.getAttribute("data-glifler");
  if (!ogeler.length || !url || hareketAzaltildi() || oturum(false)) return;
  let veri;
  try { veri = await glifleriYukle(new URL(url, doc.baseURI).href); } catch { return; }
  if (hareketAzaltildi() || saat() > sinir) return;
  oturum(true);
  const logo = ogeler.some((e) => e.querySelector("svg"));
  await Promise.all(ogeler.map((e) => kur(e, veri, {
    gecikme: e.dataset.gecikme ? Number(e.dataset.gecikme) : logo && !e.querySelector("svg") ? SURE.yazi : 0,
  })));
}

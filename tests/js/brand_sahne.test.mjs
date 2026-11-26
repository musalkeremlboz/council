// The shared scene guards, run against fakes: no DOM, no timers. Run by tests/test_brand_js.py.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  hareketAzaltildi, azaltmaIzle, yaklas, cizimDongusu, gorunurlukBekcisi, kokuIsaretle,
} from "../../brand/js/sahne/ortak.js";
import { glifYollari, zamanla, SURE, baslat as yaziKur, amblemiKur } from "../../brand/js/sahne/yazi-kur.js";
import { TUR, GECIS, SOZ, amblemSvg } from "../../brand/js/sahne/cizgi-soz.js";
import { bolumBul, koltukAcilari, doluluk, etiketOpak, ozellikAdi, kayitSatirlari } from "../../brand/js/sahne/kurul-turu.js";
import { readFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const oku = (yol) => JSON.parse(readFileSync(new URL(yol, import.meta.url), "utf8"));
const GLIFLER = oku("../../brand/font/glifler.json");
const METIN = oku("../../brand/js/metin.json");
const OZELLIKLER = oku("../../brand/js/ozellikler.json");
const TURKCE = /[ğışİĞŞ]/;

function sahteMq(matches) {
  const mq = {
    matches,
    dinleyiciler: new Set(),
    addEventListener(_t, f) { this.dinleyiciler.add(f); },
    removeEventListener(_t, f) { this.dinleyiciler.delete(f); },
    degistir(v) { this.matches = v; for (const f of [...this.dinleyiciler]) f({ matches: v }); },
  };
  return mq;
}

function sahteRaf() {
  const kuyruk = new Map();
  let no = 0;
  return {
    raf(f) { kuyruk.set(++no, f); return no; },
    caf(n) { kuyruk.delete(n); },
    bekleyen: () => kuyruk.size,
    kare() { const hepsi = [...kuyruk.values()]; kuyruk.clear(); hepsi.forEach((f) => f(0)); },
  };
}

test("yaklas reaches the target exactly", () => {
  let x = 0;
  let adim = 0;
  while (x !== 10 && adim < 1000) { x = yaklas(x, 10); adim++; }
  assert.equal(x, 10);
  assert.ok(adim < 1000);
  assert.equal(yaklas(9.9995, 10), 10);
  assert.ok(yaklas(0, 10) > 0 && yaklas(0, 10) < 10);
});

test("cizimDongusu stops when adim returns false and draws zero frames afterwards", () => {
  const f = sahteRaf();
  let sayi = 0;
  const d = cizimDongusu(() => ++sayi < 3, f.raf, f.caf);
  d.baslat();
  assert.equal(d.calisiyor(), true);
  for (let i = 0; i < 10; i++) f.kare();
  assert.equal(sayi, 3);
  assert.equal(d.calisiyor(), false);
  assert.equal(f.bekleyen(), 0);
  f.kare();
  assert.equal(sayi, 3);
});

test("cizimDongusu does not double-schedule", () => {
  const f = sahteRaf();
  const d = cizimDongusu(() => true, f.raf, f.caf);
  d.baslat();
  d.baslat();
  assert.equal(f.bekleyen(), 1);
  d.durdur();
  assert.equal(f.bekleyen(), 0);
  assert.equal(d.calisiyor(), false);
});

test("azaltmaIzle reports a change made while running", () => {
  const mq = sahteMq(false);
  const goruldu = [];
  const birak = azaltmaIzle((a) => goruldu.push(a), mq);
  mq.degistir(true);
  mq.degistir(false);
  assert.deepEqual(goruldu, [true, false]);
  birak();
  mq.degistir(true);
  assert.deepEqual(goruldu, [true, false]);
});

test("hareketAzaltildi reads the current preference", () => {
  const onceki = globalThis.matchMedia;
  globalThis.matchMedia = () => ({ matches: true });
  assert.equal(hareketAzaltildi(), true);
  globalThis.matchMedia = () => ({ matches: false });
  assert.equal(hareketAzaltildi(), false);
  globalThis.matchMedia = onceki;
});

test("gorunurlukBekcisi calls cik on visibilitychange to hidden and gir on return while intersecting", () => {
  let io;
  class SahteIO {
    constructor(cb) { this.cb = cb; this.kesildi = false; io = this; }
    observe() {}
    disconnect() { this.kesildi = true; }
  }
  const doc = {
    visibilityState: "visible",
    d: new Set(),
    addEventListener(_t, f) { this.d.add(f); },
    removeEventListener(_t, f) { this.d.delete(f); },
    degistir(v) { this.visibilityState = v; [...this.d].forEach((f) => f()); },
  };
  const olay = [];
  const birak = gorunurlukBekcisi({}, { gir: () => olay.push("gir"), cik: () => olay.push("cik") },
    { IntersectionObserver: SahteIO, document: doc });
  io.cb([{ isIntersecting: true }]);
  assert.deepEqual(olay, ["gir"]);
  doc.degistir("hidden");
  assert.deepEqual(olay, ["gir", "cik"]);
  doc.degistir("visible");
  assert.deepEqual(olay, ["gir", "cik", "gir"]);
  io.cb([{ isIntersecting: false }]);
  assert.deepEqual(olay, ["gir", "cik", "gir", "cik"]);
  doc.degistir("hidden");
  doc.degistir("visible");
  assert.deepEqual(olay, ["gir", "cik", "gir", "cik"]);
  birak();
  assert.equal(io.kesildi, true);
  assert.equal(doc.d.size, 0);
});

test("kokuIsaretle adds js and removes it on the first error", () => {
  const siniflar = new Set();
  const dinleyiciler = [];
  const doc = {
    documentElement: { classList: { add: (c) => siniflar.add(c), remove: (c) => siniflar.delete(c) } },
    defaultView: { addEventListener: (t, f, o) => dinleyiciler.push({ t, f, o }) },
  };
  kokuIsaretle(doc);
  assert.ok(siniflar.has("js"));
  assert.equal(dinleyiciler[0].t, "error");
  assert.equal(dinleyiciler[0].o.once, true);
  dinleyiciler[0].f();
  assert.ok(!siniflar.has("js"));
});

test("glifYollari orders bars, rings, slanted bars", () => {
  const glif = {
    genislik: 700, sol: 0, ilkeller: [
      { t: "p", noktalar: [[0, 0], [100, 0], [400, 700], [300, 700]] },
      { t: "r", cx: 350, cy: 350, r: 350, a0: 0, a1: 180, s: 100 },
      { t: "b", x: 0, y: 0, w: 100, h: 700 },
      { t: "r", cx: 350, cy: 350, r: 200, a0: 180, a1: 360, s: 100 },
    ],
  };
  const yol = glifYollari(glif, 0);
  assert.deepEqual(yol.map((y) => y.t), ["b", "r", "r", "p"]);
  assert.deepEqual(yol.map((y) => y.sira), [0, 1, 2, 3]);
  for (const y of yol) assert.ok(y.d.startsWith("M") && y.uzunluk > 0);
  assert.ok(yol[3].kirp, "slanted bar is clipped to its own quadrilateral");
  const iki = glifYollari(GLIFLER.glifler.two, 0);
  assert.deepEqual(iki.map((y) => y.t), ["b", "r", "p"]);
});

test("glifYollari flips y (font y=700 becomes svg y=0)", () => {
  const [cubuk] = glifYollari({ genislik: 210, sol: 55, ilkeller: [{ t: "b", x: 0, y: 0, w: 100, h: 700 }] }, 10);
  assert.equal(cubuk.d, "M115 700L115 0");
  assert.equal(cubuk.uzunluk, 700);
  assert.equal(cubuk.kalinlik, 100);
  const [halka] = glifYollari(GLIFLER.glifler.O, 0);
  const uclar = [...halka.d.matchAll(/(?:M|A[-\d.]+ [-\d.]+ 0 0 [01] )(-?[\d.]+) (-?[\d.]+)/g)];
  const ys = uclar.map((m) => Number(m[2]));
  assert.equal(ys[0], 50, "the full ring starts at its top: font y=650 is svg y=50");
  assert.ok(Math.min(...ys) >= 50 - 0.1 && Math.max(...ys) <= 650 + 0.1);
  assert.ok(Math.abs(halka.uzunluk - 2 * Math.PI * 300) < 1);
});

test("zamanla builds the heading within the readable limit", () => {
  const ilkeller = Array.from({ length: 32 }, (_, i) => 1 + (i % 6));
  for (const gecikme of [0, 360]) {
    const z = zamanla(ilkeller, gecikme);
    assert.equal(z.length, 32);
    const son = Math.max(...z.flat()) + SURE.ciz;
    assert.ok(son <= SURE.okunur, `ends at ${son}`);
    assert.ok(z[0][0] === gecikme);
  }
  assert.ok(SURE.okunur <= 1200 && SURE.en <= 1800);
});

test("bolumBul boundaries", () => {
  assert.equal(bolumBul(0), 0);
  assert.equal(bolumBul(0.099), 0);
  assert.equal(bolumBul(0.10), 1);
  assert.equal(bolumBul(0.27), 2);
  assert.equal(bolumBul(0.47), 3);
  assert.equal(bolumBul(0.64), 4);
  assert.equal(bolumBul(0.82), 5);
  assert.equal(bolumBul(1), 5);
});

test("koltukAcilari covers 45..315 in six 45° parts", () => {
  const a = [0, 1, 2, 3, 4, 5].map(koltukAcilari);
  assert.deepEqual(a[0], [45, 90]);
  assert.deepEqual(a[5], [270, 315]);
  for (let i = 0; i < 6; i++) {
    assert.equal(a[i][1] - a[i][0], 45);
    if (i) assert.equal(a[i][0], a[i - 1][1]);
  }
});

test("etiketOpak: labels are never dimmed while features take turns (text stays at 4.5:1)", () => {
  for (let i = 0; i < 6; i++) {
    assert.equal(etiketOpak(i, 0), 0);
    for (let p = 0.24; p <= 0.83; p += 0.005) assert.equal(etiketOpak(i, p), 1, `i=${i} p=${p}`);
    assert.equal(etiketOpak(i, 1), 0);
  }
});

test("doluluk: tamam is always 1, denemede is 0.5 before 0.82, yolda is 0 before 0.82 and 1 at p=1", () => {
  const ps = [0, 0.05, 0.12, 0.3, 0.5, 0.7, 0.819];
  for (const p of [...ps, 0.9, 1]) assert.equal(doluluk({ durum: "tamam" }, 0, p), 1);
  for (const p of ps) {
    assert.equal(doluluk({ durum: "denemede" }, 1, p), 0.5);
    for (let i = 2; i < 6; i++) assert.equal(doluluk({ durum: "yolda" }, i, p), 0);
  }
  for (let i = 1; i < 6; i++) {
    assert.equal(doluluk({ durum: i === 1 ? "denemede" : "yolda" }, i, 1), 1);
  }
  const ara = [2, 3, 4, 5].map((i) => doluluk({ durum: "yolda" }, i, 0.89));
  for (let k = 1; k < ara.length; k++) assert.ok(ara[k] <= ara[k - 1], "fills in order");
  for (const p of [0.85, 0.9, 0.95]) {
    const v = doluluk({ durum: "yolda" }, 3, p);
    assert.ok(v >= 0 && v <= 1);
  }
});

test("TUR total ≤ 9000 ms and GECIS.duration ≤ 840", () => {
  assert.deepEqual(TUR, [{ id: "soz", bekle: 1200 }, { id: "cizgi", bekle: 6800 }]);
  assert.deepEqual(GECIS, { duration: 840, easing: "cubic-bezier(.2,0,0,1)", fill: "forwards" });
  const toplam = TUR.reduce((a, t) => a + t.bekle, 0) + GECIS.duration;
  assert.ok(toplam <= 9000, `${toplam}`);
  assert.ok(GECIS.duration <= 840);
});

test("amblemSvg: söz carries the words, the kor O is the same in both forms", () => {
  const cizgi = amblemSvg("cizgi", "a");
  const soz = amblemSvg("soz", "b");
  assert.ok(soz.includes("BİRÇOK ÜYE · TEK HAFIZA") && soz.includes("ORTAK HAFIZA"));
  assert.ok(soz.includes("<textPath"));
  assert.ok(!cizgi.includes("<text"));
  const kor = (s) => s.match(/<circle[^>]*s-kor[^>]*>/)[0].replace(/url\(#[^)]+\)/, "");
  assert.equal(kor(cizgi), kor(soz));
  assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(cizgi + soz.replace(/href="#[^"]+"|url\(#[^)]+\)/g, "")));
});

// A page with one heading to build; getComputedStyle is the first thing the build touches, so it marks "built".
function kurulacakSayfa(url) {
  const kok = {
    ownerDocument: null,
    baseURI: "http://ornek.test/",
    documentElement: { classList: { add() {}, remove() {} } },
    defaultView: { addEventListener() {} },
  };
  const baslik = { dataset: {}, textContent: "Tek hafıza", childNodes: [], querySelector: () => null, getAttribute: () => url };
  kok.querySelectorAll = () => [baslik];
  kok.querySelector = () => baslik;
  return kok;
}

async function kimlikAni(url, saat) {
  const onceki = { mm: globalThis.matchMedia, f: globalThis.fetch, gcs: globalThis.getComputedStyle };
  globalThis.matchMedia = () => sahteMq(false);
  globalThis.fetch = async () => ({ ok: true, json: async () => GLIFLER });
  globalThis.getComputedStyle = () => { throw new Error("kuruldu"); };
  try { globalThis.sessionStorage?.clear(); } catch { /* node without web storage */ }   // a fresh session each time
  try {
    await yaziKur(kurulacakSayfa(url), { saat });
    return false;
  } catch (e) {
    if (e.message !== "kuruldu") throw e;
    return true;
  } finally {
    globalThis.matchMedia = onceki.mm; globalThis.fetch = onceki.f; globalThis.getComputedStyle = onceki.gcs;
  }
}

test("the identity moment builds when the glyphs arrive early and never wipes a heading the visitor is already reading", async () => {
  assert.ok(SURE.gec + SURE.okunur <= SURE.en, "a late start still ends inside the identity limit");
  assert.equal(await kimlikAni("erken.json", () => SURE.gec - 1), true);
  assert.equal(await kimlikAni("gec.json", () => SURE.gec + 1), false);
  assert.equal(await kimlikAni("cok-gec.json", () => 2200), false);
});

function sahteParca(rol, uzunluk) {
  const attrs = {}, siniflar = new Set();
  return {
    dataset: { kur: rol }, attrs, siniflar,
    classList: { add: (c) => siniflar.add(c) },
    getTotalLength: () => uzunluk,
    setAttribute(a, v) { attrs[a] = v; },
    get d() { return Number(/--d:(\d+)/.exec(attrs.style)[1]); },
  };
}

test("amblemiKur draws the kor O first, then the C, the wave last, and the wordmark inside the limit", () => {
  const kor = sahteParca("kor", 704), c = sahteParca("c", 792), maske = sahteParca("isaret", 528), dalga = sahteParca("isaret", 528);
  const yazi = { dataset: { kur: "yazi", metin: "COUNCIL", ara: "60" }, innerHTML: "" };
  const svg = { querySelectorAll: () => [kor, c, maske, yazi, dalga] };
  const onceki = globalThis.getComputedStyle;
  globalThis.getComputedStyle = () => ({ fill: "currentColor" });
  let son;
  try { son = amblemiKur(svg, GLIFLER, 0); } finally { globalThis.getComputedStyle = onceki; }
  assert.ok(kor.d < c.d && c.d < dalga.d, `${kor.d} ${c.d} ${dalga.d}`);
  assert.equal(maske.d, dalga.d, "the cut in the kor O opens with the wave");
  for (const p of [kor, c, maske, dalga]) {
    assert.ok(p.siniflar.has("s-ciz"));
    assert.match(p.attrs["stroke-dasharray"], /^\d+(\.\d)? \d+(\.\d)?$/);
  }
  const yazilar = [...yazi.innerHTML.matchAll(/--d:(\d+)/g)].map((m) => Number(m[1]));
  assert.ok(yazilar.length >= 7, "every letter of COUNCIL is drawn");
  assert.ok(Math.min(...yazilar) > kor.d);
  assert.ok(son <= SURE.okunur, `the logo is whole by ${son} ms`);
});

// The shape of a text tree: object keys and array lengths, leaves as their type.
const bicimi = (v) => Array.isArray(v) ? v.map(bicimi)
  : v && typeof v === "object" ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, bicimi(v[k])])) : typeof v;
const yapraklar = (v) => (v && typeof v === "object" ? Object.values(v).flatMap(yapraklar) : [v]);

test("metin.json: tr and en carry the same keys, and en has no Turkish-only letters", () => {
  assert.deepEqual(Object.keys(METIN).sort(), ["en", "tr"]);
  assert.deepEqual(bicimi(METIN.en), bicimi(METIN.tr));
  for (const t of yapraklar(METIN.en)) assert.ok(!TURKCE.test(t), t);
  const { c, ci, dalga, yerlesim } = METIN.tr.cizgiSoz;
  assert.deepEqual({ c, ci, dalga, yerlesim }, SOZ, "the default words are the tr words");
});

test("amblemSvg: the words come from the language passed in", () => {
  const soz = amblemSvg("soz", "x", METIN.en.cizgiSoz);
  assert.ok(soz.includes("SHARED MEMORY") && soz.includes("MANY MEMBERS · ONE MEMORY") && soz.includes("ONE MEMORY · MANY MEMBERS"));
  assert.ok(!soz.includes("HAFIZA"));
  assert.equal(amblemSvg("soz", "cs-soz", METIN.tr.cizgiSoz), amblemSvg("soz", "cs-soz"));
  const sayfa = readFileSync(new URL("../../brand/ornek/index.html", import.meta.url), "utf8");
  assert.ok(sayfa.includes(amblemSvg("soz", "cs-soz")) && sayfa.includes(amblemSvg("cizgi", "cs-cizgi")), "the example page carries the tr forms");
  for (const k of ["etiketCizgi", "etiketSoz"]) assert.ok(sayfa.includes(`aria-label="${METIN.tr.cizgiSoz[k]}"`), k);
});

test("Kurul turu text: feature names and record lines in English", () => {
  assert.equal(ozellikAdi(OZELLIKLER[0], "en"), "Memory");
  assert.equal(ozellikAdi(OZELLIKLER[0], "tr"), "Hafıza");
  assert.equal(ozellikAdi(OZELLIKLER[2], "en"), null);
  assert.equal(ozellikAdi(OZELLIKLER[2], "tr"), null);
  const en = kayitSatirlari(OZELLIKLER, METIN.en.kurulTuru);
  assert.equal(en.length, 2);
  for (const satir of en) assert.equal(satir.length, 4);
  const metin = en.flat().join(" ");
  assert.ok(metin.includes("4"), metin);
  assert.ok(!TURKCE.test(metin), metin);
  assert.ok(!/[{}]/.test(metin), metin);
  const tr = kayitSatirlari(OZELLIKLER, METIN.tr.kurulTuru).flat().join(" ");
  assert.ok(tr.includes("4 özellik yolda") && tr.includes("bugün 1 dolu, 1 denemede"), tr);
  assert.equal(METIN.en.kurulTuru.atla, "Skip the story");
  assert.equal(METIN.tr.kurulTuru.atla, "Hikâyeyi atla");
});

test("kurul-turu.js holds no Turkish text outside comments", () => {
  const kaynak = readFileSync(new URL("../../brand/js/sahne/kurul-turu.js", import.meta.url), "utf8");
  const kod = kaynak.split("\n").map((l) => l.replace(/(^|\s)\/\/.*$/, "")).join("\n");
  assert.ok(!/[çğıöşüâÇĞİÖŞÜ]/.test(kod), kod.match(/.*[çğıöşüâÇĞİÖŞÜ].*/)?.[0]);
});

test("parca.mjs prints the two Çizgi-Söz forms of a language", () => {
  const cli = fileURLToPath(new URL("../../brand/js/parca.mjs", import.meta.url));
  for (const dil of ["tr", "en"]) {
    const { cizgiSoz } = JSON.parse(execFileSync("node", [cli, dil], { encoding: "utf8" }));
    assert.equal(cizgiSoz.soz, amblemSvg("soz", "cs-soz", METIN[dil].cizgiSoz));
    assert.equal(cizgiSoz.cizgi, amblemSvg("cizgi", "cs-cizgi", METIN[dil].cizgiSoz));
  }
  assert.throws(() => execFileSync("node", [cli, "de"], { stdio: "pipe" }));
});

// The shared scene guards, run against fakes: no DOM, no timers. Run by tests/test_brand_js.py.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  hareketAzaltildi, azaltmaIzle, yaklas, cizimDongusu, gorunurlukBekcisi, kokuIsaretle,
} from "../../brand/js/sahne/ortak.js";
import { glifYollari, zamanla, SURE } from "../../brand/js/sahne/yazi-kur.js";
import { TUR, GECIS, amblemSvg } from "../../brand/js/sahne/cizgi-soz.js";
import { bolumBul, koltukAcilari, doluluk } from "../../brand/js/sahne/kurul-turu.js";
import { readFileSync } from "node:fs";

const GLIFLER = JSON.parse(readFileSync(new URL("../../brand/font/glifler.json", import.meta.url), "utf8"));

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

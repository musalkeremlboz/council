// The shared scene guards, run against fakes: no DOM, no timers. Run by tests/test_brand_js.py.
import { test } from "node:test";
import assert from "node:assert/strict";
import {
  hareketAzaltildi, azaltmaIzle, yaklas, cizimDongusu, gorunurlukBekcisi, kokuIsaretle,
} from "../../brand/js/sahne/ortak.js";

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

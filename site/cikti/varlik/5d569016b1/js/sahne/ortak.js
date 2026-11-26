// Shared scene guards: reduced motion, eased steps, a frame loop that idles, a visibility guard, the js root class.

const AZALT = "(prefers-reduced-motion: reduce)";

export function hareketAzaltildi() {
  return matchMedia(AZALT).matches;
}

export function azaltmaIzle(cb, mq = matchMedia(AZALT)) {
  const dinle = (e) => cb(e.matches);
  mq.addEventListener("change", dinle);
  return () => mq.removeEventListener("change", dinle);
}

export function yaklas(simdiki, hedef, oran = 0.18, esik = 0.001) {
  if (Math.abs(hedef - simdiki) < esik) return hedef;
  return simdiki + (hedef - simdiki) * oran;
}

export function cizimDongusu(adim, raf = requestAnimationFrame, caf = cancelAnimationFrame) {
  let no = null;
  const kare = () => {
    no = null;
    if (adim()) no = raf(kare);
  };
  return {
    baslat() { if (no === null) no = raf(kare); },
    durdur() { if (no !== null) { caf(no); no = null; } },
    calisiyor: () => no !== null,
  };
}

export function gorunurlukBekcisi(el, { gir, cik }, deps = { IntersectionObserver, document }) {
  const doc = deps.document;
  let kesisiyor = false;
  let acik = false;
  const guncelle = () => {
    const olmali = kesisiyor && doc.visibilityState === "visible";
    if (olmali === acik) return;
    acik = olmali;
    (olmali ? gir : cik)();
  };
  const io = new deps.IntersectionObserver((kayitlar) => {
    kesisiyor = kayitlar[kayitlar.length - 1].isIntersecting;
    guncelle();
  });
  io.observe(el);
  doc.addEventListener("visibilitychange", guncelle);
  return () => {
    io.disconnect();
    doc.removeEventListener("visibilitychange", guncelle);
  };
}

export function kokuIsaretle(doc = document) {
  const kok = doc.documentElement;
  kok.classList.add("js");
  doc.defaultView.addEventListener("error", () => kok.classList.remove("js"), { once: true });
}

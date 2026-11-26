// COUNCIL site: page boot. The measuring hook (?denetim=1) starts first so it sees the identity moment build the logo;
// then the identity moment (once per session), the copy buttons and, on the home page, the two scenes after it.
// Without JS, with reduced motion or when a file does not load, the page stays as written. The page holds every text:
// a copy button carries its result labels (data-tamam, data-hata), the scenes read metin.json in the page's language.
import { denetimKur } from "./denetim.js";
import { baslat as yaziKur } from "./sahne/yazi-kur.js";

const GOSTER = 2000;   // ms a copy button shows its result

// Copies the text; false when there is no clipboard or it refuses. Never throws.
export async function kopyala(metin, pano = globalThis.navigator?.clipboard) {
  try {
    if (typeof pano?.writeText !== "function") return false;
    await pano.writeText(metin);
    return true;
  } catch {
    return false;
  }
}

// [data-kopyala="<id>"] copies that element's text. When copying fails the text is selected for the visitor to copy.
function kopyaKur(doc) {
  for (const dugme of doc.querySelectorAll("[data-kopyala]")) {
    const hedef = doc.getElementById(dugme.dataset.kopyala);
    if (!hedef) continue;
    const ilk = dugme.textContent;
    let zaman = 0;
    dugme.addEventListener("click", async () => {
      const tamam = await kopyala(hedef.textContent);
      if (!tamam) doc.getSelection()?.selectAllChildren(hedef);
      dugme.textContent = tamam ? dugme.dataset.tamam : dugme.dataset.hata;
      clearTimeout(zaman);
      zaman = setTimeout(() => { dugme.textContent = ilk; }, GOSTER);
    });
    dugme.hidden = false;
  }
}

const bosa = (p) => p.catch(() => null);
const json = (ad) => fetch(new URL(ad, import.meta.url)).then((r) => {
  if (!r.ok) throw new Error(String(r.status));
  return r.json();
});

// The home page's scenes load only where their sections are, and start once the identity moment is over.
async function sahneler(doc, kimlik) {
  const cs = doc.getElementById("cizgi-soz-bolum"), tur = doc.getElementById("kurul-turu");
  if (!cs && !tur) return;
  const [csModul, turModul, veri] = await Promise.all([
    cs && bosa(import("./sahne/cizgi-soz.js")),
    tur && bosa(import("./sahne/kurul-turu.js")),
    tur && bosa(Promise.all([json("ozellikler.json"), json("metin.json")])),
  ]);
  await bosa(kimlik);
  if (csModul) csModul.baslat(cs);
  if (turModul && veri) {
    const [ozellikler, metin] = veri;
    const dil = Object.hasOwn(metin, doc.documentElement.lang) ? doc.documentElement.lang : "tr";
    turModul.baslat(tur, ozellikler, metin[dil].kurulTuru, dil);
  }
}

if (globalThis.document) {
  denetimKur(document);
  const kimlik = yaziKur(document);
  kopyaKur(document);
  sahneler(document, kimlik);
}

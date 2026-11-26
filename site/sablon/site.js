// COUNCIL site: page boot. The measuring hook (?denetim=1) starts first so it sees the identity moment build the
// wordmark; then the identity moment (once per session), the copy buttons and, on the home page, the Kurul Masası
// (masa.js, loaded only where its canvas is). Without JS, with reduced motion or when a file does not load, the page
// stays as written. The page holds every text: a copy button carries its result labels (data-tamam, data-hata).
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

// The home page's table (canvas, seats, sections) loads only on the home page.
async function masa(doc) {
  if (!doc.getElementById("alan")) return;
  try {
    (await import("./masa.js")).baslat(doc);
  } catch {
    // The sections stay stacked and readable, as without JS.
    doc.documentElement.classList.remove("masa-js");
    for (const s of doc.querySelectorAll(".sahne")) s.hidden = false;
  }
}

if (globalThis.document) {
  denetimKur(document);
  yaziKur(document);
  kopyaKur(document);
  masa(document);
}

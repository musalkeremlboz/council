// Örnek sayfanın üç sahnesi. Ayrı dosyadır: yüklenemezse sayfanın geri kalanı (tema, sekmeler, menü) çalışmaya devam eder.
import { baslat as yaziKur } from "../js/sahne/yazi-kur.js";
import { baslat as cizgiSoz } from "../js/sahne/cizgi-soz.js";
import { baslat as kurulTuru } from "../js/sahne/kurul-turu.js";

const bolum = (id) => document.getElementById(id);

// Kimlik anı hemen başlar: glifler, özellik listesi ve sahne yazıları aynı anda yüklenir.
const kimlik = yaziKur(document);
const json = (yol) => fetch(yol).then((r) => r.json());
let veri = null;
try { veri = await Promise.all([json("../js/ozellikler.json"), json("../js/metin.json")]); } catch { /* dosya olarak açılmışsa duran hâl kalır */ }

await kimlik;
cizgiSoz(bolum("cizgi-soz-bolum"));
if (veri) kurulTuru(bolum("kurul-turu"), veri[0], veri[1].tr.kurulTuru);

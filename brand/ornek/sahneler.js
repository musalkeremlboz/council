// Örnek sayfanın üç sahnesi. Ayrı dosyadır: yüklenemezse sayfanın geri kalanı (tema, sekmeler, menü) çalışmaya devam eder.
import { baslat as yaziKur } from "../js/sahne/yazi-kur.js";
import { baslat as cizgiSoz } from "../js/sahne/cizgi-soz.js";
import { baslat as kurulTuru } from "../js/sahne/kurul-turu.js";

const bolum = (id) => document.getElementById(id);

let ozellikler = null;
try { ozellikler = await fetch("../js/ozellikler.json").then((r) => r.json()); } catch { /* dosya olarak açılmışsa duran hâl kalır */ }

await yaziKur(document);
cizgiSoz(bolum("cizgi-soz-bolum"));
if (ozellikler) kurulTuru(bolum("kurul-turu"), ozellikler);

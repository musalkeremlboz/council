// Sahnelerin durağan parçaları, sayfaya yazılmak için: node brand/js/parca.mjs <tr|en>
// Çıktı JSON: {"cizgiSoz": {"cizgi": "<svg…>", "soz": "<svg…>"}}; sözler metin.json'dan, kimlikler cs-cizgi / cs-soz.
import { readFileSync } from "node:fs";
import { amblemSvg } from "./sahne/cizgi-soz.js";

const metin = JSON.parse(readFileSync(new URL("metin.json", import.meta.url), "utf8"));
const dil = process.argv[2];
if (!Object.hasOwn(metin, dil)) {
  console.error(`kullanım: node brand/js/parca.mjs <${Object.keys(metin).join("|")}>`);
  process.exit(2);
}
const soz = metin[dil].cizgiSoz;
process.stdout.write(JSON.stringify({ cizgiSoz: { cizgi: amblemSvg("cizgi", "cs-cizgi", soz), soz: amblemSvg("soz", "cs-soz", soz) } }) + "\n");

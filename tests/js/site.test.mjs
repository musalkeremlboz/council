// site/sablon/site.js and masa.js: the copy helper (run against clipboard stubs) and the ring statuses.
// Run by tests/test_site_build.py. site.js imports its neighbours as they sit in the published asset folder
// (js/denetim.js, js/sahne/), so the test lays the files out the same way in a temporary folder and imports from there.
import { test } from "node:test";
import assert from "node:assert/strict";
import { cpSync, mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const kok = fileURLToPath(new URL("../../", import.meta.url));
const js = join(mkdtempSync(join(tmpdir(), "site-js-")), "js");
mkdirSync(join(js, "sahne"), { recursive: true });
for (const ad of ["ortak.js", "yazi-kur.js"]) cpSync(join(kok, "brand/js/sahne", ad), join(js, "sahne", ad));
cpSync(join(kok, "brand/js/denetim.js"), join(js, "denetim.js"));
cpSync(join(kok, "site/sablon/site.js"), join(js, "site.js"));
cpSync(join(kok, "site/sablon/masa.js"), join(js, "masa.js"));
writeFileSync(join(js, "package.json"), '{"type":"module"}\n');
const { kopyala } = await import(pathToFileURL(join(js, "site.js")).href);
const { durumlar } = await import(pathToFileURL(join(js, "masa.js")).href);

test("kopyala: true when the clipboard takes the text", async () => {
  const yazilan = [];
  assert.equal(await kopyala("cümle", { writeText: async (t) => { yazilan.push(t); } }), true);
  assert.deepEqual(yazilan, ["cümle"]);
});

test("kopyala: false without a clipboard", async () => {
  assert.equal(await kopyala("cümle", undefined), false);
  assert.equal(await kopyala("cümle", null), false);
  assert.equal(await kopyala("cümle", {}), false);
});

test("kopyala: false when the clipboard refuses, never throws", async () => {
  assert.equal(await kopyala("cümle", { writeText: () => Promise.reject(new Error("izin yok")) }), false);
  assert.equal(await kopyala("cümle", { writeText: () => { throw new Error("izin yok"); } }), false);
});

test("durumlar: six feature statuses become the ring's 2 / 1 / 0", () => {
  assert.deepEqual(durumlar("tamam,denemede,yolda,yolda,yolda,yolda"), [2, 1, 0, 0, 0, 0]);
  assert.deepEqual(durumlar("tamam,tamam,denemede,yolda,yolda,yolda"), [2, 2, 1, 0, 0, 0]);
});

test("durumlar: an unknown word is on the way; a wrong count or no list leaves all six on the way", () => {
  assert.deepEqual(durumlar("tamam,bilinmeyen,yolda,yolda,yolda,yolda"), [2, 0, 0, 0, 0, 0]);
  assert.deepEqual(durumlar("tamam,denemede"), [0, 0, 0, 0, 0, 0]);
  assert.deepEqual(durumlar(undefined), [0, 0, 0, 0, 0, 0]);
  assert.deepEqual(durumlar(""), [0, 0, 0, 0, 0, 0]);
});

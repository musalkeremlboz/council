// The section scripts' pure functions, loaded as the browser loads them (a plain script that registers itself on
// window.Panel) into a bare context: no DOM, no packages. Run by tests/test_panel_js.py.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import vm from "node:vm";

const STATIC = fileURLToPath(new URL("../../council/panel/static/", import.meta.url));

function load(...names) {
  const Panel = { sections: {}, texts: {}, fmt: {}, el() {}, svg() {}, fill() {}, rebuild() {}, reducedMotion: true };
  const context = vm.createContext({ window: { Panel } });
  for (const name of names) vm.runInContext(readFileSync(STATIC + name, "utf8"), context, { filename: name });
  return Panel;
}

const { map: M, notes: N } = load("map.js", "notes.js");

function memory(regionNames, perRegion) {
  const notes = [{ path: "core.md", region: "cekirdek", chars: 900 }];
  regionNames.forEach((r, j) => {
    for (let k = 0; k < perRegion(j); k++) notes.push({ path: `projects/${r}/n${k}.md`, region: r, chars: 50 * k });
  });
  const counts = new Map();
  notes.forEach((n) => counts.set(n.region, (counts.get(n.region) || 0) + 1));
  return { notes, links: [[0, 1], [1, 2]], recent: ["core.md"],
    regions: [...counts].map(([id, count]) => ({ id, name: id, count })) };
}

const TEN = memory(["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"], (j) => [70, 40, 25, 20, 15, 10, 8, 6, 4, 1][j]);

test("the same memory always lays out the same map", () => {
  const pos = (m) => JSON.stringify(m.notes.map((n) => n.p.map((v) => v.toFixed(6))));
  assert.equal(pos(M.layout(TEN)), pos(M.layout(JSON.parse(JSON.stringify(TEN)))));
  assert.equal(TEN.notes.length, 200);
});

test("no two region spheres meet, nor reach the centre ring", () => {
  const outer = M.layout(TEN).regions.filter((r) => r.id !== "cekirdek");
  assert.equal(outer.length, 10);
  outer.forEach((a, i) => {
    assert.ok(Math.hypot(...a.centre) - a.r > 48, a.id);
    outer.slice(i + 1).forEach((b) => {
      const d = Math.hypot(a.centre[0] - b.centre[0], a.centre[1] - b.centre[1], a.centre[2] - b.centre[2]);
      assert.ok(d > a.r + b.r, `${a.id} meets ${b.id}`);
    });
  });
});

test("a folder may be named like a property of every object", () => {
  const odd = memory(["constructor", "__proto__", "toString", "valueOf", "hasOwnProperty"], () => 3);
  const model = M.layout(odd);
  assert.equal(model.regions.filter((r) => r.id !== "cekirdek").length, 5);
  assert.equal(model.byId.get("__proto__").count, 3);
  assert.equal(model.index.get("projects/constructor/n0.md"), 1);
  const hidden = Object.create(null);
  hidden.constructor = true;
  assert.equal(M.shownNotes(model, hidden).filter(Boolean).length, 13);
});

test("at zoom 1 the frame spans 0.88 of the short side and every note stays on the stage at any turn", () => {
  const model = M.layout(TEN);
  for (const [w, h] of [[900, 560], [360, 640], [1400, 1400]]) {
    const f = M.fit(model, w, h);
    assert.ok(Math.abs((2 * model.extent * f.scale) / Math.min(w, h) - 0.88) < 1e-9);
    for (let yaw = 0; yaw < 2 * Math.PI; yaw += 0.13) {
      for (let pitch = -1.3; pitch <= 1.3; pitch += 0.1) {
        const view = { yaw, pitch, zoom: 1, scale: f.scale, perspective: f.perspective };
        model.notes.forEach((n) => {
          const [x, y, , k] = M.project(n.p, view), r = Math.max(3, n.r * k);
          assert.ok(Math.abs(x) + r <= w / 2 && Math.abs(y) + r <= h / 2, `${n.path} leaves the ${w}x${h} stage`);
        });
      }
    }
  }
});

test("the calendar's circle grows at 21, 81 and 111 changes", () => {
  const size = (n) => (N.stepOf(n) || { size: 0 }).size;
  assert.deepEqual([0, 1, 20, 21, 80, 81, 110, 111, 5000].map(size), [0, 10, 10, 16, 16, 22, 22, 28, 28]);
});

test("the ranking's axis names distinct whole numbers", () => {
  assert.deepEqual([...N.ticks(1)], [0, 1]);
  assert.deepEqual([...N.ticks(2)], [0, 1, 2]);
  assert.deepEqual([...N.ticks(9)], [0, 5, 9]);
});

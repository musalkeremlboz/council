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

// ---------- the schema: merging pulse answers, following the newest, the dot's journey ----------

const { schema: S } = load("schema.js");
const ev = (key, ts, kind = "inject") => ({ key, ts, kind, path: ["h2", "ara", "sec", "haf"] });
const keys = (list) => [...list].map((e) => e.key);  // an array of this realm, for deepEqual

test("merging keeps the newest first, drops a repeat by its key and stops at the cap", () => {
  const list = [ev("c3", 30), ev("u2", 20), ev("u1", 10)];
  assert.deepEqual(keys(S.mergeEvents(list, [ev("c3", 30), ev("u4", 40)], 30)), ["u4", "c3", "u2", "u1"]);
  assert.deepEqual(keys(S.mergeEvents(list, [ev("u4", 40), ev("u5", 50)], 3)), ["u5", "u4", "c3"]);
  assert.deepEqual(keys(S.mergeEvents(list, [], 30)), ["c3", "u2", "u1"]);
  // the inputs are left as they were
  assert.deepEqual(keys(list), ["c3", "u2", "u1"]);
});

test("two events of the same second and kind are both kept; a repeat of either is not", () => {
  const twins = [ev("u8", 100), ev("u7", 100)];
  const once = S.mergeEvents([ev("u1", 10)], twins, 30);
  assert.deepEqual(keys(once), ["u8", "u7", "u1"]);
  assert.deepEqual(keys(S.mergeEvents(once, [ev("u7", 100), ev("u8", 100)], 30)), ["u8", "u7", "u1"]);
  const commits = S.mergeEvents([], [ev("caaa", 5, "edit"), ev("cbbb", 5, "edit")], 30);
  assert.equal(commits.length, 2);
});

// the page's own state and the two functions every answer goes through (no DOM is touched by either)
const answer = (...events) => ({ events, blocks: [] });

test("a pulse event of the same second as the schema answer's newest survives the merge and is not new again", () => {
  assert.deepEqual(keys(S.pulseKept([ev("b", 20), ev("a", 10)], 20)), ["b"]);
  assert.deepEqual(keys(S.pulseKept([ev("b", 20), ev("a", 10)], 21)), []);
  const s = S.newState(null);
  s.dot = true;
  S.take(s, answer(ev("a", 10)));
  // the pulse brings b; its dot plays
  S.arrive(s, [ev("b", 20)], s.events);
  assert.deepEqual(keys(s.queue), ["b"]);
  s.queue = [];
  // the five-second answer was computed in the same second, just before b's commit: it knows x but not b
  S.take(s, answer(ev("x", 20), ev("a", 10)));
  assert.ok(keys(s.events).includes("b"));
  s.queue = [];
  // the next answer has b: it is known, no second dot
  S.take(s, answer(ev("b", 20), ev("x", 20), ev("a", 10)));
  assert.deepEqual(keys(s.queue), []);
  assert.deepEqual(keys(s.events).sort(), ["a", "b", "x"]);
});

test("the opening list plays no dot and one new event plays exactly one", () => {
  const s = S.newState(null);
  s.dot = true;
  S.take(s, answer(ev("u2", 20), ev("u1", 10)));
  assert.deepEqual(keys(s.queue), []);
  S.arrive(s, [ev("u3", 30), ev("u2", 20)], s.events);
  assert.deepEqual(keys(s.queue), ["u3"]);
  // the same event again, by the pulse or by the next schema answer: nothing more
  S.arrive(s, [ev("u3", 30)], s.events);
  S.take(s, answer(ev("u3", 30), ev("u2", 20), ev("u1", 10)));
  assert.deepEqual(keys(s.queue), ["u3"]);
});

test("the selection rule, through arrive, follows the newest real event and leaves an older choice alone", () => {
  const s = S.newState(null);
  S.take(s, answer(ev("u2", 20), ev("u1", 10)));
  assert.equal(s.selected, "u2");
  S.arrive(s, [ev("u3", 30)], s.events);
  assert.equal(s.selected, "u3");
  s.selected = "u1";
  S.arrive(s, [ev("u4", 40)], s.events);
  assert.equal(s.selected, "u1");
  s.live = false;
  s.selected = "u4";
  S.arrive(s, [ev("u5", 50)], s.events);
  assert.equal(s.selected, "u4");  // not followed: the selection stays
});

test("the selection follows the newest only while the newest is selected", () => {
  assert.equal(S.nextSelection("u2", "u2", "u5"), "u5");  // the newest was selected: the new newest is
  assert.equal(S.nextSelection(null, "u2", "u5"), "u5");  // nothing was selected
  assert.equal(S.nextSelection("u1", "u2", "u5"), "u1");  // an older one stays
});

test("the places of a path are visited in drawing order, the ring last", () => {
  const blocks = ["h1", "bas", "diz", "h2", "ara", "sec", "isa", "h3", "yaz", "ogr", "haf", "yed", "den"]
    .map((id) => ({ id }));
  assert.deepEqual([...S.route(["h2", "ara", "sec", "haf", "isa"], blocks)], ["h2", "ara", "sec", "isa", "haf"]);
  assert.deepEqual([...S.route(["h3", "yaz", "haf"], blocks)], ["h3", "yaz", "haf"]);
  assert.deepEqual([...S.route(["haf"], blocks)], ["haf"]);
  assert.deepEqual([...S.route(["haf", "nope", "haf"], blocks)], ["haf"]);
});

test("a journey between two places runs from 0 to 1", () => {
  const frames = S.journey([{ x: 10, y: 20 }, { x: 110, y: 20 }], 260);
  assert.deepEqual([...frames].map((f) => [f.x, f.y, f.offset]), [[10, 20, 0], [110, 20, 1]]);
});

test("a journey across two lanes has offsets in proportion to the distance and no zero-length hop", () => {
  // two blocks of one lane, then down and across to the ring
  const pts = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 0 }, { x: 400, y: 400 }];
  const frames = S.journey(pts, 260);
  assert.equal(frames.length, 3);
  assert.deepEqual([...frames].map((f) => f.offset), [0, 100 / 600, 1]);
  for (let i = 1; i < frames.length; i++) {
    assert.ok(frames[i].offset > frames[i - 1].offset);
    assert.ok(Math.hypot(frames[i].x - frames[i - 1].x, frames[i].y - frames[i - 1].y) > 0);
  }
  // about 260 px/s, and never less than 450 ms a hop
  assert.equal(S.travelTime(pts, 260), Math.round((600 / 260) * 1000));
  assert.equal(S.travelTime([{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 20, y: 0 }], 260), 900);
});

test("a single place gives no hop, and the dot only shows itself there", () => {
  const frames = S.journey([{ x: 50, y: 60 }], 260);
  assert.equal(frames.length, 1);
  assert.equal(frames[0].offset, 0);
  assert.deepEqual(S.journey([{ x: 5, y: 5 }, { x: 5, y: 5 }], 260).length, 1);
  assert.equal(S.journey([], 260).length, 0);
  assert.ok(S.travelTime([{ x: 50, y: 60 }], 260) >= 450);
});

test("the events of the opening are not new; a repeat is dropped; a new event is reported once", () => {
  const opening = S.novel(Object.create(null), [ev("u1", 10), ev("c2", 20)], true);
  assert.equal(opening.news.length, 0);
  // the server re-sends the note change of the mark's second: nothing new, nothing to redraw
  const repeat = S.novel(opening.seen, [ev("c2", 20)], false);
  assert.equal(repeat.news.length, 0);
  const fresh = S.novel(repeat.seen, [ev("u3", 30), ev("c2", 20), ev("u3", 30)], false);
  assert.deepEqual(keys(fresh.news), ["u3"]);
  assert.equal(S.novel(fresh.seen, [ev("u3", 30)], false).news.length, 0);
  // the known keys given in are left as they were
  assert.equal(Object.keys(opening.seen).length, 2);
});

test("the dot shows only inside the lanes box, and everywhere once it has left the lanes along its wire", () => {
  const lanes = { left: 0, top: 0, right: 300, bottom: 200 };
  // a block scrolled out of the lanes box: not drawn, not even over the ring column
  assert.equal(S.shown({ x: 340, y: 100 }, lanes, false), false);
  assert.equal(S.shown({ x: 150, y: 300 }, lanes, false), false);
  assert.equal(S.shown({ x: 150, y: 100 }, lanes, false), true);
  assert.equal(S.shown({ x: 302, y: 100 }, lanes, false), true);  // its own half-width at the edge
  // past the end of the lane's line: on the vertical line and in the ring column
  assert.equal(S.shown({ x: 301, y: 400 }, lanes, true), true);
});

const SIDE = { side: true, lineX: 500, ringY: 120, entryX: 560, borderY: 0, leftX: 0 };
const STACKED = { side: false, lineX: 380, ringY: 700, entryX: 140, borderY: 520, leftX: 100 };
const xy = (pts) => [...pts].map((p) => [p.x, p.y]);

test("a journey to the ring follows the lane's line, the vertical line, then into the ring's left edge", () => {
  const w = S.wires([{ x: 60, y: 175 }, { x: 230, y: 175 }], true, SIDE);
  assert.deepEqual(xy(w.points), [[60, 175], [230, 175], [500, 175], [500, 120], [560, 120]]);
  assert.equal(w.lanePart, 2);
  // stacked: down the lanes' right edge to the column's top line, along it, down beside the ring, into its edge
  const v = S.wires([{ x: 60, y: 100 }], true, STACKED);
  assert.deepEqual(xy(v.points), [[60, 100], [380, 100], [380, 520], [100, 520], [100, 700], [140, 700]]);
  // the ring alone: the dot shows at the ring's edge, never on its label
  const r = S.wires([], true, SIDE);
  assert.deepEqual(xy(r.points), [[560, 120]]);
  assert.equal(r.lanePart, 0);
  // a journey that does not reach the ring stops at its last block
  const n = S.wires([{ x: 60, y: 175 }, { x: 230, y: 175 }], false, SIDE);
  assert.deepEqual(xy(n.points), [[60, 175], [230, 175]]);
  assert.equal(n.lanePart, 2);
});

test("an L-shaped journey keeps its offsets in proportion to the distance", () => {
  const frames = S.journey([{ x: 0, y: 0 }, { x: 200, y: 0 }, { x: 200, y: 150 }, { x: 240, y: 150 }], 260);
  assert.deepEqual([...frames].map((f) => f.offset), [0, 200 / 390, 350 / 390, 1]);
  // the lane's line already at the ring's height: the vertical hop has no length and is left out
  const level = S.wires([{ x: 60, y: 120 }], true, SIDE);
  const f = S.journey(level.points, 260);
  assert.deepEqual([...f].map((k) => [k.x, k.y]), [[60, 120], [500, 120], [560, 120]]);
  for (let i = 1; i < f.length; i++) assert.ok(f[i].offset > f[i - 1].offset);
  // the dot leaves the lanes where the lane's line ends
  assert.equal(S.offsetAt(level.points, level.lanePart), 440 / 500);
  assert.equal(S.offsetAt([{ x: 1, y: 1 }], 0), 0);
});

// ---------- today: the day's events grouped by session ----------

const { today: T } = load("today.js");
const plain = (v) => JSON.parse(JSON.stringify(v));  // objects of this realm, for deepEqual
const tev = (minute, lane, session, at_limit = false) => ({ minute, lane, session, at_limit, chars: 100,
  kind: "k", paths: [] });
const DAYDATA = {
  sessions: [
    { id: "aaaaaaaa", key: "aaaaaaaa-1", first_minute: 540, last_minute: 560, events: 3, at_limit: 1, chars: 300 },
    { id: "bbbbbbbb", key: "bbbbbbbb-1", first_minute: 545, last_minute: 545, events: 1, at_limit: 0, chars: 100 },
    { id: "aaaaaaaa", key: "aaaaaaaa-2", first_minute: 600, last_minute: 600, events: 1, at_limit: 0, chars: 100 },
    { id: "", key: "", first_minute: 550, last_minute: 700, events: 2, at_limit: 1, chars: 200 },
  ],
  events: [tev(540, "start", 0), tev(545, "inject", 1), tev(550, "inject", 3, true), tev(552, "inject", 0, true),
    tev(560, "read", 0), tev(600, "inject", 2), tev(700, "search", 3)],
};

test("sessions come latest activity first, the one without a session last, each with its events oldest first", () => {
  const rows = plain(T.sessionRows(DAYDATA, false));
  // by last event: 600, 560, 545; the session-less group last although its last event is the latest
  assert.deepEqual(rows.map((r) => r.index), [2, 0, 1, 3]);
  const a = rows[1];
  assert.deepEqual(a.events, [0, 3, 4]);
  assert.equal(a.first, 540);
  assert.equal(a.last, 560);
  assert.deepEqual(a.counts, { start: 1, inject: 1, read: 1 });
  assert.equal(a.atLimit, 1);
  // two sessions may show the same eight characters; each is known by its own key and its first minute
  assert.equal(a.id, "aaaaaaaa");
  assert.equal(a.key, "aaaaaaaa-1@540");
  assert.equal(rows[0].id, "aaaaaaaa");
  assert.equal(rows[0].key, "aaaaaaaa-2@600");
  assert.deepEqual(rows[3].events, [2, 6]);
  assert.deepEqual(rows[3].counts, { inject: 1, search: 1 });
  assert.equal(rows[3].key, "@550");
});

test("sessions whose last events fall in the same minute go by their first event, the latest first", () => {
  const data = { sessions: [
    { id: "x", key: "x", first_minute: 500, last_minute: 600 }, { id: "y", key: "y", first_minute: 550, last_minute: 600 }],
  events: [tev(500, "read", 0), tev(600, "read", 0), tev(550, "read", 1), tev(600, "read", 1)] };
  assert.deepEqual(plain(T.sessionRows(data, false)).map((r) => r.id), ["y", "x"]);
});

test("a session with a single event has one minute for its start and its end", () => {
  const b = plain(T.sessionRows(DAYDATA, false))[0];
  assert.deepEqual(b.events, [5]);
  assert.equal(b.first, 600);
  assert.equal(b.last, 600);
  assert.equal(b.atLimit, 0);
});

test("under the at-limit filter only the events at the limit stay, and a session with none is left out", () => {
  const rows = plain(T.sessionRows(DAYDATA, true));
  assert.deepEqual(rows.map((r) => r.key), ["aaaaaaaa-1@540", "@550"]);  // the key does not move with the filter
  assert.deepEqual(rows[0].events, [3]);
  assert.equal(rows[0].first, 552);
  assert.equal(rows[0].last, 552);
  assert.deepEqual(rows[0].counts, { inject: 1 });
  assert.deepEqual(rows[1].events, [2]);
});

test("a day without events has no sessions", () => {
  assert.equal(T.sessionRows({ sessions: [], events: [] }, false).length, 0);
  assert.equal(T.sessionRows({ events: [] }, true).length, 0);
});

// ---------- the theme ----------

function loadTheme(stored) {
  const store = stored === undefined ? {} : { "council-panel-theme": stored };
  const localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; } };
  const window = { localStorage };
  vm.runInContext(readFileSync(STATIC + "theme.js", "utf8"), vm.createContext({ window }), { filename: "theme.js" });
  return { theme: window.PanelTheme, store };
}

test("a stored theme is light, dark or the system's", () => {
  const { theme } = loadTheme();
  assert.equal(theme.resolveTheme("light"), "light");
  assert.equal(theme.resolveTheme("dark"), "dark");
  for (const odd of [null, undefined, "", "system", "Dark", " dark", "auto", 1, {}]) assert.equal(theme.resolveTheme(odd), null, String(odd));
});

test("the choice is kept and read back; the system's choice is no stored value", () => {
  const { theme, store } = loadTheme("dark");
  assert.equal(theme.get(), "dark");
  theme.set("light");
  assert.equal(store["council-panel-theme"], "light");
  assert.equal(theme.get(), "light");
  theme.set("system");
  assert.equal("council-panel-theme" in store, false);
  assert.equal(theme.get(), "system");
  assert.equal(loadTheme("purple").theme.get(), "system");
});

test("without storage the choice still holds for the page's life", () => {
  const window = { get localStorage() { throw new Error("denied"); } };
  vm.runInContext(readFileSync(STATIC + "theme.js", "utf8"), vm.createContext({ window }), { filename: "theme.js" });
  assert.equal(window.PanelTheme.get(), "system");
  window.PanelTheme.set("dark");
  assert.equal(window.PanelTheme.get(), "dark");
});

function themeWorld(stored) {
  const store = stored === undefined ? {} : { "council-panel-theme": stored };
  const localStorage = { getItem: (k) => (k in store ? store[k] : null), setItem: (k, v) => { store[k] = String(v); },
    removeItem: (k) => { delete store[k]; } };
  const listeners = {}, events = [], attrs = {};
  const window = { localStorage,
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); },
    dispatchEvent: (e) => { events.push(e.type); (listeners[e.type] || []).forEach((fn) => fn(e)); return true; } };
  const document = { documentElement: { setAttribute: (k, v) => { attrs[k] = v; }, removeAttribute: (k) => { delete attrs[k]; } } };
  vm.runInContext(readFileSync(STATIC + "theme.js", "utf8"), vm.createContext({ window, document, Event }), { filename: "theme.js" });
  return { theme: window.PanelTheme, store, listeners, events, attrs };
}

test("a choice is announced, and a choice made in another tab is followed", () => {
  const w = themeWorld("light");
  assert.equal(w.attrs["data-theme"], "light");
  w.theme.set("dark");
  assert.deepEqual(w.events, ["council-theme"]);
  assert.equal(w.attrs["data-theme"], "dark");
  // another tab chose the system: storage changes under us and a storage event arrives
  delete w.store["council-panel-theme"];
  w.listeners.storage.forEach((fn) => fn({ key: "council-panel-theme", newValue: null }));
  assert.equal(w.theme.get(), "system");
  assert.equal("data-theme" in w.attrs, false);
  assert.deepEqual(w.events, ["council-theme", "council-theme"]);
  // and then dark again; an unrelated key changes nothing
  w.store["council-panel-theme"] = "dark";
  w.listeners.storage.forEach((fn) => fn({ key: "council-panel-theme", newValue: "dark" }));
  assert.equal(w.attrs["data-theme"], "dark");
  w.listeners.storage.forEach((fn) => fn({ key: "something-else", newValue: "x" }));
  assert.equal(w.events.length, 3);
});

// ---------- settings: the three theme buttons, against a tiny stand-in for the DOM ----------

function fakeNode(tag) {
  const node = { tag, attrs: {}, children: [], handlers: {},
    setAttribute(k, v) { this.attrs[k] = String(v); }, getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    appendChild(c) { this.children.push(c); return c; }, addEventListener(type, fn) { this.handlers[type] = fn; } };
  return node;
}
function fakeEl(tag, attrs, children) {
  const node = fakeNode(tag);
  Object.keys(attrs || {}).forEach((k) => {
    const v = attrs[k];
    if (v === null || v === undefined || v === false) return;
    if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (k !== "text" && k !== "style") node.setAttribute(k, v);
  });
  [].concat(children === undefined ? [] : children).forEach((c) => { if (c !== null && c !== undefined) node.appendChild(c); });
  return node;
}
function all(node, test, out = []) {
  if (node && typeof node === "object") { if (test(node)) out.push(node); (node.children || []).forEach((c) => all(c, test, out)); }
  return out;
}

test("a theme button sets the theme and is then the one pressed; a change elsewhere moves the press", () => {
  let chosen = "system";
  const calls = [], listeners = {};
  const Panel = { sections: {}, texts: { theme_system: "S", theme_light: "L", theme_dark: "D" }, el: fakeEl,
    rebuild: (root, draw) => { root.children = []; draw(); } };
  const window = { Panel, PanelTheme: { get: () => chosen, set: (v) => { calls.push(v); chosen = v; }, EVENT: "council-theme" },
    addEventListener: (type, fn) => { (listeners[type] = listeners[type] || []).push(fn); } };
  vm.runInContext(readFileSync(STATIC + "settings.js", "utf8"), vm.createContext({ window }), { filename: "settings.js" });
  const root = fakeNode("div");
  Panel.sections.settings.render(root, {});
  const buttons = all(root, (n) => n.attrs["data-theme-choice"]);
  assert.deepEqual(buttons.map((b) => b.attrs["data-theme-choice"]), ["system", "light", "dark"]);
  const pressed = () => buttons.filter((b) => b.attrs["aria-pressed"] === "true").map((b) => b.attrs["data-theme-choice"]);
  assert.deepEqual(pressed(), ["system"]);
  buttons[2].handlers.click();
  assert.deepEqual(calls, ["dark"]);
  assert.deepEqual(pressed(), ["dark"]);
  // another tab chose light: theme.js announces it and the buttons follow
  chosen = "light";
  listeners["council-theme"].forEach((fn) => fn());
  assert.deepEqual(pressed(), ["light"]);
});

// ---------- the map's note picker: filtering ----------

test("the note picker filters on the path, ignoring case the Turkish way, and caps the rows", () => {
  const paths = ["core.md", "projects/İzmir/plan.md", "knowledge/ılık-su.md", "people/Işık.md", "rules.md"];
  assert.deepEqual(plain(M.filterNotes(paths, "", 50)), { items: paths, total: 5 });
  assert.deepEqual(plain(M.filterNotes(paths, "  ", 50)), { items: paths, total: 5 });
  assert.deepEqual(plain(M.filterNotes(paths, "plan", 50)), { items: ["projects/İzmir/plan.md"], total: 1 });
  // İ lowers to i, I lowers to ı
  assert.deepEqual(plain(M.filterNotes(paths, "izmir", 50)).items, ["projects/İzmir/plan.md"]);
  assert.deepEqual(plain(M.filterNotes(paths, "IŞIK", 50)).items, ["people/Işık.md"]);
  assert.deepEqual(plain(M.filterNotes(paths, "ILIK", 50)).items, ["knowledge/ılık-su.md"]);
  assert.deepEqual(plain(M.filterNotes(paths, "RULES", 50)).items, ["rules.md"]);
  assert.deepEqual(plain(M.filterNotes(paths, "yok", 50)), { items: [], total: 0 });
  const many = Array.from({ length: 300 }, (_, i) => `knowledge/ek-${i}.md`);
  const capped = M.filterNotes(many, "ek", 50);
  assert.equal(capped.items.length, 50);
  assert.equal(capped.total, 300);
  assert.equal(capped.items[0], "knowledge/ek-0.md");
});

// ---------- today: the hour labels give way to the "now" label ----------

test("an hour label the now label would cover is hidden; the others stay", () => {
  // the axis is 600px wide: an hour is 25px, a label of five characters about 33px
  assert.deepEqual(plain(T.hiddenHours(720, 600, 5)), [720]);        // now at 12:00 covers 12:00
  assert.deepEqual(plain(T.hiddenHours(700, 600, 5)), [720]);        // 11:40: the label starts just left of 12:00
  assert.deepEqual(plain(T.hiddenHours(9 * 60, 600, 5)), []);        // 09:00: far from every hour label
  assert.deepEqual(plain(T.hiddenHours(0, 600, 5)), [0]);            // midnight covers 00:00
  assert.deepEqual(plain(T.hiddenHours(1430, 600, 5)), [1440]);      // late evening runs into 24:00
  assert.deepEqual(plain(T.hiddenHours(780, 600, 5)), []);           // 13:00 is clear of 12:00 at this width
  assert.deepEqual(plain(T.hiddenHours(780, 300, 5)), [720]);        // but not on a narrow axis
});

// ---------- settings: the password form and its answers ----------

const { settings: Z } = load("settings.js");

test("the change can be sent when the current one is given, the new one fits and both new fields match", () => {
  assert.equal(Z.passwordState("", "", "", 10, 200), "empty");
  assert.equal(Z.passwordState("", "yepyeni-sifre", "yepyeni-sifre", 10, 200), "empty");
  assert.equal(Z.passwordState("eski", "kisa", "kisa", 10, 200), "short");
  assert.equal(Z.passwordState("eski", "x".repeat(201), "x".repeat(201), 10, 200), "long");
  assert.equal(Z.passwordState("eski", "yepyeni-sifre", "yepyeni-sifr", 10, 200), "mismatch");
  assert.equal(Z.passwordState("eski", "yepyeni-sifre", "", 10, 200), "mismatch");
  assert.equal(Z.passwordState("eski", "yepyeni-sifre", "yepyeni-sifre", 10, 200), "ready");
  assert.equal(Z.passwordState("eski", "x".repeat(10), "x".repeat(10), 10, 200), "ready");
  assert.equal(Z.passwordState("eski", "x".repeat(200), "x".repeat(200), 10, 200), "ready");
});

test("the length is counted in characters as the server counts them, not in UTF-16 units", () => {
  const nine = "ğüşçöıİ" + "🗂🗂";                 // nine characters, eleven UTF-16 units
  assert.equal(Z.passwordState("eski", nine, nine, 10, 200), "short");
  assert.equal(Z.passwordState("eski", nine + "a", nine + "a", 10, 200), "ready");
});

test("each answer of the server says its line and which fields to empty", () => {
  assert.deepEqual(plain(Z.passwordAnswer(200, { ok: true, closed: 2 })), { key: "password_ok", n: 2, clear: "all", done: true });
  assert.deepEqual(plain(Z.passwordAnswer(200, { ok: true, closed: 0 })), { key: "password_ok_alone", n: 0, clear: "all", done: true });
  assert.deepEqual(plain(Z.passwordAnswer(403, { error: "wrong" })), { key: "password_wrong", n: 0, clear: "current", done: false });
  assert.deepEqual(plain(Z.passwordAnswer(400, { error: "weak" })), { key: "password_weak", n: 0, clear: "none", done: false });
  assert.deepEqual(plain(Z.passwordAnswer(400, { error: "same" })), { key: "password_same", n: 0, clear: "none", done: false });
  assert.deepEqual(plain(Z.passwordAnswer(429, { error: "locked" })), { key: "password_locked", n: 0, clear: "all", done: false });
  for (const [status, body] of [[500, { error: "unavailable" }], [403, null], [400, { error: "bad_request" }], [0, undefined], [200, {}]]) {
    assert.deepEqual(plain(Z.passwordAnswer(status, body)), { key: "password_failed", n: 0, clear: "none", done: false }, String(status));
  }
});

test("today's open session stays open when a refresh brings a new session above it", () => {
  const open = plain(T.sessionRows(DAYDATA, false)).find((r) => r.id === "bbbbbbbb").key;
  const later = {
    sessions: [{ id: "cccccccc", key: "cccccccc-1", first_minute: 710, last_minute: 712, events: 1, at_limit: 0,
      chars: 100 }, ...DAYDATA.sessions],
    events: [...DAYDATA.events.map((e) => ({ ...e, session: e.session + 1 })), tev(712, "inject", 0)],
  };
  const rows = plain(T.sessionRows(later, false));
  assert.equal(rows[0].id, "cccccccc");
  assert.equal(T.openAfter(later, false, open), open);
  assert.equal(rows.find((r) => r.key === open).events.length, 1);
  // the limit filter hides it (no event at the limit): closed while hidden, the key itself is kept by the page
  assert.equal(T.openAfter(later, true, open), null);
  assert.equal(T.openAfter(later, false, null), null);
  assert.equal(T.openAfter(later, false, "gone@1"), null);
});

/* The map: every note a dot on one canvas, links as thin lines, notes clustered on small spheres per region
   around the centre, where the root notes sit inside the accent ring. Dragging turns it, the wheel and two
   buttons zoom, a slow turn can be switched off. The layout and the hit test are plain functions of the data, so
   the same memory always draws the same map. Only note names are drawn, never note text. */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, t = P.texts, fmt = P.fmt;
  var SEED = 7;
  var ROOT = "cekirdek";            // the region of the notes loaded at every session start
  var SPREAD = 220;                 // the least distance of a region centre from the centre, in model units
  var ROOT_RADIUS = 30, CORE_RING = 48;
  var ROOM = 0.45;                  // a region's sphere is at most this share of the distance to its nearest centre
  var DEPTH = 4;                    // the eye sits this many map radii away: near notes grow at most by 4/3
  var FRAME = 0.88;                 // the frame circle's diameter as a share of the stage's short side at zoom 1
  var LABEL_HEIGHT = 14;
  var NAMES_LIMIT = 60;             // above this many visible notes names are off unless a note is selected
  var ZOOM = [0.5, 2.8], WHEEL = [1.08, 0.93], STEP_ZOOM = 1.2, TURN = 0.35, DRAG = 0.008, PITCH = 1.3;
  var SPEED = 0.075;                // radians a second
  var CLICK = 4;                    // pixels a press may move and still be a click
  var INK = "#111416", GROUND = "#F4F5F3", ACCENT = "#E8421F", HAIRLINE = "#D5D8D4", SECONDARY = "#4A5157";
  var states = new WeakMap();

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  // ---------- the layout: data in, data out ----------

  function random(seed) {
    var a = seed | 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var x = Math.imul(a ^ (a >>> 15), 1 | a);
      x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* point i of n spread evenly over a unit sphere */
  function sphere(i, n) {
    var y = n === 1 ? 0 : 1 - (2 * i + 1) / n, r = Math.sqrt(Math.max(0, 1 - y * y)), a = i * 2.399963;
    return [Math.cos(a) * r, y, Math.sin(a) * r];
  }

  function radiusOf(chars) { return 4 + Math.min(8, Math.sqrt(Math.max(0, chars || 0)) / 38); }

  function nameOf(path) {
    var name = String(path).split("/").pop().replace(/\.md$/, "");
    return name.length > 30 ? name.slice(0, 29) + "…" : name;
  }

  /* The map's model: notes with a fixed position, regions with their centre and size, links, neighbours.
     Everything keyed by a name from the data is a Map, so a folder may be called anything, "constructor" too. */
  function layout(data) {
    var rnd = random(SEED), byId = new Map(), regions = [];
    function region(id, name, count) {
      if (!byId.has(id)) { byId.set(id, { id: id, name: name || id, count: count || 0, members: [], centre: [0, 0, 0],
        r: 0, turn: 0 }); regions.push(byId.get(id)); }
      return byId.get(id);
    }
    (data.regions || []).forEach(function (r) { region(r.id, r.name, r.count); });
    var recent = new Set(data.recent || []);
    var index = new Map();
    var notes = data.notes.map(function (n, i) {
      var r = region(n.region);
      r.members.push(i);
      index.set(n.path, i);
      return { i: i, path: n.path, name: nameOf(n.path), region: n.region, sections: n.sections, chars: n.chars,
        skill: !!n.skill, changed: n.changed, recent: recent.has(n.path), r: radiusOf(n.chars), p: [0, 0, 0],
        neighbours: [] };
    });
    var links = (data.links || []).filter(function (l) { return notes[l[0]] && notes[l[1]] && l[0] !== l[1]; });
    links.forEach(function (l) { notes[l[0]].neighbours.push(l[1]); notes[l[1]].neighbours.push(l[0]); });
    notes.forEach(function (n) { n.neighbours.sort(function (a, b) { return a - b; }); });
    var outer = regions.filter(function (r) { return r.id !== ROOT; });
    var spread = spacing(outer);
    regions.forEach(function (r) {
      var n = r.members.length;
      r.count = n;
      r.turn = rnd() * 2 * Math.PI;  // each small sphere starts at its own fixed angle
      if (r.id === ROOT) r.r = ROOT_RADIUS;
      var c = Math.cos(r.turn), s = Math.sin(r.turn);
      r.members.forEach(function (i, k) {
        var v = sphere(k, n), x = v[0] * c + v[2] * s, z = -v[0] * s + v[2] * c;
        notes[i].p = [r.centre[0] + x * r.r, r.centre[1] + v[1] * r.r, r.centre[2] + z * r.r];
      });
    });
    var extent = CORE_RING;
    notes.forEach(function (n) { extent = Math.max(extent, Math.hypot(n.p[0], n.p[1], n.p[2]) + n.r); });
    regions.forEach(function (r) { extent = Math.max(extent, Math.hypot(r.centre[0], r.centre[1], r.centre[2]) + r.r); });
    return { notes: notes, regions: regions, byId: byId, links: links, index: index, extent: extent, spread: spread };
  }

  /* the wanted sphere of a region: it grows with the square root of its notes; one note sits at its centre */
  function wanted(n) { return n <= 1 ? 0 : 10 + 10 * Math.sqrt(n); }

  /* Place the outer regions' centres evenly on a sphere around the centre and give each its radius, so that no
     two spheres meet and none reaches the centre ring: a sphere is at most ROOM times the distance to its nearest
     other centre (the map's own centre counts), and the centres move out until every wanted radius fits. */
  function spacing(outer) {
    var unit = outer.map(function (r, j) { return sphere(j, outer.length); });
    var nearest = unit.map(function (u, j) {
      var d = 1;  // the map's centre is one unit away
      unit.forEach(function (v, k) { if (k !== j) d = Math.min(d, Math.hypot(u[0] - v[0], u[1] - v[1], u[2] - v[2])); });
      return d;
    });
    var spread = SPREAD;
    outer.forEach(function (r, j) {
      spread = Math.max(spread, wanted(r.members.length) / (ROOM * nearest[j]), (CORE_RING + 12) / (1 - ROOM));
    });
    outer.forEach(function (r, j) {
      r.centre = [unit[j][0] * spread, unit[j][1] * spread, unit[j][2] * spread];
      r.r = Math.min(wanted(r.members.length), ROOM * nearest[j] * spread);
    });
    return spread;
  }

  /* The scale at which the frame circle (radius `extent`) spans FRAME of the stage's short side at zoom 1. No
     point is farther than `extent` from the centre, and with the eye DEPTH extents away perspective moves such a
     point at most DEPTH / sqrt(DEPTH^2 - 1) (about 1.033) times its distance out on the screen, so at any turn
     every note stays inside the stage: 0.44 x 1.033 < 0.5 of the short side. */
  function fit(model, w, h) {
    var short = Math.max(20, Math.min(w, h));
    return { scale: FRAME * short / 2 / model.extent, perspective: DEPTH * model.extent };
  }

  /* Region labels as boxes {x, y, width, z} (x the middle, y the bottom) -> where each is drawn, or null when it
     is dropped: nearer labels are placed first; a label that would cover one already placed moves up, then
     down, by one line, and is dropped if it still covers one. */
  function placeLabels(boxes) {
    var placed = [], out = boxes.map(function () { return null; });
    var order = boxes.map(function (b, i) { return i; }).sort(function (a, b) { return boxes[b].z - boxes[a].z || a - b; });
    order.forEach(function (i) {
      var b = boxes[i];
      [0, -(LABEL_HEIGHT + 2), LABEL_HEIGHT + 2].some(function (dy) {
        var box = { left: b.x - b.width / 2, right: b.x + b.width / 2, top: b.y + dy - LABEL_HEIGHT, bottom: b.y + dy };
        var free = placed.every(function (o) {
          return box.right <= o.left || box.left >= o.right || box.bottom <= o.top || box.top >= o.bottom;
        });
        if (free) { placed.push(box); out[i] = { x: b.x, y: b.y + dy }; }
        return free;
      });
    });
    return out;
  }

  /* a point of the model -> [x, y, depth, scale] on the screen, relative to the stage's centre */
  function project(p, view) {
    var cy = Math.cos(view.yaw), sy = Math.sin(view.yaw), cp = Math.cos(view.pitch), sp = Math.sin(view.pitch);
    var x = p[0] * cy + p[2] * sy, z1 = -p[0] * sy + p[2] * cy;
    var y = p[1] * cp - z1 * sp, z = p[1] * sp + z1 * cp;
    var depth = view.perspective || 900;
    var k = view.zoom * (view.scale || 1) * depth / (depth - z);
    return [x * k, y * k, z, k];
  }

  function projectAll(model, view) { return model.notes.map(function (n) { return project(n.p, view); }); }

  /* which notes are drawn, given the hidden regions */
  function shownNotes(model, hidden) { return model.notes.map(function (n) { return !(hidden && hidden[n.region]); }); }

  /* the hidden regions: a dictionary without a prototype, so no region name can collide with one of its keys */
  function noneHidden() { return Object.create(null); }

  /* the note under (x, y) relative to the centre, the nearest one in front first; -1 for none */
  function hitTest(model, projected, shown, x, y) {
    var best = -1, depth = -Infinity;
    model.notes.forEach(function (n, i) {
      if (!shown[i]) return;
      var q = projected[i], reach = Math.max(6, n.r * q[3]) + 4, dx = q[0] - x, dy = q[1] - y;
      if (dx * dx + dy * dy <= reach * reach && q[2] > depth) { best = i; depth = q[2]; }
    });
    return best;
  }

  /* the notes whose names are drawn: with a selection, the selected note and its neighbours; otherwise every
     shown note when names are on and no more than NAMES_LIMIT are shown */
  function labelled(model, shown, selected, namesOn) {
    if (selected >= 0) return [selected].concat(model.notes[selected].neighbours.filter(function (i) { return shown[i]; }));
    var count = shown.filter(Boolean).length;
    if (!namesOn || count > NAMES_LIMIT) return [];
    return model.notes.filter(function (n, i) { return shown[i]; }).map(function (n) { return n.i; });
  }

  // ---------- painting ----------

  function depthAlpha(z) { return clamp(0.65 + z / 600, 0.3, 1); }

  /* the page's text and mono faces, read once from its CSS variables */
  var faces = null;
  function face(name, fallback) {
    if (!faces) faces = {};
    if (!(name in faces)) {
      var v = window.getComputedStyle ? window.getComputedStyle(document.body).getPropertyValue(name) : "";
      faces[name] = (v && v.trim()) || fallback;
    }
    return faces[name];
  }

  /* the view with the scale that fits the stage as it is now */
  function viewOf(s) {
    var f = fit(s.model, s.canvas.clientWidth || 0, s.canvas.clientHeight || 0);
    return { yaw: s.view.yaw, pitch: s.view.pitch, zoom: s.view.zoom, scale: f.scale, perspective: f.perspective };
  }

  function paint(s) {
    var c = s.canvas, ctx = s.ctx;
    if (!ctx) return;
    var w = c.clientWidth || 0, h = c.clientHeight || 0, ratio = window.devicePixelRatio || 1;
    if (c.width !== Math.round(w * ratio) || c.height !== Math.round(h * ratio)) {
      c.width = Math.round(w * ratio); c.height = Math.round(h * ratio);
    }
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.globalAlpha = 1;
    ctx.fillStyle = INK;
    ctx.fillRect(0, 0, w, h);
    ctx.translate(w / 2, h / 2);
    var m = s.model, v = viewOf(s), shown = shownNotes(m, s.hidden), q = projectAll(m, v), unit = v.zoom * v.scale;
    var sel = selectedIndex(s), near = Object.create(null);
    if (sel >= 0) { near[sel] = true; m.notes[sel].neighbours.forEach(function (i) { near[i] = true; }); }

    ctx.lineWidth = 1;
    ctx.strokeStyle = SECONDARY;
    ring(ctx, 0, 0, m.extent * unit);
    ctx.strokeStyle = ACCENT;
    ctx.lineWidth = Math.max(3, 9 * unit);
    ctx.globalAlpha = s.hidden[ROOT] ? 0.25 : 1;
    ring(ctx, 0, 0, CORE_RING * unit);

    ctx.lineWidth = 1;
    ctx.strokeStyle = GROUND;
    m.links.forEach(function (l) {
      if (!shown[l[0]] || !shown[l[1]]) return;
      ctx.globalAlpha = sel < 0 ? 0.17 : (l[0] === sel || l[1] === sel ? 0.9 : 0.06);
      ctx.beginPath(); ctx.moveTo(q[l[0]][0], q[l[0]][1]); ctx.lineTo(q[l[1]][0], q[l[1]][1]); ctx.stroke();
    });

    var order = m.notes.filter(function (n, i) { return shown[i]; }).sort(function (a, b) { return q[a.i][2] - q[b.i][2]; });
    order.forEach(function (n) {
      var p = q[n.i], radius = Math.max(3, n.r * p[3]), chosen = n.i === sel;
      ctx.globalAlpha = sel >= 0 && !near[n.i] ? 0.22 : depthAlpha(p[2]);
      if (chosen) ctx.globalAlpha = 1;
      var colour = chosen ? ACCENT : GROUND;
      if (n.skill) { ctx.strokeStyle = colour; ctx.lineWidth = 2; ring(ctx, p[0], p[1], radius - 1); }
      else { ctx.fillStyle = colour; disc(ctx, p[0], p[1], radius); }
      if (chosen) { ctx.strokeStyle = ACCENT; ctx.lineWidth = 2; ring(ctx, p[0], p[1], radius + 4); }
      if (n.recent) { ctx.fillStyle = ACCENT; disc(ctx, p[0] + radius * 0.75 + 2, p[1] - radius * 0.75 - 2, 2.5); }
    });

    ctx.globalAlpha = 1;
    ctx.fillStyle = HAIRLINE;
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.font = "600 11px " + face("--metin", "sans-serif");
    var named = m.regions.filter(function (r) { return !s.hidden[r.id] && r.count; });
    var labels = named.map(function (r) {
      var p = project(r.centre, v), text = upper(r.name) + " · " + r.count;
      return { text: text, x: p[0], y: p[1] - r.r * p[3] - 8, z: p[2], width: ctx.measureText(text).width };
    });
    placeLabels(labels).forEach(function (at, i) { if (at) ctx.fillText(labels[i].text, at.x, at.y); });

    ctx.font = "11px " + face("--mono", "monospace");
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    labelled(m, shown, sel, s.names).forEach(function (i) {
      var n = m.notes[i], p = q[i], x = p[0] + n.r * p[3] + 6, y = p[1], width = ctx.measureText(n.name).width;
      ctx.globalAlpha = 1;
      ctx.fillStyle = INK;
      ctx.fillRect(x - 5, y - 8, width + 10, 16);
      ctx.globalAlpha = i === sel ? 1 : 0.85;
      ctx.fillStyle = GROUND;
      ctx.fillText(n.name, x, y);
    });
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
  }

  function ring(ctx, x, y, r) { ctx.beginPath(); ctx.arc(x, y, Math.max(0, r), 0, 2 * Math.PI); ctx.stroke(); }
  function disc(ctx, x, y, r) { ctx.beginPath(); ctx.arc(x, y, Math.max(0, r), 0, 2 * Math.PI); ctx.fill(); }

  // ---------- the frame loop: only while turning, dragging or asked for one picture ----------

  function frame(s) {
    if (s.frame || s.stopped) return;
    var raf = window.requestAnimationFrame || function (f) { return setTimeout(function () { f(Date.now()); }, 16); };
    s.frame = raf(function (now) { tick(s, now); });
  }

  function tick(s, now) {
    s.frame = 0;
    if (!s.root.isConnected) { stop(s); return; }        // the section is no longer shown
    if (document.visibilityState !== "visible") { s.last = 0; return; }  // resumed by visibilitychange
    var dt = s.last ? Math.min(now - s.last, 100) : 0;
    if (s.turning && !s.drag) s.view.yaw += SPEED * dt / 1000;
    paint(s);
    if (s.turning && !s.drag) { s.last = now; frame(s); } else s.last = 0;
  }

  function stop(s) {
    s.stopped = true;
    document.removeEventListener("visibilitychange", s.onVisible);
    window.removeEventListener("resize", s.onResize);
    if (s.observer) s.observer.disconnect();
  }

  // ---------- selection and controls ----------

  function selectedIndex(s) {
    var i = s.selected === null ? -1 : s.model.index.get(s.selected);
    return i === undefined ? -1 : i;
  }

  function select(s, i) {
    s.selected = i >= 0 ? s.model.notes[i].path : null;
    panels(s);
    frame(s);
  }

  function regionList(s) {
    var m = s.model;
    return [
      el("div", { class: "bolge-ust" }, [el("h2", { class: "etiket ikincil-yazi" }, upper(t.regions_title)),
        el("button", { type: "button", class: "ikincil kucuk-dugme", "data-key": "bolge-hepsi",
          onclick: function () { s.hidden = noneHidden(); panels(s); frame(s); } }, t.regions_all)]),
      el("div", { class: "bolge-listesi" }, m.regions.filter(function (r) { return r.count; }).map(function (r) {
        var on = !s.hidden[r.id];
        return el("button", { type: "button", class: "bolge", "aria-pressed": on ? "true" : "false", "data-key": "bolge-" + r.id,
          onclick: function () {
            s.hidden[r.id] = on;
            var sel = selectedIndex(s);
            if (sel >= 0 && s.hidden[m.notes[sel].region]) s.selected = null;
            panels(s); frame(s);
          } }, [el("span", { class: "bolge-ad" }, r.name), el("span", { class: "mono" }, fmt.number(r.count))]);
      }))
    ];
  }

  function controls(s, count) {
    function toggle(key, on, text, change) {
      return el("button", { type: "button", class: "ikincil anahtar", "aria-pressed": on ? "true" : "false", "data-key": key,
        onclick: change }, text);
    }
    function small(key, label, text, act) {
      return el("button", { type: "button", class: "ikincil yuvarlak", "aria-label": label, title: label, "data-key": key,
        onclick: act }, text);
    }
    function zoom(by) { s.view.zoom = clamp(s.view.zoom * by, ZOOM[0], ZOOM[1]); frame(s); }
    function turn(by) { s.view.yaw += by; s.turning = false; panels(s); frame(s); }
    var auto = count > NAMES_LIMIT && selectedIndex(s) < 0;
    return [
      toggle("adlar", s.names, s.names && auto ? P.fill(t.names_hidden, { n: fmt.number(NAMES_LIMIT) }) : t.names_on,
        function () { s.names = !s.names; panels(s); frame(s); }),
      toggle("don", s.turning, t.turn_on, function () { s.turning = !s.turning; s.last = 0; panels(s); frame(s); }),
      small("sola", t.turn_left, "←", function () { turn(-TURN); }),
      small("saga", t.turn_right, "→", function () { turn(TURN); }),
      small("uzak", t.zoom_out, "−", function () { zoom(1 / STEP_ZOOM); }),
      small("yakin", t.zoom_in, "+", function () { zoom(STEP_ZOOM); })
    ];
  }

  function picker(s, shown) {
    var sel = s.selected;
    var options = [el("option", { value: "", selected: sel === null }, t.pick_none)].concat(
      s.model.notes.filter(function (n, i) { return shown[i]; }).map(function (n) {
        return el("option", { value: n.path, selected: n.path === sel }, n.path);
      }));
    return [el("label", { class: "etiket ikincil-yazi", for: "harita-sec" }, upper(t.pick_label)),
      el("select", { id: "harita-sec", class: "secim mono", "data-key": "secim", onchange: function (e) {
        var i = e.target.value ? s.model.index.get(e.target.value) : -1;
        select(s, i === undefined ? -1 : i);
      } }, options)];
  }

  function card(s) {
    var m = s.model, i = selectedIndex(s);
    if (i < 0) return el("p", { class: "harita-bos" }, t.map_empty_card);
    var n = m.notes[i], region = m.byId.get(n.region);
    var chips = [P.fill(t.note_sections, { n: fmt.number(n.sections) }), P.fill(t.note_chars, { n: fmt.number(n.chars) }),
      P.fill(t.note_links, { n: fmt.number(n.neighbours.length) })];
    if (n.changed) chips.push(P.fill(t.note_changed, { date: fmt.date(n.changed) }));
    if (n.recent) chips.push(t.note_recent);
    return el("section", { class: "kart secili-not", "aria-labelledby": "secili-yol" }, [
      el("div", { class: "etiket ikincil-yazi" }, upper(P.fill(t.selected_note, { region: region ? region.name : n.region }))),
      el("p", { class: "secili-yol mono", id: "secili-yol" }, n.path),
      el("ul", { class: "fisler" }, chips.map(function (c) { return el("li", { class: "deger-kutu mono" }, c); })),
      el("div", { class: "etiket ikincil-yazi" }, upper(t.neighbours)),
      n.neighbours.length ? el("div", { class: "komsular" }, n.neighbours.map(function (j) {
        return el("button", { type: "button", class: "komsu mono", "data-key": "komsu-" + m.notes[j].path,
          onclick: function () {
            if (s.hidden[m.notes[j].region]) s.hidden[m.notes[j].region] = false;
            select(s, j);
          } }, m.notes[j].path);
      })) : el("p", { class: "bos" }, t.neighbours_none)
    ]);
  }

  /* everything around the canvas; the canvas itself stays */
  function panels(s) {
    var m = s.model, shown = shownNotes(m, s.hidden), count = shown.filter(Boolean).length;
    var links = m.links.filter(function (l) { return shown[l[0]] && shown[l[1]]; }).length;
    var regions = m.regions.filter(function (r) { return r.count && !s.hidden[r.id]; }).length;
    s.canvas.setAttribute("aria-label", P.fill(t.map_label, { notes: fmt.number(count), links: fmt.number(links) }));
    P.rebuild(s.parts.regions, function () { regionList(s).forEach(function (n) { s.parts.regions.appendChild(n); }); });
    s.parts.summary.textContent = P.fill(t.map_sum, { notes: fmt.number(count), links: fmt.number(links),
      regions: fmt.number(regions) });
    P.rebuild(s.parts.controls, function () { controls(s, count).forEach(function (n) { s.parts.controls.appendChild(n); }); });
    P.rebuild(s.parts.picker, function () { picker(s, shown).forEach(function (n) { s.parts.picker.appendChild(n); }); });
    P.rebuild(s.parts.card, function () { s.parts.card.appendChild(card(s)); });
  }

  // ---------- the pointer ----------

  function at(s, e) {
    var b = s.canvas.getBoundingClientRect();
    return [e.clientX - b.left - b.width / 2, e.clientY - b.top - b.height / 2];
  }

  function listen(s) {
    var c = s.canvas;
    c.addEventListener("pointerdown", function (e) {
      s.drag = { x: e.clientX, y: e.clientY, yaw: s.view.yaw, pitch: s.view.pitch, moved: false };
      if (c.setPointerCapture && e.pointerId !== undefined) c.setPointerCapture(e.pointerId);
    });
    c.addEventListener("pointermove", function (e) {
      var d = s.drag;
      if (!d) return;
      var dx = e.clientX - d.x, dy = e.clientY - d.y;
      if (Math.abs(dx) + Math.abs(dy) > CLICK) d.moved = true;
      if (!d.moved) return;
      s.view.yaw = d.yaw + dx * DRAG;
      // on touch a vertical swipe scrolls the page (touch-action: pan-y), so only a mouse or pen tilts the map
      if (e.pointerType !== "touch") s.view.pitch = clamp(d.pitch + dy * DRAG, -PITCH, PITCH);
      frame(s);
    });
    c.addEventListener("pointerup", function (e) {
      var d = s.drag;
      s.drag = null;
      if (d && !d.moved) {
        var xy = at(s, e), i = hitTest(s.model, projectAll(s.model, viewOf(s)), shownNotes(s.model, s.hidden), xy[0], xy[1]);
        select(s, i >= 0 && i === selectedIndex(s) ? -1 : i);
      }
      frame(s);
    });
    c.addEventListener("pointercancel", function () { s.drag = null; frame(s); });
    c.addEventListener("wheel", function (e) {
      e.preventDefault();
      s.view.zoom = clamp(s.view.zoom * (e.deltaY < 0 ? WHEEL[0] : WHEEL[1]), ZOOM[0], ZOOM[1]);
      frame(s);
    }, { passive: false });
    s.onVisible = function () {
      if (!s.root.isConnected) { stop(s); return; }
      if (document.visibilityState === "visible") { s.last = 0; frame(s); }
    };
    s.onResize = function () { if (!s.root.isConnected) stop(s); else frame(s); };
    document.addEventListener("visibilitychange", s.onVisible);
    if (window.ResizeObserver) { s.observer = new window.ResizeObserver(s.onResize); s.observer.observe(c); }
    else window.addEventListener("resize", s.onResize);
  }

  // ---------- the section ----------

  function build(s) {
    var parts = s.parts = {
      regions: el("section", { class: "harita-bolgeler", "aria-label": t.regions_title }),
      summary: el("p", { class: "mono harita-ozet" }),
      controls: el("div", { class: "harita-dugmeler" }),
      picker: el("div", { class: "harita-secim" }),
      card: el("div", { class: "harita-kart", "aria-live": "polite" })
    };
    s.canvas = el("canvas", { class: "harita-tuval", role: "img" });
    s.ctx = s.canvas.getContext ? s.canvas.getContext("2d") : null;
    var legend = el("ul", { class: "lejant", "aria-label": t.map_title }, [
      el("li", {}, [el("span", { class: "lejant-isaret nokta-ornek", "aria-hidden": "true" }), t.legend_note]),
      el("li", {}, [el("span", { class: "lejant-isaret halka-ornek", "aria-hidden": "true" }), t.legend_skill]),
      el("li", {}, [el("span", { class: "lejant-isaret merkez-ornek", "aria-hidden": "true" }), t.legend_core]),
      el("li", {}, [el("span", { class: "lejant-isaret son-ornek", "aria-hidden": "true" }), t.legend_recent])
    ]);
    s.root.appendChild(el("div", { class: "harita" }, [
      el("div", { class: "baslik-satiri" }, [el("h1", { class: "gosterim buyuk" }, upper(t.map_title)),
        el("p", { class: "on-cumle" }, t.map_lede)]),
      el("div", { class: "harita-ic" }, [
        parts.regions,
        el("section", { class: "harita-orta", "aria-label": t.map_title }, [
          el("div", { class: "harita-ust" }, [parts.summary, parts.controls]),
          el("div", { class: "sahne" }, [s.canvas, el("p", { class: "ipucu mono", "aria-hidden": "true" }, t.map_hint)]),
          legend,
          parts.picker,
          parts.card
        ])
      ])
    ]));
  }

  P.sections.map = {
    render: function (root, data) {
      var s = { root: root, data: data, model: layout(data), view: { yaw: 0.6, pitch: -0.28, zoom: 1 },
        turning: !P.reducedMotion, names: true, hidden: noneHidden(), selected: null, drag: null, frame: 0, last: 0,
        stopped: false };
      states.set(root, s);
      build(s);
      panels(s);
      listen(s);
      frame(s);
    },
    update: function (root, data) {
      var s = states.get(root);
      if (!s) { this.render(root, data); return; }
      s.data = data;
      s.model = layout(data);
      if (s.selected !== null && !s.model.index.has(s.selected)) s.selected = null;
      panels(s);
      frame(s);
    }
  };
  // for the checks: the layout and the hit test as plain functions
  P.map = { layout: layout, project: project, projectAll: projectAll, shownNotes: shownNotes, hitTest: hitTest,
    labelled: labelled, fit: fit, placeLabels: placeLabels, NAMES_LIMIT: NAMES_LIMIT, FRAME: FRAME };
})();

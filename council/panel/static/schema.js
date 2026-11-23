/* The live schema: the status strip, the thirteen blocks in their lanes, the newest events and, under them,
   either the selected event's journey or the selected block's rules and numbers. New events are asked for every
   two seconds (the pulse); each one plays a single dot along its blocks to the memory ring. */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, t = P.texts, fmt = P.fmt;
  var PULSE_EVERY = 2000;
  var PULSE_PATIENCE = 8000;  // ms a pulse request may take before it is given up
  var LIMIT = 30;  // events in the list
  // the travelling dot: px per second, the shortest hop, its fades, how many at once, how far apart they start,
  // and how many may wait (after a hidden tab comes back, only the newest few play)
  var DOT = { speed: 260, hop: 450, fadeIn: 150, fadeOut: 200, most: 3, apart: 300, waiting: 6, size: 10 };
  var LANES = [
    { id: "start", title: "lane_title_start", sub: "lane_reads" },
    { id: "message", title: "lane_title_message", sub: "lane_reads" },
    { id: "end", title: "lane_title_end", sub: "lane_writes" }
  ];
  var states = new WeakMap();

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }

  // ---------- pure: the list, the selection, the journey ----------

  /* The events of both lists, newest first, each key once, at most ``limit``. An event already in ``list`` keeps
     its place; within one second the new ones come after the known ones, in the order they came. */
  function mergeEvents(list, fresh, limit) {
    var seen = Object.create(null), out = [];
    list.concat(fresh).forEach(function (e) {
      if (!e || seen[e.key]) return;
      seen[e.key] = true;
      out.push(e);
    });
    var order = out.map(function (e, i) { return { e: e, i: i }; });
    order.sort(function (a, b) { return b.e.ts - a.e.ts || a.i - b.i; });
    return order.slice(0, limit).map(function (o) { return o.e; });
  }

  /* Which of ``fresh`` are new: not among the keys ``seen``, each once. The events of the page's opening are
     known from the start and never new. Returns the new events and the known keys after them (a new object). */
  function novel(seen, fresh, opening) {
    var known = Object.create(null), news = [];
    Object.keys(seen).forEach(function (k) { known[k] = true; });
    fresh.forEach(function (e) {
      if (!e || known[e.key]) return;
      known[e.key] = true;
      if (!opening) news.push(e);
    });
    return { news: news, seen: known };
  }

  function inside(p, r, margin) {
    return p.x >= r.left - margin && p.x <= r.right + margin && p.y >= r.top - margin && p.y <= r.bottom + margin;
  }

  /* Whether the dot, its centre at ``p``, is drawn: inside the lanes box's visible rectangle, or anywhere once
     it has passed the end of its lane's line (the vertical line and the ring column do not scroll). A block
     scrolled out of the lanes box never shows a dot over the ring column. */
  function shown(p, lanes, outside) {
    return outside || inside(p, lanes, DOT.size / 2);
  }

  /* The points of a journey along the drawn lines. ``centres`` are the lane blocks' centres in order; a journey
     to the ring then runs along the lane's line to where it meets the vertical line (``geo.lineX``), along that
     line to the ring's height, and into the ring just inside its left edge (``geo.entryX``), clear of its label.
     Stacked (``geo.side`` false, the ring under the lanes): down the lanes' right edge to the column's top line
     (``geo.borderY``), along it to the left of the ring (``geo.leftX``), down to the ring's height and in.
     ``lanePart`` is how many of the points lie in the lanes; the rest are outside them. */
  function wires(centres, endsAtRing, geo) {
    var points = centres.map(function (c) { return { x: c.x, y: c.y }; });
    if (!endsAtRing) return { points: points, lanePart: points.length };
    var entry = { x: geo.entryX, y: geo.ringY };
    if (!points.length) return { points: [entry], lanePart: 0 };
    var y = points[points.length - 1].y, tail;
    if (geo.side) tail = [{ x: geo.lineX, y: y }, { x: geo.lineX, y: geo.ringY }, entry];
    else tail = [{ x: geo.lineX, y: y }, { x: geo.lineX, y: geo.borderY }, { x: geo.leftX, y: geo.borderY },
      { x: geo.leftX, y: geo.ringY }, entry];
    return { points: points.concat(tail), lanePart: points.length };
  }

  /* The share of the whole distance run by the time the dot reaches point ``k``. */
  function offsetAt(points, k) {
    var total = 0, upto = 0;
    for (var i = 1; i < points.length; i++) {
      var d = Math.hypot(points[i].x - points[i - 1].x, points[i].y - points[i - 1].y);
      total += d;
      if (i <= k) upto += d;
    }
    return total > 0 ? upto / total : 0;
  }

  /* While the newest event is selected (or nothing is), the new newest takes the selection. */
  function nextSelection(selectedKey, oldTopKey, newTopKey) {
    return selectedKey === null || selectedKey === undefined || selectedKey === oldTopKey ? newTopKey : selectedKey;
  }

  /* The places of a path in the order they are drawn, the memory ring last: the dot never runs backwards. */
  function route(path, blocks) {
    var rank = Object.create(null);
    blocks.forEach(function (b, i) { rank[b.id] = b.id === "haf" ? blocks.length : i; });
    var seen = Object.create(null);
    return path.filter(function (id) {
      if (!(id in rank) || seen[id]) return false;
      seen[id] = true;
      return true;
    }).sort(function (a, b) { return rank[a] - rank[b]; });
  }

  function hops(points) {
    var out = [];
    points.forEach(function (p) {
      var last = out[out.length - 1];
      if (!last || Math.hypot(p.x - last.x, p.y - last.y) > 0.5) out.push({ x: p.x, y: p.y });
    });
    return out;
  }

  /* Keyframes through the points in order, each offset in proportion to the distance run so far; a point on
     the one before it is left out, so no hop has no length. */
  function journey(points, speed) {
    var pts = hops(points), total = 0, run = [0];
    for (var i = 1; i < pts.length; i++) { total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y); run.push(total); }
    return pts.map(function (p, i) { return { x: p.x, y: p.y, offset: i === 0 ? 0 : i === pts.length - 1 ? 1 : run[i] / total }; });
  }

  /* Milliseconds the journey takes: the distance at ``speed`` px per second, never under DOT.hop a hop; a
     single place is shown for one hop's time. */
  function travelTime(points, speed) {
    var pts = hops(points), total = 0;
    for (var i = 1; i < pts.length; i++) total += Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y);
    return Math.max(Math.round((total / speed) * 1000), DOT.hop * Math.max(1, pts.length - 1));
  }

  function blockOf(data, id) {
    for (var i = 0; i < data.blocks.length; i++) if (data.blocks[i].id === id) return data.blocks[i];
    return { id: id, name: id, sub: "", what: "", rules: [] };
  }

  /* "Hook" is three blocks; where a name is shared, its sub-line tells them apart */
  function label(data, id) {
    var b = blockOf(data, id);
    var shared = data.blocks.filter(function (o) { return o.name === b.name; }).length > 1;
    return shared && b.sub ? b.name + " · " + b.sub : b.name;
  }

  function topKey(s) { return s.events.length ? s.events[0].key : null; }

  function selected(s) {
    var events = s.events;
    if (!events.length) return null;
    for (var i = 0; i < events.length; i++) if (events[i].key === s.selected) return events[i];
    // the selected event left the list: back to the newest, followed
    s.selected = events[0].key;
    s.live = true;
    return events[0];
  }

  // ---------- drawing ----------

  function statusStrip(s) {
    var st = s.data.status, n = s.data.numbers || {};
    function card(title, value, note, key) {
      return el("div", { class: "kart durum-kart", "data-key": key }, [
        el("div", { class: "etiket" }, upper(title)),
        el("div", { class: "deger" }, value),
        note
      ]);
    }
    var backup = st.backup_last_ok ? fmt.date(st.backup_last_ok) + " " + fmt.time(st.backup_last_ok) : t.none;
    var service = st.service || "none", ch = st.check;
    var cards = [
      card(t.status_service, el("span", { class: service === "failed" ? "hata-yazi" : "" }, t["service_" + service])),
      card(t.status_backup, el("span", { class: "mono" }, backup),
        st.backup_failing ? el("div", { class: "not hata-yazi" }, t.status_backup_failing) : null),
      card(t.status_notes, el("span", { class: "mono" }, fmt.number(st.notes))),
      card(t.status_skills, el("span", { class: "mono" }, fmt.number(st.skills)))
    ];
    // the newest check run; before the first run, the saved questions are only counted
    if (ch) {
      cards.push(card(t.status_check, el("span", { class: "mono" }, P.fill(t.status_check_value, {
        auto: fmt.number(ch.auto), search: fmt.number(ch.search), questions: fmt.number(ch.questions) })),
        el("div", { class: "not" }, t.status_check_note)));
    } else {
      cards.push(card(t.status_check, t.none, n.den && n.den.length ? el("div", { class: "not" }, n.den[0]) : null));
    }
    // the panel's version, and the service's when its newest sample named one; a plain sentence when they differ
    if (st.panel_version) {
      var sv = st.service_version, differs = !!sv && sv !== st.panel_version;
      cards.push(card(t.status_version, el("span", { class: "mono" }, P.fill(
        sv ? t.status_version_value : t.status_version_panel, { panel: st.panel_version, service: sv })),
        differs ? el("div", { class: "not hata-yazi" }, t.status_version_differs) : null));
    }
    return el("section", { class: "durum-seridi", "aria-label": t.schema_status }, cards);
  }

  function blockButton(s, b, on, chosen, small) {
    return el("button", {
      type: "button", class: "blok" + (small ? " kucuk" : "") + (on ? " yolda" : "") + (chosen ? " secili" : ""),
      "aria-pressed": chosen ? "true" : "false", "data-key": "blok-" + b.id,
      onclick: function () { pickBlock(s, b.id); }
    }, [el("span", { class: "blok-ad" }, b.name), b.sub ? el("span", { class: "blok-alt" }, b.sub) : null]);
  }

  /* A line between two places of a lane is drawn ink when the event's path runs across it; the memory ring is
     the lane's last place. */
  function line(s, lit, last) {
    return el("span", { class: "hat" + (last ? " son" : "") + (lit ? " etkin" : ""), "aria-hidden": "true" });
  }

  function lanes(s, onPath, chosenBlock, eventMode) {
    var rows = LANES.map(function (lane) {
      var blocks = s.data.blocks.filter(function (b) { return b.lane === lane.id; });
      var places = blocks.map(function (b) { return onPath[b.id] ? 1 : 0; });
      places.push(onPath.haf ? 1 : 0);
      var first = places.indexOf(1), last = places.lastIndexOf(1);
      var row = [];
      blocks.forEach(function (b, i) {
        if (i > 0) row.push(line(s, eventMode && first >= 0 && first < i && i <= last && first !== last, false));
        row.push(blockButton(s, b, onPath[b.id], chosenBlock === b.id, false));
      });
      var n = blocks.length;
      row.push(line(s, eventMode && first >= 0 && first < n && n <= last && first !== last, true));
      return el("div", { class: "serit" }, [
        el("div", { class: "serit-baslik" }, [el("span", { class: "etiket" }, upper(t[lane.title])),
          el("span", { class: "serit-alt" }, t[lane.sub])]),
        el("div", { class: "serit-bloklar" }, row)
      ]);
    });
    return el("div", { class: "seritler", "data-scroll": "seritler" }, rows);
  }

  function memoryColumn(s, onPath, chosenBlock, event) {
    var haf = blockOf(s.data, "haf");
    var state = event && onPath.haf ? (event.memory === "written" ? t.memory_written
      : event.memory === "read" ? t.memory_read : "") : "";
    var ring = el("button", {
      type: "button", class: "halka" + (onPath.haf ? " yolda" : "") + (chosenBlock === "haf" ? " secili" : ""),
      "aria-pressed": chosenBlock === "haf" ? "true" : "false", "data-key": "blok-haf",
      onclick: function () { pickBlock(s, "haf"); }
    }, [
      el("span", { class: "etiket" }, upper(haf.name)),
      el("span", { class: "halka-alt mono" }, P.fill(t.memory_notes, { n: fmt.number(s.data.status.notes) })),
      el("span", { class: "halka-durum" }, state)
    ]);
    return el("div", { class: "hafiza-sutun" }, [ring,
      blockButton(s, blockOf(s.data, "yed"), false, chosenBlock === "yed", true),
      blockButton(s, blockOf(s.data, "den"), false, chosenBlock === "den", true)]);
  }

  function schemaCard(s, event) {
    var eventMode = s.mode === "event" && !!event;
    var onPath = Object.create(null);  // keyed by block ids from the data: no prototype to collide with
    (eventMode ? event.path : [s.block]).forEach(function (id) { onPath[id] = true; });
    var chosenBlock = eventMode ? null : s.block;
    var dot = el("button", {
      type: "button", class: "ikincil anahtar", "aria-pressed": s.dot ? "true" : "false", "data-key": "nokta",
      onclick: function () { s.dot = !s.dot; if (!s.dot) stopDots(s); draw(s); }
    }, s.dot ? t.dot_on : t.dot_off);
    return el("section", { class: "kart sema-kart", "aria-labelledby": "sema-baslik" }, [
      el("div", { class: "kart-ust" }, [
        el("div", {}, [el("h1", { class: "gosterim", id: "sema-baslik" }, upper(t.schema_title)),
          el("p", { class: "on-cumle" }, t.schema_lede)]),
        dot
      ]),
      el("div", { class: "cizim" }, [lanes(s, onPath, chosenBlock, eventMode),
        memoryColumn(s, onPath, chosenBlock, eventMode ? event : null)])
    ]);
  }

  function following(s) { return s.live && s.mode === "event"; }

  function eventsCard(s, event) {
    var on = following(s);
    var live = el("button", {
      type: "button", class: "ikincil anahtar", "aria-pressed": on ? "true" : "false", "data-key": "canli",
      onclick: function () {
        if (on) { s.live = false; draw(s); return; }
        // back to the newest, and follow it from now on
        s.live = true; s.mode = "event"; s.selected = topKey(s);
        draw(s, true);
      }
    }, on ? t.live_on : t.live_off);
    var list = s.events.map(function (e) {
      var key = e.key, chosen = s.mode === "event" && event === e;
      return el("button", {
        type: "button", class: "olay" + (chosen ? " secili" : "") + (s.fresh[key] ? " yeni" : ""),
        "aria-pressed": chosen ? "true" : "false", "data-key": "olay-" + key,
        onclick: function () {
          s.mode = "event"; s.selected = key; s.live = key === topKey(s);
          draw(s);
          if (s.dot) { s.queue.unshift(e); pump(s); }
        }
      }, [el("span", { class: "olay-saat mono" }, fmt.stamp(e.ts)), el("span", { class: "olay-ad" }, e.title)]);
    });
    return el("section", { class: "kart olaylar-kart", "aria-labelledby": "olaylar-baslik" }, [
      el("div", { class: "kart-ust" }, [
        el("div", {}, [el("h2", { class: "gosterim", id: "olaylar-baslik" }, upper(t.events_title)),
          el("p", { class: "on-cumle" }, t.events_lede)]),
        live
      ]),
      list.length ? el("div", { class: "olay-listesi", "data-scroll": "olaylar" }, list) : el("p", { class: "bos" }, t.none)
    ]);
  }

  function journeyCard(s, e) {
    var steps = e.steps.map(function (step, i) {
      return el("li", { class: "adim" }, [
        el("div", { class: "adim-ust" }, [el("span", { class: "sira", "aria-hidden": "true" }, String(i + 1)),
          el("span", { class: "etiket" }, upper(label(s.data, step.block)))]),
        el("p", {}, step.text),
        step.value ? el("div", { class: "deger-kutu mono" }, step.value) : null
      ]);
    });
    return el("section", { class: "kart ayrinti", "aria-labelledby": "ayrinti-baslik" }, [
      el("div", { class: "etiket ikincil-yazi" }, upper(t.journey)),
      el("h2", { class: "ayrinti-baslik", id: "ayrinti-baslik" }, e.title),
      el("p", { class: "mono ikincil-yazi" }, fmt.date(e.ts) + " " + fmt.time(e.ts)),
      el("ol", { class: "adimlar" }, steps)
    ]);
  }

  function blockDetail(s, id) {
    var b = blockOf(s.data, id), numbers = (s.data.numbers || {})[id] || [];
    return el("section", { class: "kart ayrinti", "aria-labelledby": "ayrinti-baslik" }, [
      el("div", { class: "etiket ikincil-yazi" }, upper(t.block)),
      el("h2", { class: "gosterim", id: "ayrinti-baslik" }, upper(label(s.data, id))),
      el("p", { class: "ne-yapar" }, b.what),
      el("div", { class: "iki-sutun" }, [
        el("div", {}, [el("div", { class: "etiket ikincil-yazi" }, upper(t.rules)),
          el("ul", { class: "kurallar" }, b.rules.map(function (r) { return el("li", {}, r); }))]),
        el("div", {}, [el("div", { class: "etiket ikincil-yazi" }, upper(t.numbers)),
          numbers.length ? el("ul", { class: "sayilar" }, numbers.map(function (line) {
            return el("li", { class: "deger-kutu mono" }, line);
          })) : el("p", { class: "bos" }, t.none)])
      ]),
      el("p", { class: "degistir" }, P.fill(t.change_block, { name: label(s.data, id) }))
    ]);
  }

  /* The first row of the list in sight and how far below the list's top edge it is. */
  function anchorOf(list) {
    // at the very top the list stays at the top, so new rows are seen arriving
    if (!list || list.scrollTop <= 0) return null;
    var rows = list.querySelectorAll(".olay");
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].offsetTop + rows[i].offsetHeight > list.scrollTop) {
        return { key: rows[i].getAttribute("data-key"), delta: rows[i].offsetTop - list.scrollTop };
      }
    }
    return null;
  }

  function rowOf(list, key) {
    return list && Array.prototype.find.call(list.querySelectorAll(".olay"), function (r) {
      return r.getAttribute("data-key") === key;
    });
  }

  /* Redraw the section. While the selection follows the newest, ``reveal`` scrolls the list (never the page) to
     the selected row; otherwise the rows in sight stay where they were even when new rows come in above them. */
  function draw(s, reveal) {
    var anchor = following(s) ? null : anchorOf(s.root.querySelector(".olay-listesi"));
    P.rebuild(s.root, function () {
      var event = selected(s);
      if (!event && s.mode === "event") { s.mode = "block"; s.block = s.block || "haf"; }
      // left column: the schema and, under it, the journey or the block; right column: the events
      s.root.appendChild(el("div", { class: "sema" }, [
        statusStrip(s),
        el("div", { class: "sema-ust" }, [
          el("div", { class: "sema-sol" }, [schemaCard(s, event),
            s.mode === "event" && event ? journeyCard(s, event) : blockDetail(s, s.block)]),
          eventsCard(s, event)
        ])
      ]));
    });
    s.fresh = Object.create(null);  // the transition plays once, not on every redrawing
    var list = s.root.querySelector(".olay-listesi");
    var row = anchor && rowOf(list, anchor.key);
    if (row) list.scrollTop = row.offsetTop - anchor.delta;
    else if (reveal && following(s)) showChosen(s);
    // dots in flight live on: back into the new drawing, and the lanes' sideways scroll moves them along
    var box = s.root.querySelector(".cizim"), lanesBox = s.root.querySelector(".seritler");
    if (box) s.dots.forEach(function (d) { box.appendChild(d.node); });
    if (lanesBox) lanesBox.addEventListener("scroll", function () { remeasure(s); }, { passive: true });
  }

  function pickBlock(s, id) { s.live = false; s.mode = "block"; s.block = id; draw(s); }

  /* Fold events into the list. New ones (not seen before, and only after the first drawing) appear with a short
     transition and each queues one dot; the selection follows the newest while it is followed. Returns whether
     the newest event changed. */
  function arrive(s, fresh, base) {
    var oldTop = topKey(s), found = novel(s.seen, fresh, s.first), news = found.news;
    s.events = mergeEvents(base, fresh, LIMIT);
    var newTop = topKey(s);
    if (s.mode === "event" && s.live) s.selected = nextSelection(s.selected, oldTop, newTop);
    if (!s.first) {
      var kept = Object.create(null);
      s.events.forEach(function (e) { kept[e.key] = true; });
      news = news.filter(function (e) { return kept[e.key]; });
      news.forEach(function (e) { s.fresh[e.key] = true; });
      if (s.dot) {
        // oldest first, the way they happened
        s.queue = s.queue.concat(news.slice().sort(function (a, b) { return a.ts - b.ts; })).slice(-DOT.waiting);
      }
    }
    s.first = false;
    // known keys: the list and the dots still waiting, nothing more
    s.seen = Object.create(null);
    s.events.concat(s.queue).forEach(function (e) { s.seen[e.key] = true; });
    return oldTop !== newTop;
  }

  /* The events the pulse brought that a schema answer whose newest event is at ``newest`` may not know yet: those
     of that second too, since the answer may have been read just before a commit in the same second (a repeat
     is dropped by its key when the two are merged). */
  function pulseKept(list, newest) {
    return list.filter(function (e) { return e.ts >= newest; });
  }

  function take(s, data) {
    s.data = data;
    var events = data.events || [], newest = events.length ? events[0].ts : -Infinity;
    // the answer is the list; pulse events of its newest second and later are kept on top of it
    return arrive(s, events, pulseKept(s.events, newest));
  }

  /* The schema shows the selected row by scrolling the list itself, never the page. */
  function showChosen(s) {
    var list = s.root.querySelector(".olay-listesi"), row = list && list.querySelector(".olay.secili");
    if (!row) return;
    var top = row.offsetTop, bottom = top + row.offsetHeight, to = null;
    if (top < list.scrollTop) to = top;
    else if (bottom > list.scrollTop + list.clientHeight) to = bottom - list.clientHeight;
    if (to === null) return;
    if (list.scrollTo) list.scrollTo({ top: to, behavior: P.reducedMotion ? "auto" : "smooth" });
    else list.scrollTop = to;
  }

  // ---------- the pulse ----------

  function pulse(s) {
    clearTimeout(s.pulseTimer);
    if (!s.root.isConnected) return;
    if (s.asking || document.visibilityState !== "visible") { s.pulseTimer = setTimeout(function () { pulse(s); }, PULSE_EVERY); return; }
    s.asking = true;
    // a request that never answers (a phone waking from sleep) is given up, and the next pulse asks again
    var controller = window.AbortController ? new AbortController() : null;
    var giveUp = controller ? setTimeout(function () { controller.abort(); }, PULSE_PATIENCE) : 0;
    P.get("pulse", { query: s.mark === null ? null : { since: s.mark }, signal: controller && controller.signal }).then(function (data) {
      if (!s.root.isConnected) return;
      if (typeof data.mark === "number" && isFinite(data.mark)) s.mark = data.mark;
      var events = Array.isArray(data.events) ? data.events : [];
      // the server repeats the note changes of the mark's second: with nothing new, nothing is redrawn
      if (!novel(s.seen, events, false).news.length) return;
      var moved = arrive(s, events, s.events);
      draw(s, moved);
      pump(s);
    }).catch(function () { /* a missed pulse is asked for again with the same mark */ }).then(function () {
      clearTimeout(giveUp);
      s.asking = false;
      if (s.root.isConnected) s.pulseTimer = setTimeout(function () { pulse(s); }, PULSE_EVERY);
    });
  }

  // ---------- the travelling dot ----------

  function centreIn(node, frame) {
    var r = node && node.getBoundingClientRect();
    if (!r || !r.width || !r.height) return null;
    return { x: r.left - frame.left + r.width / 2, y: r.top - frame.top + r.height / 2 };
  }

  /* An event's journey along the drawn lines, measured now in the coordinates of the drawing box: its points
     and the progress at which it leaves the lanes; null when a place is not drawn (the dot is then not shown at
     all, never at a corner). */
  function measure(s, ids) {
    var box = s.root.querySelector(".cizim"), lanesBox = s.root.querySelector(".seritler");
    var column = s.root.querySelector(".hafiza-sutun"), ring = s.root.querySelector(".halka");
    if (!box || !lanesBox || !column || !ring) return null;
    var frame = box.getBoundingClientRect(), centres = [];
    var lane = ids.filter(function (id) { return id !== "haf"; });
    for (var i = 0; i < lane.length; i++) {
      var c = centreIn(s.root.querySelector('[data-key="blok-' + lane[i] + '"]'), frame);
      if (!c) return null;
      centres.push(c);
    }
    var lanes = lanesBox.getBoundingClientRect(), col = column.getBoundingClientRect(), r = ring.getBoundingClientRect();
    if (!r.width || !col.width) return null;
    var ringStyle = window.getComputedStyle(ring), colStyle = window.getComputedStyle(column);
    var border = parseFloat(ringStyle.borderLeftWidth) || 0, half = DOT.size / 2;
    var side = col.left >= lanes.right - 1;
    var geo = {
      side: side,
      // the vertical line is the column's left border; stacked, the lanes' right edge stands in for it
      lineX: side ? col.left - frame.left + (parseFloat(colStyle.borderLeftWidth) || 0) / 2
        : lanes.right - frame.left - half - 2,
      borderY: col.top - frame.top + (parseFloat(colStyle.borderTopWidth) || 0) / 2,
      leftX: Math.max(half, r.left - frame.left - 16),
      ringY: r.top - frame.top + r.height / 2,
      entryX: r.left - frame.left + border + half + 3
    };
    var w = wires(centres, ids[ids.length - 1] === "haf", geo);
    return { points: w.points, outsideAt: w.lanePart >= w.points.length ? Infinity : offsetAt(w.points, w.lanePart) };
  }

  function frames(points) {
    var f = journey(points, DOT.speed);
    if (f.length === 1) f.push({ x: f[0].x, y: f[0].y, offset: 1 });  // one place: the dot stays there
    var half = DOT.size / 2;
    return f.map(function (k) {
      return { transform: "translate(" + (k.x - half) + "px, " + (k.y - half) + "px)", offset: k.offset };
    });
  }

  function launch(s, e) {
    var box = s.root.querySelector(".cizim");
    if (!box || typeof box.animate !== "function") return false;
    var ids = route(e.path || [], s.data.blocks), m = ids.length ? measure(s, ids) : null;
    if (!m) return false;
    var travel = travelTime(m.points, DOT.speed), total = DOT.fadeIn + travel + DOT.fadeOut;
    var node = el("span", { class: "nokta", "aria-hidden": "true" });
    box.appendChild(node);
    var d = { node: node, ids: ids, outsideAt: m.outsideAt };
    d.move = node.animate(frames(m.points), { duration: travel, delay: DOT.fadeIn, fill: "both", easing: "linear" });
    d.fade = node.animate([
      { opacity: 0, offset: 0 }, { opacity: 1, offset: DOT.fadeIn / total },
      { opacity: 1, offset: (total - DOT.fadeOut) / total }, { opacity: 0, offset: 1 }
    ], { duration: total, fill: "both", easing: "linear" });
    d.fade.onfinish = function () { finish(s, d); };
    s.dots.push(d);
    s.lastStart = Date.now();
    watch(s, d);
    if (!s.frame) s.frame = window.requestAnimationFrame(function () { look(s); });
    return true;
  }

  /* Hide or show one dot for where it is now (CSSOM visibility; its opacity belongs to its fade). */
  function watch(s, d) {
    var lanesBox = s.root.querySelector(".seritler");
    if (!lanesBox) return;
    var r = d.node.getBoundingClientRect(), p = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    var progress = (d.move.effect && d.move.effect.getComputedTiming().progress) || 0;
    var on = shown(p, lanesBox.getBoundingClientRect(), progress >= d.outsideAt - 1e-9);
    d.node.style.visibility = on ? "visible" : "hidden";
  }

  /* Once a frame while dots are in flight. */
  function look(s) {
    s.frame = 0;
    if (!s.dots.length || !s.root.isConnected) return;
    s.dots.forEach(function (d) { watch(s, d); });
    s.frame = window.requestAnimationFrame(function () { look(s); });
  }

  function finish(s, d) {
    var at = s.dots.indexOf(d);
    if (at < 0) return;
    s.dots.splice(at, 1);
    if (d.node.parentNode) d.node.parentNode.removeChild(d.node);
    pump(s);
  }

  /* Start waiting dots: at most DOT.most at once, DOT.apart milliseconds between two starts. */
  function pump(s) {
    clearTimeout(s.pumpTimer);
    if (!s.dot || !s.root.isConnected) { s.queue = []; return; }
    while (s.queue.length && s.dots.length < DOT.most) {
      var wait = s.lastStart + DOT.apart - Date.now();
      if (wait > 0) { s.pumpTimer = setTimeout(function () { pump(s); }, wait); return; }
      launch(s, s.queue.shift());
    }
  }

  /* The switch turned off: nothing waits, and the dots in flight fade out instead of vanishing. */
  function stopDots(s) {
    clearTimeout(s.pumpTimer);
    s.queue = [];
    s.dots.forEach(function (d) {
      if (d.stopping) return;
      d.stopping = true;
      var now = Number(window.getComputedStyle(d.node).opacity) || 0;
      d.fade.onfinish = null;
      d.fade.pause();
      d.move.pause();
      var out = d.node.animate([{ opacity: now }, { opacity: 0 }], { duration: DOT.fadeOut, fill: "forwards" });
      out.onfinish = function () { finish(s, d); };
    });
  }

  /* The lanes scrolled sideways: the dots in flight are measured again, so they stay on their blocks. */
  function remeasure(s) {
    s.dots.forEach(function (d) {
      var m = measure(s, d.ids);
      if (!m || !d.move.effect || !d.move.effect.setKeyframes) return;
      d.move.effect.setKeyframes(frames(m.points));
      d.outsideAt = m.outsideAt;
    });
  }

  function newState(root) {
    return { root: root, data: null, events: [], mode: "event", selected: null, block: "haf", live: true,
      dot: !P.reducedMotion, seen: Object.create(null), fresh: Object.create(null), first: true,
      mark: null, asking: false, pulseTimer: 0, queue: [], dots: [], lastStart: 0, pumpTimer: 0, frame: 0 };
  }

  P.sections.schema = {
    render: function (root, data) {
      var s = newState(root);
      states.set(root, s);
      take(s, data);
      draw(s);
      pulse(s);
    },
    update: function (root, data) {
      var s = states.get(root);
      if (!s) { this.render(root, data); return; }
      var moved = take(s, data);
      draw(s, moved);
      pump(s);
    }
  };
  // for the checks: the list, the selection and the dot's journey as plain functions
  P.schema = { mergeEvents: mergeEvents, nextSelection: nextSelection, route: route, journey: journey,
    travelTime: travelTime, novel: novel, shown: shown, wires: wires, offsetAt: offsetAt, DOT: DOT, LIMIT: LIMIT,
    pulseKept: pulseKept, take: take, arrive: arrive, newState: newState };
})();

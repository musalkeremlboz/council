/* The live schema: the status strip, the thirteen blocks in their lanes, the newest events and, under them,
   either the selected event's journey or the selected block's rules and numbers. */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, t = P.texts, fmt = P.fmt;
  var STEP_EVERY = 4000;
  var LANES = [
    { id: "start", title: "lane_title_start", sub: "lane_reads" },
    { id: "message", title: "lane_title_message", sub: "lane_reads" },
    { id: "end", title: "lane_title_end", sub: "lane_writes" }
  ];
  var states = new WeakMap();

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }
  function eventKey(e) { return [e.ts, e.kind, e.path.join(",")].join("|"); }

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

  function selected(s) {
    var events = s.data.events;
    if (!events.length) return null;
    for (var i = 0; i < events.length; i++) if (eventKey(events[i]) === s.eventKey) return events[i];
    s.eventKey = eventKey(events[0]);
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
    return el("span", { class: "hat" + (last ? " son" : "") + (lit ? " etkin" : ""), "aria-hidden": "true" },
      lit ? el("span", { class: "nokta" + (s.dot ? " akar" : "") }) : null);
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
      onclick: function () { s.dot = !s.dot; draw(s); }
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

  function eventsCard(s, event) {
    var live = el("button", {
      type: "button", class: "ikincil anahtar", "aria-pressed": s.live ? "true" : "false", "data-key": "canli",
      onclick: function () { s.live = !s.live; if (s.live) s.mode = "event"; draw(s); }
    }, s.live ? t.live_on : t.live_off);
    var list = s.data.events.map(function (e) {
      var key = eventKey(e), chosen = s.mode === "event" && event === e;
      return el("button", {
        type: "button", class: "olay" + (chosen ? " secili" : "") + (s.fresh[key] ? " yeni" : ""),
        "aria-pressed": chosen ? "true" : "false", "data-key": "olay-" + key,
        onclick: function () { s.live = false; s.mode = "event"; s.eventKey = key; draw(s); }
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

  function journey(s, e) {
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

  function draw(s) {
    P.rebuild(s.root, function () {
      var event = selected(s);
      if (!event && s.mode === "event") { s.mode = "block"; s.block = s.block || "haf"; }
      // left column: the schema and, under it, the journey or the block; right column: the events
      s.root.appendChild(el("div", { class: "sema" }, [
        statusStrip(s),
        el("div", { class: "sema-ust" }, [
          el("div", { class: "sema-sol" }, [schemaCard(s, event),
            s.mode === "event" && event ? journey(s, event) : blockDetail(s, s.block)]),
          eventsCard(s, event)
        ])
      ]));
    });
    s.fresh = Object.create(null);  // the transition plays once, not on every redrawing
  }

  function pickBlock(s, id) { s.live = false; s.mode = "block"; s.block = id; draw(s); }

  /* Events seen for the first time after the first drawing appear with one short transition. */
  function take(s, data) {
    s.data = data;
    s.fresh = Object.create(null);
    data.events.forEach(function (e) {
      var key = eventKey(e);
      if (!s.seen[key] && !s.first) s.fresh[key] = true;
      s.seen[key] = true;
    });
    s.first = false;
  }

  function step(s) {
    if (!s.root.isConnected) { clearInterval(s.timer); return; }
    if (!s.live || s.mode !== "event" || document.visibilityState !== "visible") return;
    var events = s.data.events;
    if (events.length < 2) return;
    var at = 0;
    for (var i = 0; i < events.length; i++) if (eventKey(events[i]) === s.eventKey) at = i;
    s.eventKey = eventKey(events[(at + 1) % events.length]);
    draw(s);
    showChosen(s);
  }

  /* Live stepping keeps the selected row in sight by scrolling the list itself, never the page. */
  function showChosen(s) {
    var list = s.root.querySelector(".olay-listesi"), row = list && list.querySelector(".olay.secili");
    if (!row) return;
    var top = row.offsetTop, bottom = top + row.offsetHeight;
    if (top < list.scrollTop) list.scrollTop = top;
    else if (bottom > list.scrollTop + list.clientHeight) list.scrollTop = bottom - list.clientHeight;
  }

  P.sections.schema = {
    render: function (root, data) {
      var s = { root: root, data: null, mode: "event", eventKey: null, block: "haf", live: !P.reducedMotion,
        dot: !P.reducedMotion, seen: Object.create(null), fresh: Object.create(null), first: true };
      states.set(root, s);
      take(s, data);
      draw(s);
      s.timer = setInterval(function () { step(s); }, STEP_EVERY);
    },
    update: function (root, data) {
      var s = states.get(root);
      if (!s) { this.render(root, data); return; }
      take(s, data);
      draw(s);
    }
  };
})();

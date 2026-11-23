/* Today: six counters, six lanes over the 24 hours with one mark per event (an overview, not a control), the
   day's sessions as rows that open in place on their events, and three budget rings of equal size (the start of
   a session, the selected event against the message budget, the skill index). */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, svg = P.svg, t = P.texts, fmt = P.fmt;
  var DAY = 1440;
  var R = 54, C = 2 * Math.PI * R, GAP = 3;
  var SIZE = { start: 12, read: 7, search: 9, open: 9, pointer: 9 };
  var OPEN_TIME = 220;  // ms; symmetric easing, so a reversed transition continues from where it was
  var states = new WeakMap();

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }

  function defaultSelection(events) {
    for (var i = events.length - 1; i >= 0; i--) if (events[i].lane === "inject") return i;
    return -1;
  }

  function markSize(e, budget) {
    if (e.lane !== "inject") return SIZE[e.lane] || 8;
    return 6 + Math.round(Math.min(e.chars, budget) / budget * 8);
  }

  // ---------- pure: the sessions ----------

  /* A session is known across refreshes by its whole stored id and its first minute, never by its place in the
     list (two sessions may show the same eight characters). */
  function sessionKey(session) {
    return (session.key !== undefined ? session.key : session.id) + "@" + session.first_minute;
  }

  /* The day's sessions as rows, latest activity first (by last event, then by first event), the events without a
     session last; each with its events (indices
     into data.events, oldest first), their first and last minute, a count per lane and how many hit the limit.
     With limitOnly, only events at the limit count and a session with none left is left out. */
  function sessionRows(data, limitOnly) {
    var rows = (data.sessions || []).map(function (session, index) {
      return { index: index, id: session.id, key: sessionKey(session), first: null, last: null, events: [],
        counts: Object.create(null), atLimit: 0 };
    });
    (data.events || []).forEach(function (e, i) {
      var r = rows[e.session];
      if (!r || (limitOnly && !e.at_limit)) return;
      r.events.push(i);
      if (r.first === null || e.minute < r.first) r.first = e.minute;
      if (r.last === null || e.minute > r.last) r.last = e.minute;
      r.counts[e.lane] = (r.counts[e.lane] || 0) + 1;
      if (e.at_limit) r.atLimit += 1;
    });
    var kept = rows.filter(function (r) { return r.events.length > 0; });
    var sessions = data.sessions || [];
    function last(r) { return sessions[r.index].last_minute; }
    function first(r) { return sessions[r.index].first_minute; }
    function none(r) { return r.id === "" && !sessions[r.index].key; }  // the events without a session
    var named = kept.filter(function (r) { return !none(r); });
    named.sort(function (a, b) { return last(b) - last(a) || first(b) - first(a) || b.index - a.index; });
    return named.concat(kept.filter(none));
  }

  /* The open session's key if that session is still on the list, otherwise null; found by key, so a new session
     drawn above it does not move the opening to another row. */
  function openAfter(data, limitOnly, key) {
    if (key === null || key === undefined) return null;
    return sessionRows(data, limitOnly).some(function (r) { return r.key === key; }) ? key : null;
  }

  // ---------- the counters and the strip ----------

  function counters(s) {
    var d = s.data;
    return el("section", { class: "sayaclar", "aria-label": t.today_counts }, d.lanes.map(function (lane) {
      return el("div", { class: "kart sayac" }, [el("div", { class: "sayac-sayi mono" }, fmt.number(d.counts[lane] || 0)),
        el("div", { class: "sayac-ad" }, t["lane_" + lane])]);
    }));
  }

  // the hour labels under the strip, and their measure: DM Mono at 11px is 0.6em a character
  var HOURS = [0, 360, 720, 1080, 1440], CHAR = 6.6, LABEL_GAP = 4, NAME_COLUMN = 170, AXIS_LEAST = 590;

  /* The hour labels the "now" label would touch on an axis `width` pixels wide: the now label starts at its line
     (plus 4px) and is `nowChars` long; 00:00 starts at the left edge, 24:00 ends at the right, the others are
     centred on their hour. The now line and label always stay; a touched hour label gives way. */
  function hiddenHours(nowMinute, width, nowChars) {
    var hourWidth = 5 * CHAR, n = nowMinute / DAY * width, now = [n, n + LABEL_GAP + nowChars * CHAR];
    return HOURS.filter(function (h) {
      var x = h / DAY * width;
      var label = h === 0 ? [0, hourWidth] : h === DAY ? [width - hourWidth, width] : [x - hourWidth / 2, x + hourWidth / 2];
      return label[0] < now[1] + LABEL_GAP && now[0] < label[1] + LABEL_GAP;
    });
  }

  function strip(s, open) {
    var d = s.data, budget = d.budgets.message.budget, now = d.now_minute / DAY * 100 + "%";
    var bucket = Object.create(null);  // keyed by lane names from the data: no prototype to collide with
    var marks = Object.create(null);
    d.lanes.forEach(function (lane) { marks[lane] = []; });
    d.events.forEach(function (e, i) {
      if (!marks[e.lane]) return;
      var key = e.lane + "-" + Math.floor(e.minute / 4);
      var k = bucket[key] = (bucket[key] || 0) + 1;
      var size = markSize(e, budget), chosen = i === s.selected, session = d.sessions && d.sessions[e.session];
      var other = open !== null && !(session && sessionKey(session) === open);
      // the sessions below are the click targets; a mark only shows where and how much
      marks[e.lane].push(el("span", {
        class: "isaret tur-" + e.lane + (other ? " ote" : "") + (chosen ? " secili" : "") +
          (s.limitOnly && !e.at_limit ? " sonuk" : "") + (i >= s.known ? " yeni" : ""),
        "aria-hidden": "true",
        style: { left: e.minute / DAY * 100 + "%", top: 20 + ((k - 1) % 3 - 1) * 9 + "px", width: size + "px",
          height: size + "px", margin: -size / 2 + "px" }
      }));
    });
    var rows = d.lanes.map(function (lane) {
      return el("div", { class: "satir" }, [
        el("div", { class: "satir-ad" }, t["lane_" + lane]),
        el("div", { class: "iz" }, [el("span", { class: "simdi-cizgi", "aria-hidden": "true", style: { left: now } }),
          marks[lane]])
      ]);
    });
    // the axis is the strip less its name column, never narrower than the strip's least width allows
    var width = Math.max(AXIS_LEAST, (s.root.clientWidth || 0) - 50 - NAME_COLUMN);
    var hidden = hiddenHours(d.now_minute, width, String(t.strip_now || "").length);
    var axis = el("div", { class: "satir eksen", "aria-hidden": "true" }, [el("div", { class: "satir-ad" }),
      el("div", { class: "iz mono" }, HOURS.filter(function (h) { return hidden.indexOf(h) < 0; }).map(function (h) {
        if (h === 0) return el("span", { style: { left: "0%" } }, fmt.minute(h));
        if (h === DAY) return el("span", { class: "sag", style: { right: "0" } }, "24:00");
        return el("span", { class: "orta", style: { left: h / DAY * 100 + "%" } }, fmt.minute(h));
      }).concat([el("span", { class: "simdi-yazi", style: { left: now } }, t.strip_now)]))]);
    var toggle = el("button", {
      type: "button", class: "ikincil anahtar", "aria-pressed": s.limitOnly ? "true" : "false", "data-key": "sinir",
      onclick: function () { s.limitOnly = !s.limitOnly; draw(s); }
    }, P.fill(t.at_limit_toggle, { n: fmt.number(d.at_limit) }));
    return el("section", { class: "kart", "aria-labelledby": "serit-baslik" }, [
      el("div", { class: "kart-ust" }, [
        el("div", {}, [el("h2", { class: "gosterim", id: "serit-baslik" }, upper(t.strip_title)),
          el("p", { class: "on-cumle" }, t.strip_lede)]),
        el("div", { class: "suzgec" }, [toggle, el("p", { class: "tanim" }, t.at_limit_definition)])
      ]),
      el("div", { class: "serit-kutu", "data-scroll": "gun" }, el("div", { class: "serit-ic" }, rows.concat([axis]))),
      d.events.length ? null : el("p", { class: "bos" }, t.none),
      el("div", { class: "aciklama" }, [el("span", {}, t.strip_size),
        el("span", { class: "secili-ornek" }, [el("span", { class: "ornek-nokta", "aria-hidden": "true" }), t.strip_selected]),
        open !== null ? el("span", {}, t.strip_open) : null]),
      sessionList(s, open)
    ]);
  }

  // ---------- the sessions ----------

  function span(first, last) { return first === last ? fmt.minute(first) : fmt.minute(first) + " \u2013 " + fmt.minute(last); }

  function eventTable(s, r, id) {
    var d = s.data;
    return el("div", { class: "oturum-panel", id: id, "data-panel": r.key }, el("div", { class: "olay-tablo" }, [
      el("div", { class: "olay-baslik", "aria-hidden": "true" }, [el("span", {}, t.col_time), el("span", {}, t.col_lane),
        el("span", {}, t.col_chars), el("span", {}, t.col_paths)]),
      el("ol", { class: "oturum-olaylari" }, r.events.map(function (i) {
        var e = d.events[i], chosen = i === s.selected, paths = e.paths || [];
        return el("li", {}, el("button", {
          type: "button", class: "olay-satir" + (chosen ? " secili" : ""), "aria-pressed": chosen ? "true" : "false",
          "data-key": "olay-" + i, onclick: function () { s.selected = i; s.chosen = true; draw(s); }
        }, [
          el("span", { class: "olay-saat mono" }, fmt.minute(e.minute)),
          el("span", { class: "olay-tur" }, t["lane_" + e.lane]),
          el("span", { class: "olay-karakter" }, [el("span", { class: "mono" }, P.fill(t.event_chars, { chars: fmt.number(e.chars) })),
            e.at_limit ? el("span", { class: "olay-sinir" }, t.event_at_limit) : null]),
          // note paths are the owner's own text: always text nodes, one per line
          el("span", { class: "olay-yollar mono" }, paths.length ? paths.map(function (path) {
            return el("span", { class: "olay-yol" }, String(path));
          }) : el("span", { class: "olay-yol bos-yol" }, t.event_no_paths))
        ]));
      }))
    ]));
  }

  function sessionList(s, open) {
    var d = s.data;
    if (!d.events.length) return null;
    var rows = sessionRows(d, s.limitOnly);
    var items = rows.map(function (r) {
      var isOpen = r.key === open, closing = !isOpen && closingOf(s, r.key) !== null;
      var id = "oturum-olaylar-" + r.index;
      var lanes = d.lanes.filter(function (lane) { return r.counts[lane]; }).map(function (lane) {
        return el("span", { class: "oturum-tur" }, P.fill(t.session_lane, { n: fmt.number(r.counts[lane]),
          lane: t["lane_short_" + lane] }));
      });
      var button = el("button", {
        type: "button", class: "oturum-satir", "aria-expanded": isOpen ? "true" : "false", "aria-controls": id,
        "data-key": "oturum-" + r.key, onclick: function () { toggle(s, r.key); }
      }, [
        el("span", { class: "oturum-saat mono" }, span(r.first, r.last)),
        el("span", { class: "oturum-kimlik" + (r.id ? " mono" : "") }, r.id || t.session_none),
        el("span", { class: "oturum-ozet" }, [
          el("span", { class: "oturum-sayi" }, P.fill(t.session_events, { n: fmt.number(r.events.length) })),
          lanes,
          r.atLimit ? el("span", { class: "oturum-sinir" }, P.fill(t.session_at_limit, { n: fmt.number(r.atLimit) })) : null
        ]),
        el("span", { class: "oturum-ok", "aria-hidden": "true", "data-ok": r.key })
      ]);
      return el("li", { class: "oturum" + (isOpen ? " acik" : "") }, [button, isOpen || closing ? eventTable(s, r, id) : null]);
    });
    return el("div", { class: "oturumlar" }, [
      el("h3", { class: "etiket" }, upper(t.sessions_title)),
      el("p", { class: "not" }, t.sessions_lede),
      rows.length ? el("ol", { class: "oturum-listesi" }, items) : el("p", { class: "bos" }, t.sessions_limit_none)
    ]);
  }

  /* One session open at a time; clicking the open one closes it. A transition cut short by another click turns
     round where it is: with a symmetric easing, time t into one direction is time OPEN_TIME - t into the other. */
  function closingOf(s, key) {
    for (var i = 0; i < s.closing.length; i++) if (s.closing[i].key === key) return s.closing[i];
    return null;
  }

  function toggle(s, key) {
    var now = performance.now(), was = s.open;
    function from(tr) { return tr ? now - Math.max(0, OPEN_TIME - (now - tr.start)) : now; }
    var turning = closingOf(s, key);
    s.closing = s.closing.filter(function (tr) { return tr.key !== key && tr.key !== was; });
    if (P.reducedMotion) { s.closing = []; s.opening = null; s.open = was === key ? null : key; draw(s); return; }
    if (was === key) {
      s.closing.push({ key: key, start: from(s.opening && s.opening.key === key ? s.opening : null) });
      s.opening = null;
      s.open = null;
    } else {
      if (was !== null) s.closing.push({ key: was, start: from(s.opening && s.opening.key === was ? s.opening : null) });
      s.opening = { key: key, start: from(turning) };
      s.open = key;
    }
    draw(s);
  }

  function byAttr(root, name, value) {
    return Array.prototype.find.call(root.querySelectorAll("[" + name + "]"), function (n) {
      return n.getAttribute(name) === value;
    }) || null;
  }

  /* Plays (or, after a refresh rebuilt the page mid-way, carries on) the open and close transitions: the panel's
     height is measured and animated, so nothing jumps to height: auto. */
  function motion(s) {
    var now = performance.now();
    (s.opening ? [s.opening] : []).concat(s.closing).forEach(function (tr) {
      var opening = tr === s.opening;
      var panel = byAttr(s.root, "data-panel", tr.key), arrow = byAttr(s.root, "data-ok", tr.key);
      if (!panel || !panel.animate) return;
      var h = panel.scrollHeight, elapsed = Math.min(OPEN_TIME, Math.max(0, now - tr.start));
      var heights = [{ height: "0px", opacity: 0 }, { height: h + "px", opacity: 1 }];
      var turns = [{ transform: "rotate(45deg)" }, { transform: "rotate(225deg)" }];
      var options = { duration: OPEN_TIME, easing: "ease-in-out", fill: opening ? "none" : "forwards" };
      panel.style.overflow = "hidden";
      var a = panel.animate(opening ? heights : heights.slice().reverse(), options);
      a.currentTime = elapsed;
      if (arrow) arrow.animate(opening ? turns : turns.slice().reverse(), options).currentTime = elapsed;
      tr.anim = a;
      a.onfinish = function () {
        if (opening) { panel.style.overflow = ""; if (s.opening === tr) s.opening = null; return; }
        if (s.closing.indexOf(tr) >= 0) { s.closing = s.closing.filter(function (c) { return c !== tr; }); draw(s); }
      };
    });
  }

  // ---------- the rings ----------

  /* slices: [{start, chars}] in characters of the budget; flat gaps of GAP between them */
  function ring(name, budget, used, slices, accent) {
    var arcs = slices.map(function (sl) {
      var from = Math.min(sl.start, budget), len = Math.max(0, Math.min(sl.chars, budget - from));
      var d = Math.max(0, len / budget * C - (slices.length > 1 ? GAP : 0));
      return svg("circle", { cx: 66, cy: 66, r: R, class: accent ? "dilim vurgu" : "dilim",
        "stroke-dasharray": d.toFixed(1) + " " + (C - d).toFixed(1), "stroke-dashoffset": (-(from / budget * C)).toFixed(1) });
    });
    var label = P.fill(t.ring_label, { name: name, budget: fmt.number(budget), used: fmt.number(used) });
    return el("div", { class: "halka-kutu" }, [
      svg("svg", { width: 132, height: 132, viewBox: "0 0 132 132", role: "img", "aria-label": label }, [
        svg("g", { fill: "none", "stroke-width": 14, transform: "rotate(-90 66 66)" },
          [svg("circle", { cx: 66, cy: 66, r: R, class: "zemin-halka" })].concat(arcs))
      ]),
      el("div", { class: "halka-ici" }, [el("span", { class: "halka-sayi mono" }, used === null ? "—" : fmt.number(used)),
        el("span", { class: "halka-butce mono" }, "/ " + fmt.number(budget))])
    ]);
  }

  function startRing(d) {
    var b = d.budgets.start, at = 0, used = 0;
    var slices = b.parts.filter(function (p) { return p.chars > 0; }).map(function (p) {
      var sl = { start: at, chars: p.chars }; at += p.chars; used += p.chars; return sl;
    });
    var left = b.left_out.length ? P.fill(t.left_out, { list: b.left_out.map(function (o) {
      return P.fill(t.left_out_item, { name: o.name, chars: fmt.number(o.chars) });
    }).join(", ") }) : t.left_out_none;
    return el("div", { class: "butce" }, [ring(t.ring_start, b.budget, used, slices, false),
      el("div", { class: "butce-yazi" }, [el("div", { class: "etiket" }, upper(t.ring_start)),
        el("ol", { class: "dilimler mono" }, b.parts.map(function (p) { return el("li", {}, p.name + " · " + fmt.number(p.chars)); })),
        el("p", { class: "not" }, left)])]);
  }

  function selectedRing(s) {
    var d = s.data, b = d.budgets.message, e = s.selected >= 0 ? d.events[s.selected] : null;
    var inject = e && e.lane === "inject";
    var used = inject ? e.chars : null;
    var note = !e ? t.selected_none : !inject ? P.fill(t.selected_other, { chars: fmt.number(e.chars) })
      : !e.chars ? t.selected_empty : e.at_limit ? t.selected_at_limit : t.selected_under;
    return el("div", { class: "butce" }, [
      ring(t.ring_selected, b.budget, used, inject && e.chars ? [{ start: 0, chars: e.chars }] : [], true),
      el("div", { class: "butce-yazi" }, [el("div", { class: "etiket" }, upper(t.ring_selected)),
        e ? el("p", { class: "mono" }, fmt.minute(e.minute) + " · " + t["lane_" + e.lane]) : null,
        el("p", { class: "not" }, note)])]);
  }

  function indexRing(d) {
    var b = d.budgets.index;
    return el("div", { class: "butce" }, [ring(t.ring_index, b.budget, b.chars, b.chars ? [{ start: 0, chars: b.chars }] : [], false),
      el("div", { class: "butce-yazi" }, [el("div", { class: "etiket" }, upper(t.ring_index)),
        el("p", { class: "mono" }, P.fill(t.index_listed, { n: fmt.number(b.listed) })),
        el("p", { class: "not" }, b.left_out ? P.fill(t.index_left, { n: fmt.number(b.left_out) }) : t.index_all)])]);
  }

  function budgets(s) {
    return el("section", { class: "kart", "aria-labelledby": "butce-baslik" }, [
      el("h2", { class: "gosterim", id: "butce-baslik" }, upper(t.budget_title)),
      el("p", { class: "on-cumle" }, t.budget_lede),
      el("div", { class: "halkalar" }, [startRing(s.data), selectedRing(s), indexRing(s.data)])
    ]);
  }

  function draw(s) {
    var d = s.data, now = performance.now();
    if (!s.chosen || s.selected >= d.events.length) { s.selected = defaultSelection(d.events); s.chosen = false; }
    if (s.opening && now - s.opening.start >= OPEN_TIME) s.opening = null;
    s.closing = s.closing.filter(function (tr) { return now - tr.start < OPEN_TIME; });
    // the open session, if it is still on the list (the filter may hide it; it opens again when the filter goes)
    var open = openAfter(d, s.limitOnly, s.open);
    var x = window.scrollX, y = window.scrollY;
    P.rebuild(s.root, function () {
      s.root.appendChild(el("div", { class: "bugun" }, [
        el("div", { class: "baslik-satiri" }, [el("h1", { class: "gosterim buyuk" }, upper(t.today_title)),
          el("p", { class: "on-cumle" }, P.fill(t.today_lede, { date: fmt.date(d.date), now: fmt.minute(d.now_minute) }))]),
        counters(s), strip(s, open), budgets(s)
      ]));
    });
    if (window.scrollX !== x || window.scrollY !== y) window.scrollTo(x, y);
    s.known = d.events.length;  // the transition plays once, for marks that were not there before
    if (!P.reducedMotion) motion(s);
  }

  function take(s, data) {
    if (s.data && s.data.date !== data.date) { s.chosen = false; s.known = 0; s.open = null; s.opening = null; s.closing = []; }
    s.data = data;
  }

  P.sections.today = {
    render: function (root, data) {
      // every mark is "known" at the first drawing: only later arrivals move
      var s = { root: root, data: null, selected: -1, chosen: false, limitOnly: false, known: data.events.length,
        open: null, opening: null, closing: [] };
      states.set(root, s);
      take(s, data);
      draw(s);
    },
    update: function (root, data) {
      var s = states.get(root);
      if (!s) { this.render(root, data); return; }
      take(s, data);
      draw(s);
    }
  };
  // for the checks: the session rows as a plain function
  P.today = { sessionRows: sessionRows, hiddenHours: hiddenHours, openAfter: openAfter };
})();

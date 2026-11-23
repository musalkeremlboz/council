/* Today: six counters, six lanes over the 24 hours with one mark per event, and three budget rings of equal
   size (the start of a session, the selected event against the message budget, the skill index). */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, svg = P.svg, t = P.texts, fmt = P.fmt;
  var DAY = 1440;
  var R = 54, C = 2 * Math.PI * R, GAP = 3;
  var SIZE = { start: 12, read: 7, search: 9, open: 9, pointer: 9 };
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

  // ---------- the counters and the strip ----------

  function counters(s) {
    var d = s.data;
    return el("section", { class: "sayaclar", "aria-label": t.today_counts }, d.lanes.map(function (lane) {
      return el("div", { class: "kart sayac" }, [el("div", { class: "sayac-sayi mono" }, fmt.number(d.counts[lane] || 0)),
        el("div", { class: "sayac-ad" }, t["lane_" + lane])]);
    }));
  }

  function strip(s) {
    var d = s.data, budget = d.budgets.message.budget, now = d.now_minute / DAY * 100 + "%";
    var bucket = Object.create(null);  // keyed by lane names from the data: no prototype to collide with
    var marks = Object.create(null);
    d.lanes.forEach(function (lane) { marks[lane] = []; });
    d.events.forEach(function (e, i) {
      if (!marks[e.lane]) return;
      var key = e.lane + "-" + Math.floor(e.minute / 4);
      var k = bucket[key] = (bucket[key] || 0) + 1;
      var size = markSize(e, budget), chosen = i === s.selected;
      marks[e.lane].push(el("button", {
        type: "button",
        class: "isaret tur-" + e.lane + (chosen ? " secili" : "") + (s.limitOnly && !e.at_limit ? " sonuk" : "") +
          (i >= s.known ? " yeni" : ""),
        "aria-pressed": chosen ? "true" : "false", "data-key": "isaret-" + i,
        "aria-label": P.fill(t.mark_label, { time: fmt.minute(e.minute), lane: t["lane_" + e.lane],
          chars: fmt.number(e.chars) }),
        style: { left: e.minute / DAY * 100 + "%", top: 20 + ((k - 1) % 3 - 1) * 9 + "px", width: size + "px",
          height: size + "px", margin: -size / 2 + "px" },
        onclick: function () { s.selected = i; s.chosen = true; draw(s); }
      }));
    });
    var rows = d.lanes.map(function (lane) {
      return el("div", { class: "satir" }, [
        el("div", { class: "satir-ad" }, t["lane_" + lane]),
        el("div", { class: "iz" }, [el("span", { class: "simdi-cizgi", "aria-hidden": "true", style: { left: now } }),
          marks[lane]])
      ]);
    });
    var axis = el("div", { class: "satir eksen", "aria-hidden": "true" }, [el("div", { class: "satir-ad" }),
      el("div", { class: "iz mono" }, [
        el("span", { style: { left: "0%" } }, "00:00"), el("span", { class: "orta", style: { left: "25%" } }, "06:00"),
        el("span", { class: "orta", style: { left: "50%" } }, "12:00"), el("span", { class: "orta", style: { left: "75%" } }, "18:00"),
        el("span", { class: "sag", style: { right: "0" } }, "24:00"),
        el("span", { class: "simdi-yazi", style: { left: now } }, t.strip_now)
      ])]);
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
        el("span", { class: "secili-ornek" }, [el("span", { class: "ornek-nokta", "aria-hidden": "true" }), t.strip_selected])])
    ]);
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
    var d = s.data;
    if (!s.chosen || s.selected >= d.events.length) { s.selected = defaultSelection(d.events); s.chosen = false; }
    P.rebuild(s.root, function () {
      s.root.appendChild(el("div", { class: "bugun" }, [
        el("div", { class: "baslik-satiri" }, [el("h1", { class: "gosterim buyuk" }, upper(t.today_title)),
          el("p", { class: "on-cumle" }, P.fill(t.today_lede, { date: fmt.date(d.date), now: fmt.minute(d.now_minute) }))]),
        counters(s), strip(s), budgets(s)
      ]));
    });
    s.known = d.events.length;  // the transition plays once, for marks that were not there before
  }

  function take(s, data) {
    if (s.data && s.data.date !== data.date) { s.chosen = false; s.known = 0; }
    s.data = data;
  }

  P.sections.today = {
    render: function (root, data) {
      // every mark is "known" at the first drawing: only later arrivals move
      var s = { root: root, data: null, selected: -1, chosen: false, limitOnly: false, known: data.events.length };
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
})();

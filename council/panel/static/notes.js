/* Notes: the usage ranking (a dot on a line at total / max, then the three counts), the notes never used, and
   the pulse: the last 35 days of changes as a calendar, weeks as columns and weekdays as rows. */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, t = P.texts, fmt = P.fmt;
  var TOP = 18;          // ranking rows shown before "show all"
  var UNUSED_TOP = 36;   // unused notes shown before "show all"
  // the four sizes of a day's circle, by its number of changes; the last step has no upper end
  var STEPS = [{ from: 1, to: 20, size: 10 }, { from: 21, to: 80, size: 16 }, { from: 81, to: 110, size: 22 },
    { from: 111, to: null, size: 28 }];
  var EMPTY = 4;         // a day with no changes, or before the memory's first change, is a 4px dot
  var states = new WeakMap();

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }
  function total(u) { return u.injected + u.read + u.found; }

  /* changes -> the step it falls in; 0 changes -> null */
  function stepOf(changes) {
    if (!changes) return null;
    for (var i = STEPS.length - 1; i >= 0; i--) if (changes >= STEPS[i].from) return STEPS[i];
    return STEPS[0];
  }

  /* "2026-11-22" -> a local date at midnight */
  function day(iso) { var p = iso.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function weekday(d) { return (d.getDay() + 6) % 7; }  // Monday 0 ... Sunday 6
  function short(d) { return fmt.date(isoOf(d)).slice(0, 5); }
  function isoOf(d) {
    var m = d.getMonth() + 1, n = d.getDate();
    return d.getFullYear() + "-" + (m < 10 ? "0" : "") + m + "-" + (n < 10 ? "0" : "") + n;
  }

  /* The calendar as data: one column per Monday-based week that holds one of the days, seven cells each; a cell
     is null outside the window. Days before the memory's first recorded change ("YYYY-MM-DD", or null when it
     has none) are "before"; a quiet day on or after it is a day without changes. */
  function calendar(days, firstChange) {
    var weeks = [];
    days.forEach(function (dd, i) {
      var d = day(dd.date), w = weekday(d);
      if (!weeks.length || w === 0) {
        var monday = new Date(d.getFullYear(), d.getMonth(), d.getDate() - w);
        weeks.push({ monday: monday, cells: [null, null, null, null, null, null, null] });
      }
      weeks[weeks.length - 1].cells[w] = { index: i, data: dd, weekday: w,
        before: !firstChange || dd.date < firstChange, step: stepOf(dd.changes) };
    });
    return weeks;
  }

  // ---------- the ranking ----------

  /* the axis: 0, the middle and the maximum, each a distinct whole number (max 1 -> 0 and 1) */
  function ticks(max) {
    var out = [0];
    [Math.round(max / 2), max].forEach(function (v) { if (v > out[out.length - 1]) out.push(v); });
    return out;
  }

  function more(s, key, count, limit) {
    if (count <= limit) return null;
    return el("button", { type: "button", class: "ikincil", "aria-expanded": s.open[key] ? "true" : "false",
      "data-key": "daha-" + key, onclick: function () { s.open[key] = !s.open[key]; draw(s); } },
      s.open[key] ? t.show_less : t.show_all);
  }

  function rankRow(u, max) {
    var sum = total(u);
    return el("li", { class: "sira-satir" }, [
      el("span", { class: "sira-yol mono", "aria-hidden": "true" }, u.path),
      el("span", { class: "sira-cizgi", "aria-hidden": "true" },
        el("span", { class: "sira-daire", style: { left: (max ? sum / max * 100 : 0) + "%" } })),
      el("span", { class: "sira-sayi mono", "aria-hidden": "true" },
        fmt.number(u.injected) + " · " + fmt.number(u.read) + " · " + fmt.number(u.found)),
      el("span", { class: "gizli" }, P.fill(t.ranking_row, { path: u.path, total: fmt.number(sum),
        injected: fmt.number(u.injected), read: fmt.number(u.read), found: fmt.number(u.found) }))
    ]);
  }

  function ranking(s) {
    var d = s.data, rows = d.ranking, max = rows.length ? total(rows[0]) : 0;
    var shown = s.open.sira ? rows : rows.slice(0, TOP);
    var head = el("div", { class: "sira-baslik", "aria-hidden": "true" }, [
      el("span", { class: "sira-yol" }, t.ranking_note),
      el("span", { class: "sira-eksen mono" }, ticks(max).map(function (v) {
        return el("span", { class: v === 0 ? "sol" : v === max ? "sag" : "orta" }, fmt.number(v));
      })),
      el("span", { class: "sira-sayi" }, t.ranking_counts)
    ]);
    var lede = t.ranking_lede + (d.since ? " " + P.fill(t.ranking_since, { date: fmt.date(d.since) }) : "");
    var unused = s.open.bos ? d.unused : d.unused.slice(0, UNUSED_TOP);
    return el("section", { class: "kart notlar-sira", "aria-labelledby": "sira-baslik" }, [
      el("div", {}, [el("h2", { class: "gosterim", id: "sira-baslik" }, upper(t.ranking_title)),
        el("p", { class: "on-cumle" }, lede)]),
      rows.length ? el("div", { class: "sira-tablo" }, [head, el("ol", { class: "sira-liste" },
        shown.map(function (u) { return rankRow(u, max); }))]) : el("p", { class: "bos" }, t.none),
      rows.length ? el("p", { class: "not" }, rows.length > shown.length
        ? P.fill(t.ranking_shown, { shown: fmt.number(shown.length), n: fmt.number(rows.length) })
        : P.fill(t.ranking_all, { n: fmt.number(rows.length) })) : null,
      more(s, "sira", rows.length, TOP),
      el("p", { class: "not" }, P.fill(t.always_loaded, { list: d.always_loaded.join(", ") })),
      el("div", { class: "kullanilmayan" }, [
        el("div", { class: "kume-baslik" }, [el("h3", { class: "etiket" }, upper(t.unused_title)),
          el("span", { class: "mono" }, P.fill(t.unused_count, { n: fmt.number(d.unused.length), total: fmt.number(d.total) }))]),
        d.unused.length ? el("ul", { class: "kume" }, unused.map(function (p) {
          return el("li", { class: "kume-not mono" }, [el("span", { class: "bos-halka", "aria-hidden": "true" }), p]);
        })) : el("p", { class: "bos" }, t.unused_none),
        more(s, "bos", d.unused.length, UNUSED_TOP),
        el("p", { class: "not" }, t.unused_note)
      ])
    ]);
  }

  // ---------- the pulse ----------

  function dayLabel(cell) {
    var d = day(cell.data.date);
    return { date: fmt.date(cell.data.date), weekday: t.weekdays[weekday(d)] };
  }

  function dot(size, kind) {
    return el("span", { class: "gun-daire " + kind, "aria-hidden": "true", style: { width: size + "px", height: size + "px" } });
  }

  function cellOf(s, cell) {
    if (!cell) return el("span", { class: "gun bos-gun", "aria-hidden": "true" });
    if (cell.before) return el("span", { class: "gun", role: "img", "aria-label": P.fill(t.pulse_day, dayLabel(cell)) + ": " + t.pulse_before }, dot(EMPTY, "once"));
    var chosen = cell.index === s.day;
    var name = dayLabel(cell);
    name.changes = fmt.number(cell.data.changes);
    return el("button", {
      type: "button", class: "gun" + (chosen ? " secili" : ""), "aria-pressed": chosen ? "true" : "false",
      "aria-label": P.fill(t.pulse_day_label, name), "data-key": "gun-" + cell.data.date,
      onclick: function () { s.day = cell.index; s.chosenDate = cell.data.date; draw(s); }
    }, dot(cell.step ? cell.step.size : EMPTY, cell.step ? "dolu" : "sessiz"));
  }

  function pulse(s) {
    var d = s.data, weeks = calendar(d.days, d.first_change), last = d.days.length - 1;
    var sum = d.days.reduce(function (a, x) { return { changes: a.changes + x.changes, added: a.added + x.added }; },
      { changes: 0, added: 0 });
    var columns = "44px repeat(" + weeks.length + ", minmax(0, 48px))";
    var header = el("div", { class: "takvim-satir takvim-ust mono", "aria-hidden": "true", style: { gridTemplateColumns: columns } },
      [el("span")].concat(weeks.map(function (w, i) {
        return el("span", { class: i === weeks.length - 1 ? "bu-hafta" : "" }, short(w.monday));
      })));
    var rows = [0, 1, 2, 3, 4, 5, 6].map(function (r) {
      return el("div", { class: "takvim-satir", style: { gridTemplateColumns: columns } },
        [el("span", { class: "gun-ad", "aria-hidden": "true" }, t.weekdays_short[r])].concat(weeks.map(function (w) {
          return cellOf(s, w.cells[r]);
        })));
    });
    var chosen = d.days[s.day] || d.days[last];
    var label = chosen ? dayLabel({ data: chosen }) : null;
    var legend = el("div", { class: "aciklama" }, [
      el("span", { class: "ornek" }, [dot(EMPTY, "once"), t.pulse_before]),
      el("span", { class: "ornek" }, [dot(EMPTY, "sessiz"), t.pulse_quiet])
    ].concat(STEPS.map(function (st) {
      return el("span", { class: "ornek" }, [dot(st.size, "dolu"), st.to === null
        ? P.fill(t.pulse_step_last, { from: fmt.number(st.from) })
        : P.fill(t.pulse_step, { from: fmt.number(st.from), to: fmt.number(st.to) })]);
    })));
    return el("section", { class: "kart notlar-nabiz", "aria-labelledby": "nabiz-baslik" }, [
      el("div", {}, [el("h2", { class: "gosterim", id: "nabiz-baslik" }, upper(t.pulse_title)),
        el("p", { class: "on-cumle" }, t.pulse_lede)]),
      el("p", { class: "mono nabiz-ozet" }, P.fill(t.pulse_sum, { days: fmt.number(d.days.length),
        changes: fmt.number(sum.changes), added: fmt.number(sum.added) })),
      el("div", { class: "takvim" }, [header].concat(rows)),
      legend,
      chosen ? el("div", { class: "gun-ayrinti", "aria-live": "polite" }, [
        el("div", { class: "gun-ayrinti-ad" }, [el("span", { class: "ornek-nokta", "aria-hidden": "true" }),
          el("strong", {}, P.fill(t.pulse_day, label))]),
        el("p", { class: "mono" }, P.fill(t.pulse_counts, { changes: fmt.number(chosen.changes),
          notes: fmt.number(chosen.notes), added: fmt.number(chosen.added) }))
      ]) : null
    ]);
  }

  function draw(s) {
    var d = s.data;
    // the chosen day is kept by its date; when it leaves the window, today is chosen
    s.day = d.days.length - 1;
    for (var i = 0; i < d.days.length; i++) if (d.days[i].date === s.chosenDate) s.day = i;
    P.rebuild(s.root, function () {
      s.root.appendChild(el("div", { class: "notlar" }, [
        el("div", { class: "baslik-satiri" }, [el("h1", { class: "gosterim buyuk" }, upper(t.notes_title)),
          el("p", { class: "on-cumle" }, P.fill(t.notes_lede, { n: fmt.number(d.total) }))]),
        el("div", { class: "notlar-ic" }, [ranking(s), pulse(s)])
      ]));
    });
  }

  P.sections.notes = {
    render: function (root, data) {
      var s = { root: root, data: data, day: -1, chosenDate: null, open: Object.create(null) };
      states.set(root, s);
      draw(s);
    },
    update: function (root, data) {
      var s = states.get(root);
      if (!s) { this.render(root, data); return; }
      s.data = data;
      draw(s);
    }
  };
  // for the checks: the calendar and the size steps as plain data
  P.notes = { calendar: calendar, stepOf: stepOf, ticks: ticks };
})();

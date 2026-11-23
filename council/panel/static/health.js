/* Health: one sentence on the state now, the last 30 days with one mark per component and day (filled circle
   full, half circle partial, flat bar failed, empty outline no record), and the grid of the saved questions over
   the newest check runs, by number only. */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, t = P.texts, fmt = P.fmt;
  var ROWS = ["service", "backup", "updates"];
  var STATES = ["full", "partial", "failed", "none"];

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }
  function short(date) { return fmt.date(date).slice(0, 5); }

  // ---------- the state now ----------

  function sentence(d) {
    var s = d.summary, ran = d.runs.length > 0;
    var ok = s.service === "full" && s.backup !== "failed" && s.updates !== "failed" &&
      (!ran || s.both === s.questions);
    var parts = [t["health_service_" + s.service], t["health_backup_" + s.backup]];
    if (s.updates === "failed") parts.push(t.health_updates_failed);
    parts.push(ran ? P.fill(t.health_check, { questions: fmt.number(s.questions), both: fmt.number(s.both) })
      : t.health_check_none);
    return el("p", { class: "saglik-cumle" }, [
      el("span", { class: ok ? "durum-iyi" : "durum-kotu hata-yazi" }, ok ? t.health_ok : t.health_attention),
      " " + parts.filter(Boolean).join(" ")
    ]);
  }

  // ---------- the history ----------

  function mark(state, label) {
    return el("span", { class: "gun-izi " + state, role: "img", "aria-label": label });
  }

  function legend() {
    return el("ul", { class: "lejant" }, STATES.map(function (state) {
      return el("li", {}, [el("span", { class: "gun-izi " + state, "aria-hidden": "true" }), t["legend_" + state]]);
    }));
  }

  function history(d) {
    var days = d.days;
    var rows = ROWS.filter(function (row) { return days.some(function (day) { return day[row] !== "none"; }); });
    var first = -1;
    for (var i = 0; i < days.length && first < 0; i++) {
      if (ROWS.some(function (row) { return days[i][row] !== "none"; })) first = i;
    }
    var head = el("div", {}, [el("h2", { class: "gosterim", id: "gecmis-baslik" }, upper(t.history_title)),
      el("p", { class: "on-cumle" }, t.history_lede)]);
    if (!rows.length) {
      return el("section", { class: "kart", "aria-labelledby": "gecmis-baslik" }, [
        el("div", { class: "kart-ust" }, head), el("p", { class: "bos" }, t.history_empty),
        el("p", { class: "not" }, t.history_rule)]);
    }
    var columns = { gridTemplateColumns: "repeat(" + days.length + ", minmax(0, 1fr))" };
    var lines = rows.map(function (row) {
      return el("div", { class: "gecmis-satir" }, [
        el("div", { class: "gecmis-ad" }, [el("span", { class: "gecmis-ad-ust" }, t["row_" + row]),
          el("span", { class: "not" }, t["row_" + row + "_sub"])]),
        el("div", { class: "gecmis-gunler", style: columns }, days.map(function (day) {
          return el("span", { class: "gun-kutu" }, mark(day[row], P.fill(t.day_label, {
            date: fmt.date(day.date), row: t["row_" + row], state: t["state_" + day[row]] })));
        }))
      ]);
    });
    var last = days.length - 1;
    var axis = el("div", { class: "gecmis-satir eksen-satir", "aria-hidden": "true" }, [el("div", { class: "gecmis-ad" }),
      el("div", { class: "gecmis-gunler mono", style: columns }, [
        first > 0 ? el("span", { class: "eksen-bas", style: { gridColumn: "1" } }, short(days[0].date)) : null,
        first === last ? null : el("span", { class: "eksen-ilk", style: { gridColumn: String(first + 1) } },
          t.history_first_tick),
        el("span", { class: "eksen-son", style: { gridColumn: String(last + 1) } }, t.history_today)
      ])]);
    return el("section", { class: "kart", "aria-labelledby": "gecmis-baslik" }, [
      el("div", { class: "kart-ust" }, head),
      el("div", { class: "gecmis-kutu", "data-scroll": "gecmis" },
        el("div", { class: "gecmis-ic" }, lines.concat([axis]))),
      legend(),
      el("p", { class: "gecmis-not" }, [P.fill(t.history_first, { date: fmt.date(days[first].date) }) + " ",
        el("span", { class: "ikincil-yazi" }, t.history_rule)])
    ]);
  }

  // ---------- the grid of questions ----------

  function measured(list) {
    var n = 0, yes = 0;
    list.forEach(function (v) { if (v !== null && v !== undefined) { n++; if (v) yes++; } });
    return { n: n, yes: yes };
  }

  function cell(value, label) {
    if (value === null || value === undefined) return el("span", { class: "izgara-hucre", "aria-hidden": "true" });
    return el("span", { class: "izgara-hucre" },
      el("span", { class: "izgara-isaret " + (value ? "buldu" : "kacirdi"), role: "img", "aria-label": label }));
  }

  function grid(d) {
    var runs = d.runs;
    var head = [el("h2", { class: "gosterim", id: "izgara-baslik" }, upper(t.grid_title)),
      el("p", { class: "on-cumle" }, t.grid_lede)];
    if (!runs.length) {
      return el("section", { class: "kart", "aria-labelledby": "izgara-baslik" },
        [el("div", { class: "kart-ust" }, el("div", {}, head)), el("p", { class: "bos" }, t.grid_empty),
          el("p", { class: "not" }, t.grid_rule)]);
    }
    var n = runs.length, count = 0;
    runs.forEach(function (r) { count = Math.max(count, r.auto.length, r.search.length); });
    var groups = [{ key: "auto", name: t.grid_auto }, { key: "search", name: t.grid_search }];
    var cells = [];
    function row(label, perRun) {
      cells.push(el("span", { class: "izgara-ad" }, label));
      groups.forEach(function (g, gi) {
        if (gi) cells.push(el("span", { class: "izgara-ara", "aria-hidden": "true" }));
        runs.forEach(function (r, ri) { cells.push(perRun(g, r, ri)); });
      });
    }
    // group titles
    cells.push(el("span", { class: "izgara-ad" }));
    groups.forEach(function (g, gi) {
      if (gi) cells.push(el("span", { class: "izgara-ara", "aria-hidden": "true" }));
      cells.push(el("span", { class: "etiket izgara-grup", style: { gridColumn: "span " + n } }, upper(g.name)));
    });
    row("", function (g, r, ri) {
      var day = fmt.date(r.ts), before = ri > 0 ? fmt.date(runs[ri - 1].ts) : "";
      return el("span", { class: "izgara-zaman mono" }, [day !== before ? el("span", { class: "izgara-gun" }, day.slice(0, 5)) : null,
        el("span", {}, fmt.time(r.ts))]);
    });
    row("", function (g, r) {
      var m = measured(r[g.key]);
      return el("span", { class: "izgara-toplam mono" }, P.fill(t.grid_total, { n: m.yes, total: m.n }));
    });
    var missing = Object.create(null);
    d.missing.forEach(function (q) { missing[q] = true; });
    for (var q = 0; q < count; q++) {
      (function (q) {
        var label = P.fill(t.grid_question, { n: q + 1 });
        row([missing[q + 1] ? el("span", { class: "kacan", "aria-hidden": "true" }) : null,
          el("span", { class: "mono" }, label)], function (g, r) {
          return cell(r[g.key][q], P.fill(t.grid_cell, { n: q + 1, when: fmt.date(r.ts) + " " + fmt.time(r.ts),
            group: g.name, result: r[g.key][q] ? t.grid_found : t.grid_missed }));
        });
      })(q);
    }
    var table = el("div", { class: "izgara", style: {
      gridTemplateColumns: "88px repeat(" + n + ", 44px) 24px repeat(" + n + ", 44px)" } }, cells);
    var list = d.missing.map(function (q) { return P.fill(t.grid_question, { n: q }); });
    return el("section", { class: "kart", "aria-labelledby": "izgara-baslik" }, [
      el("div", { class: "kart-ust" }, el("div", {}, head)),
      el("div", { class: "izgara-kutu", "data-scroll": "izgara" }, table),
      el("ul", { class: "lejant" }, [
        el("li", {}, [el("span", { class: "izgara-isaret buldu", "aria-hidden": "true" }), t.grid_legend_found]),
        el("li", {}, [el("span", { class: "izgara-isaret kacirdi", "aria-hidden": "true" }), t.grid_legend_missed]),
        el("li", {}, t.grid_legend_gone),  // the grid leaves such a cell empty: no swatch
        el("li", {}, [el("span", { class: "kacan", "aria-hidden": "true" }), t.grid_legend_missing])
      ]),
      el("div", { class: "kacanlar" }, [
        el("p", { class: list.length ? "kacan-liste" : "" }, list.length ? P.fill(t.missing_list, { list: list.join(", ") })
          : t.missing_none),
        el("p", { class: "not" }, t.grid_rule)])
    ]);
  }

  function draw(root, d) {
    P.rebuild(root, function () {
      root.appendChild(el("div", { class: "saglik" }, [
        el("div", { class: "saglik-ust" }, [el("h1", { class: "gosterim buyuk" }, upper(t.health_title)), sentence(d)]),
        history(d), grid(d)
      ]));
    });
  }

  P.sections.health = {
    render: function (root, data) { draw(root, data); },
    update: function (root, data) { draw(root, data); }
  };
})();

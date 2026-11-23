/* Releases: the six-part ring (the memory's own part in the accent, a part being measured dashed ink, waiting
   parts hairline), the version cards newest first and the numbered list of what comes next. */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, svg = P.svg, t = P.texts, fmt = P.fmt;
  var R = 70, C = 2 * Math.PI * R, GAP = 8, DASH = 6, SPACE = 4;
  var STATE = { pending: "state_pending", released: "state_released", first: "state_first" };
  var PART = { full: "ring_full", measured: "ring_measured", waiting: "ring_waiting" };
  var states = new WeakMap();

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }
  function lower(text) { return String(text).toLocaleLowerCase("tr-TR"); }

  /* a dash pattern that draws `length` as short dashes and then leaves the rest of the circle empty */
  function dashed(length) {
    var out = [], at = 0;
    while (at + DASH < length) { out.push(DASH, SPACE); at += DASH + SPACE; }
    out.push(Math.max(0, length - at), C - length);
    return out.map(function (v) { return v.toFixed(1); }).join(" ");
  }

  /* part i of n -> its class: the first part is the memory itself */
  function partClass(part, i) {
    if (part.state === "full") return i === 0 ? "parca vurgu" : "parca dolu";
    if (part.state === "measured") return "parca olculuyor";
    return "parca bekliyor";
  }

  function ring(parts) {
    var n = parts.length, each = C / n, len = Math.max(0, each - GAP);
    var full = parts.filter(function (p) { return p.state === "full"; }).length;
    var arcs = parts.map(function (p, i) {
      return svg("circle", { cx: 88, cy: 88, r: R, class: partClass(p, i),
        "stroke-dasharray": p.state === "measured" ? dashed(len) : len.toFixed(1) + " " + (C - len).toFixed(1),
        transform: "rotate(" + (i * 360 / n).toFixed(2) + " 88 88)" });
    });
    return el("div", { class: "halka-buyuk" }, [
      svg("svg", { width: 176, height: 176, viewBox: "0 0 176 176", role: "img",
        "aria-label": P.fill(t.ring_aria, { n: fmt.number(full), total: fmt.number(n) }) },
        [svg("g", { fill: "none", "stroke-width": 18, transform: "rotate(" + (-90 + GAP / 2 / C * 360).toFixed(2) + " 88 88)" }, arcs)]),
      el("div", { class: "halka-ici", "aria-hidden": "true" }, [
        el("span", { class: "gosterim" }, P.fill(t.ring_count, { n: fmt.number(full), total: fmt.number(n) })),
        el("span", { class: "not" }, t.ring_count_label)])
    ]);
  }

  /* The parts as lines; neighbouring waiting parts without a name are one line ("3 - 6"). */
  function partLines(parts) {
    var lines = [];
    parts.forEach(function (p, i) {
      var prev = lines[lines.length - 1];
      if (!p.name && p.state === "waiting" && prev && prev.unnamed) { prev.to = p.n; return; }
      lines.push({ from: p.n, to: p.n, name: p.name, state: p.state, unnamed: !p.name && p.state === "waiting",
        cls: partClass(p, i) });
    });
    return el("ul", { class: "parcalar" }, lines.map(function (l) {
      var title = l.unnamed ? (l.from === l.to ? String(l.from) : P.fill(t.ring_parts, { from: l.from, to: l.to }))
        : P.fill(t.ring_part, { n: l.from, name: l.name || "" });
      return el("li", {}, [el("span", { class: "parca-ornek " + l.cls.replace("parca ", ""), "aria-hidden": "true" }),
        el("span", {}, [el("strong", {}, title), " — " + (l.unnamed ? t.ring_unnamed : t[PART[l.state]] || l.state)])]);
    }));
  }

  function ringCard(d) {
    return el("section", { class: "kart halka-kart", "aria-labelledby": "halka-baslik" }, [
      ring(d.ring),
      el("div", { class: "halka-yazi" }, [
        el("h2", { class: "gosterim", id: "halka-baslik" }, upper(t.ring_title)),
        el("p", { class: "on-cumle" }, t.ring_lede),
        partLines(d.ring)])
    ]);
  }

  function version(v) {
    var badge = t[STATE[v.state]] || v.state;
    return el("article", { class: "kart surum" }, [
      el("div", { class: "surum-sol" }, [
        el("h3", { class: "gosterim surum-no" }, v.version),
        el("span", { class: "rozet" + (v.state === "pending" ? " bekliyor" : "") }, badge),
        lower(v.date) === lower(badge) ? null : el("span", { class: "mono not" }, v.date)
      ]),
      el("div", { class: "surum-sag" }, [
        el("p", { class: "surum-ozet" }, v.summary),
        el("ul", { class: "eklenenler" }, v.added.map(function (a) { return el("li", {}, a); }))
      ])
    ]);
  }

  /* "0.10.0" after "0.9.1": newest first, whatever order the file keeps */
  function newestFirst(versions) {
    function parts(v) { return String(v.version).split(".").map(function (x) { return parseInt(x, 10) || 0; }); }
    return versions.slice().sort(function (a, b) {
      var x = parts(a), y = parts(b);
      for (var i = 0; i < Math.max(x.length, y.length); i++) if ((x[i] || 0) !== (y[i] || 0)) return (y[i] || 0) - (x[i] || 0);
      return 0;
    });
  }

  function nextList(items) {
    return el("ol", { class: "siradakiler" }, items.map(function (item, i) {
      return el("li", { class: "kart siradaki" }, [
        el("span", { class: "sira-no", "aria-hidden": "true" }, String(i + 1)),
        el("span", { class: "siradaki-yazi" }, [el("strong", {}, item.title),
          el("span", { class: "ikincil-yazi" }, item.text), el("span", { class: "mono not" }, item.waits_for)])
      ]);
    }));
  }

  function draw(s) {
    var d = s.data;
    P.rebuild(s.root, function () {
      s.root.appendChild(el("div", { class: "guncellemeler" }, [
        el("h1", { class: "gosterim buyuk" }, upper(t.releases_title)),
        ringCard(d),
        el("div", { class: "guncellemeler-ic" }, [
          el("section", { class: "surumler", "aria-labelledby": "surum-baslik" }, [
            el("h2", { class: "gosterim", id: "surum-baslik" }, upper(t.versions_title))].concat(newestFirst(d.versions).map(version))),
          el("section", { class: "siradakiler-kutu", "aria-labelledby": "sira-baslik" }, [
            el("h2", { class: "gosterim", id: "sira-baslik" }, upper(t.next_title)), nextList(d.next)])
        ])
      ]));
    });
  }

  P.sections.releases = {
    render: function (root, data) { var s = { root: root, data: data }; states.set(root, s); draw(s); },
    update: function (root, data) {
      var s = states.get(root);
      if (!s) { this.render(root, data); return; }
      s.data = data;
      draw(s);
    }
  };
})();

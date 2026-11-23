/* The shell of the panel: one section at a time, chosen by the address fragment, refreshed every five seconds
   while the tab is visible. Section files register themselves in Panel.sections under their API name and only
   ever build the page with createElement and textContent. Every word shown comes from Panel.texts. */
(function () {
  "use strict";

  var body = document.body;
  var base = body.getAttribute("data-base") || "";
  var texts = {};
  try { texts = JSON.parse(body.getAttribute("data-texts") || "{}"); } catch (e) { texts = {}; }

  var SVG_NS = "http" + "://www.w3.org/2000/svg";
  var EVERY = 5000;
  // fragment -> the section's API name (also its key in Panel.sections)
  var ROUTES = { sema: "schema", bugun: "today", saglik: "health", harita: "map", notlar: "notes",
    guncellemeler: "releases" };
  var FIRST = "sema";

  function SignedOut() { this.name = "SignedOut"; }

  function append(node, children) {
    if (children === null || children === undefined || children === false) return;
    if (Array.isArray(children)) { children.forEach(function (c) { append(node, c); }); return; }
    node.appendChild(typeof children === "object" ? children : document.createTextNode(String(children)));
  }

  function build(node, attrs, children) {
    Object.keys(attrs || {}).forEach(function (key) {
      var value = attrs[key];
      if (value === null || value === undefined || value === false) return;
      if (key === "text") node.textContent = String(value);
      else if (key === "style") Object.keys(value).forEach(function (k) { node.style[k] = value[k]; });
      else if (key.slice(0, 2) === "on" && typeof value === "function") node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : String(value));
    });
    append(node, children);
    return node;
  }

  /* el("button", {class: "x", onclick: fn, style: {left: "3%"}}, ["text", child]) */
  function el(tag, attrs, children) { return build(document.createElement(tag), attrs, children); }
  function svg(tag, attrs, children) { return build(document.createElementNS(SVG_NS, tag), attrs, children); }

  /* "{n} not" with {n: 3} -> "3 not"; a missing value leaves the placeholder empty */
  function fill(template, values) {
    return String(template === undefined ? "" : template).replace(/\{(\w+)\}/g, function (_, k) {
      return values && values[k] !== undefined ? String(values[k]) : "";
    });
  }

  function two(n) { return (n < 10 ? "0" : "") + n; }
  var fmt = {
    /* 9000 -> "9.000", the way the code's own rules are written */
    number: function (n) {
      var s = String(Math.round(Math.abs(Number(n) || 0))).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
      return (Number(n) < 0 ? "-" : "") + s;
    },
    /* seconds since the epoch -> "18:49" */
    time: function (ts) { var d = new Date(ts * 1000); return two(d.getHours()) + ":" + two(d.getMinutes()); },
    /* "2026-11-22" or seconds since the epoch -> "22.11.2026" */
    date: function (value) {
      if (typeof value === "string") { var p = value.split("-"); return p[2] + "." + p[1] + "." + p[0]; }
      var d = new Date(value * 1000);
      return two(d.getDate()) + "." + two(d.getMonth() + 1) + "." + d.getFullYear();
    },
    /* minute of the day -> "06:05" */
    minute: function (m) { return two(Math.floor(m / 60)) + ":" + two(m % 60); },
    /* today's moments by their time, older ones with their day in front */
    stamp: function (ts) {
      var d = new Date(ts * 1000), now = new Date();
      var day = d.toDateString() === now.toDateString() ? "" : two(d.getDate()) + "." + two(d.getMonth() + 1) + " ";
      return day + fmt.time(ts);
    }
  };

  function get(section, options) {
    return fetch(base + "/api/" + encodeURIComponent(section), {
      credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" },
      signal: options && options.signal
    }).then(function (r) {
      if (r.status === 401) { window.location.assign(base + "/login"); throw new SignedOut(); }
      if (!r.ok) throw new Error("status " + r.status);
      return r.json();
    }).then(function (data) {
      if (!data || data.error) throw new Error((data && data.error) || "empty");
      return data;
    });
  }

  /* Rebuild a section's box without losing the keyboard focus or the scroll of its lanes and lists: elements
     that should survive carry data-key (focus) or data-scroll (both scroll positions). */
  function rebuild(root, draw) {
    var active = document.activeElement;
    var key = active && root.contains(active) ? active.getAttribute("data-key") : null;
    var scrolls = {};
    Array.prototype.forEach.call(root.querySelectorAll("[data-scroll]"), function (n) {
      scrolls[n.getAttribute("data-scroll")] = [n.scrollLeft, n.scrollTop];
    });
    while (root.firstChild) root.removeChild(root.firstChild);
    draw();
    Array.prototype.forEach.call(root.querySelectorAll("[data-scroll]"), function (n) {
      var was = scrolls[n.getAttribute("data-scroll")];
      if (was) { n.scrollLeft = was[0]; n.scrollTop = was[1]; }
    });
    if (key) {
      var again = Array.prototype.find.call(root.querySelectorAll("[data-key]"), function (n) {
        return n.getAttribute("data-key") === key;
      });
      if (again) again.focus({ preventScroll: true });
    }
  }

  var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var Panel = window.Panel = {
    base: base, texts: texts, get: get, el: el, svg: svg, fill: fill, fmt: fmt, rebuild: rebuild,
    reducedMotion: reduced, sections: {}
  };

  // ---------- the shell ----------

  var main, status, current = null;

  function say(text) { if (status) status.textContent = text || ""; }

  function routeOf() {
    var fragment = window.location.hash.replace(/^#/, "");
    return ROUTES[fragment] ? fragment : FIRST;
  }

  function markNav(route) {
    Array.prototype.forEach.call(document.querySelectorAll(".ust nav a"), function (a) {
      if (a.getAttribute("href") === "#" + route) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    });
  }

  function leave() {
    if (!current) return;
    clearTimeout(current.timer);
    if (current.controller) current.controller.abort();
    current = null;
  }

  function schedule(view) {
    clearTimeout(view.timer);
    if (view === current && document.visibilityState === "visible") view.timer = setTimeout(function () { poll(view); }, EVERY);
  }

  function poll(view) {
    if (view !== current || view.busy || document.visibilityState !== "visible") return;
    clearTimeout(view.timer);
    view.busy = true;
    view.controller = window.AbortController ? new AbortController() : null;
    get(view.name, { signal: view.controller && view.controller.signal }).then(function (data) {
      if (view !== current) return;
      say("");
      var json = JSON.stringify(data);
      if (json === view.json) return;
      try {
        if (!view.drawn) {
          while (view.box.firstChild) view.box.removeChild(view.box.firstChild);
          view.section.render(view.box, data);
          view.drawn = true;
        } else {
          view.section.update(view.box, data);
        }
        view.json = json;  // only a drawing that worked counts; a failed one is tried again next time
      } catch (drawing) {
        // a fault in the page, not the connection: keep the last drawing; with none yet, say the section is
        // unavailable instead of loading for ever (the next answer tries the first drawing again)
        if (window.console) console.error(drawing);
        if (!view.drawn) {
          while (view.box.firstChild) view.box.removeChild(view.box.firstChild);
          view.box.appendChild(el("p", { class: "yer-tutucu" }, texts.unavailable));
        }
      }
    }).catch(function (error) {
      if (view !== current || error instanceof SignedOut || (error && error.name === "AbortError")) return;
      // keep the last data; say so quietly
      say(texts.offline);
      if (!view.drawn) {
        while (view.box.firstChild) view.box.removeChild(view.box.firstChild);
        view.box.appendChild(el("p", { class: "yer-tutucu" }, texts.unavailable));
      }
    }).then(function () {
      view.busy = false;
      schedule(view);
    });
  }

  function show() {
    var route = routeOf();
    markNav(route);
    leave();
    say("");
    while (main.firstChild) main.removeChild(main.firstChild);
    var box = el("div", { class: "bolum-ic" });
    main.appendChild(box);
    var name = ROUTES[route], section = Panel.sections[name];
    if (!section) {
      box.appendChild(el("p", { class: "yer-tutucu" }, texts.placeholder));
      return;
    }
    box.appendChild(el("p", { class: "yer-tutucu" }, texts.loading));
    current = { name: name, section: section, box: box, json: null, drawn: false, busy: false, timer: 0 };
    poll(current);
  }

  var started = false;
  function start() {
    if (started) return;
    started = true;
    main = document.getElementById("bolum");
    status = document.getElementById("baglanti");
    if (!main) return;
    window.addEventListener("hashchange", show);
    document.addEventListener("visibilitychange", function () {
      if (!current) return;
      if (document.visibilityState === "visible") poll(current);
      else clearTimeout(current.timer);
    });
    show();
  }

  // The section files are deferred scripts that run after this one; DOMContentLoaded fires after all of them.
  if (document.readyState === "complete") start();
  else { document.addEventListener("DOMContentLoaded", start); window.addEventListener("load", start); }
})();

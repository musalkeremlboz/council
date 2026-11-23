/* The theme, chosen before the first paint: the one script in <head>, before the stylesheet, on both pages.
   A stored "light" or "dark" is set on <html data-theme>; with nothing stored the system decides through the
   stylesheet's prefers-color-scheme block. The choice lives in this browser only. Storage may be refused (a
   private window, blocked site data): the choice then holds for the page's life. Every change, by the owner or
   by the system or in another tab, is announced with a "council-theme" event so drawings that read the tokens paint again. */
(function () {
  "use strict";

  var KEY = "council-panel-theme";
  var EVENT = "council-theme";
  var root = typeof document !== "undefined" ? document.documentElement : null;
  var kept = null;  // the choice of this page: read from storage once, then whatever the owner chose last

  /* a stored value -> "light" | "dark" | null (null: follow the system) */
  function resolveTheme(stored) { return stored === "light" || stored === "dark" ? stored : null; }

  function storage() { try { return window.localStorage || null; } catch (e) { return null; } }

  function read() {
    var s = storage();
    if (s) { try { return resolveTheme(s.getItem(KEY)); } catch (e) { /* refused: the system's */ } }
    return null;
  }

  function apply(theme) {
    if (!root) return;
    if (theme) root.setAttribute("data-theme", theme); else root.removeAttribute("data-theme");
  }

  function announce() {
    if (typeof window.dispatchEvent !== "function" || typeof Event !== "function") return;
    window.dispatchEvent(new Event(EVENT));
  }

  /* "system" | "light" | "dark" */
  function get() { return kept || "system"; }

  function set(value) {
    var theme = resolveTheme(value), s = storage();
    kept = theme;
    if (s) {
      try { if (theme) s.setItem(KEY, theme); else s.removeItem(KEY); } catch (e) { /* the kept choice holds */ }
    }
    apply(theme);
    announce();
  }

  kept = read();
  apply(kept);

  // the system's own change matters while nothing is chosen; the drawings are told either way
  var query = typeof window.matchMedia === "function" ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  if (query) {
    if (query.addEventListener) query.addEventListener("change", announce);
    else if (query.addListener) query.addListener(announce);
  }

  // a choice made in another tab of this browser reaches this one through the storage event
  if (typeof window.addEventListener === "function") {
    window.addEventListener("storage", function (e) {
      if (e.key !== KEY && e.key !== null) return;  // null: the whole storage was cleared
      kept = read();
      apply(kept);
      announce();
    });
  }

  window.PanelTheme = { get: get, set: set, resolveTheme: resolveTheme, EVENT: EVENT };
})();

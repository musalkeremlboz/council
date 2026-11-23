/* Settings: a column of cards. The theme: three choices side by side (system, light, dark), the chosen one
   pressed; a click applies it at once through window.PanelTheme (theme.js), which keeps it in this browser. The
   password: a real form (so password managers know it) posted with Panel.post; the typed passwords are read from
   the fields when it is sent and kept nowhere else. The sessions: how many are open, when this one ends, and closing
   the others after a second, in-place yes. The shell asks /api/settings for the sessions; when that answer fails the
   cards are drawn without it (drawsWithout), and the theme works as before. */
(function () {
  "use strict";

  var P = window.Panel, el = P.el, t = P.texts;
  var CHOICES = [["system", t.theme_system], ["light", t.theme_light], ["dark", t.theme_dark]];
  var shown = [];  // the buttons drawn last; a change from elsewhere (another tab, the system) moves their press

  // ---------- pure: what the form may send, what an answer means ----------

  /* characters as the server counts them (code points), not UTF-16 units */
  function chars(text) { return Array.from(String(text || "")).length; }

  /* "empty" | "short" | "long" | "mismatch" | "ready" */
  function passwordState(current, next, repeat, min, max) {
    if (!next) return "empty";
    var n = chars(next);
    if (n < min) return "short";
    if (n > max) return "long";
    if (next !== repeat) return "mismatch";
    return current ? "ready" : "empty";
  }

  /* an answer of POST /api/password -> the line to show (a key of the texts), the count it names, which fields to
     empty ("all" when the attempt ended, "current" after a wrong current password, "none" for a correctable one) */
  function passwordAnswer(status, body) {
    var error = body && body.error;
    if (status === 200 && body && body.ok === true) {
      var n = Math.max(0, Number(body.closed) || 0);
      return { key: n > 0 ? "password_ok" : "password_ok_alone", n: n, clear: "all", done: true };
    }
    if (error === "wrong") return { key: "password_wrong", n: 0, clear: "current", done: false };
    if (error === "weak") return { key: "password_weak", n: 0, clear: "none", done: false };
    if (error === "same") return { key: "password_same", n: 0, clear: "none", done: false };
    if (error === "locked") return { key: "password_locked", n: 0, clear: "all", done: false };
    return { key: "password_failed", n: 0, clear: "none", done: false };
  }

  // ---------- drawing ----------

  var info = null;          // the last settings answer: {sessions, expires, min_length}
  var sessionsBox = null;   // the body of the sessions card, redrawn on every answer
  var confirming = false;   // the close button asked once and waits for its yes
  var closing = false;
  var sessionsLine = null;  // {text, bad} under the sessions buttons

  function upper(text) { return String(text).toLocaleUpperCase("tr-TR"); }

  function minLength() { return (info && info.min_length) || t.password_min || 10; }
  function maxLength() { return t.password_max || 200; }

  /* a template with its {values} in the mono face */
  function monoFill(template, values) {
    return String(template || "").split(/(\{\w+\})/).filter(Boolean).map(function (part) {
      var m = /^\{(\w+)\}$/.exec(part);
      return m ? el("span", { class: "mono" }, values[m[1]] === undefined ? "" : String(values[m[1]])) : part;
    });
  }

  function mark() {
    var theme = window.PanelTheme, now = theme ? theme.get() : null;
    shown.forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-theme-choice") === now ? "true" : "false");
    });
  }

  function card(id, title, lede, body) {
    return el("section", { class: "kart ayar-kart", "aria-labelledby": id }, [
      el("h2", { class: "gosterim", id: id }, upper(title)),
      el("p", { class: "on-cumle" }, lede)
    ].concat(body));
  }

  function themeCard() {
    var theme = window.PanelTheme;
    var buttons = shown = CHOICES.map(function (c) {
      return el("button", { type: "button", class: "secenek", "data-theme-choice": c[0], "data-key": "tema-" + c[0],
        onclick: function () { theme.set(c[0]); mark(); } }, c[1]);
    });
    var body = theme
      ? [el("div", { class: "secenekler", role: "group", "aria-label": t.theme_group }, buttons),
        el("p", { class: "not" }, t.theme_kept)]
      : [el("p", { class: "yer-tutucu" }, t.unavailable)];
    if (theme) mark();
    return card("tema-baslik", t.theme_title, t.theme_lede, body);
  }

  function field(input, label) {
    return el("div", { class: "alan-grup" }, [el("label", { for: input.id }, label), input]);
  }

  function passwordCard() {
    var sending = false;
    var current = el("input", { id: "sifre-simdiki", name: "current-password", type: "password",
      autocomplete: "current-password", class: "alan", "data-key": "sifre-simdiki", oninput: check });
    var next = el("input", { id: "sifre-yeni", name: "new-password", type: "password",
      autocomplete: "new-password", class: "alan", "data-key": "sifre-yeni", oninput: check });
    var repeat = el("input", { id: "sifre-tekrar", name: "new-password-repeat", type: "password",
      autocomplete: "new-password", class: "alan", "data-key": "sifre-tekrar", oninput: check });
    var submit = el("button", { type: "submit", "data-key": "sifre-gonder", disabled: true }, t.password_submit);
    var line = el("p", { class: "cevap", role: "status", "aria-live": "polite" });

    function say(text, bad) {
      line.textContent = text || "";
      if (bad) line.classList.add("kotu"); else line.classList.remove("kotu");
    }

    function state() { return passwordState(current.value, next.value, repeat.value, minLength(), maxLength()); }

    function check() {
      var now = state();
      submit.disabled = sending || now !== "ready";
      if (sending) return;
      // a hint while typing, only for what the owner can see is off: a repeat that differs, a new one too long
      if (now === "mismatch" && repeat.value) say(t.password_mismatch, true);
      else if (now === "long") say(t.password_weak, true);
      else say("", false);
    }

    function send(event) {
      event.preventDefault();
      if (sending || state() !== "ready") return;
      sending = true;
      submit.disabled = true;
      submit.textContent = t.password_working;
      say("", false);
      P.post("password", { current: current.value, new: next.value }).then(function (answer) {
        return passwordAnswer(answer.status, answer.data);
      }, function (error) {
        if (error && error.name === "SignedOut") throw error;
        return passwordAnswer(0, null);
      }).then(function (a) {
        if (a.clear === "all") { current.value = ""; next.value = ""; repeat.value = ""; }
        else if (a.clear === "current") { current.value = ""; current.focus(); }
        var text = a.done ? P.fill(t[a.key], { n: a.n }) + " " + t.password_remind : P.fill(t[a.key], { n: a.n });
        sending = false;
        check();
        say(text, !a.done);
        if (a.done && info) {
          info = { sessions: Math.max(1, info.sessions - a.n), expires: info.expires, min_length: info.min_length };
          drawSessions();
        }
      }).catch(function () { sending = false; }).then(function () {
        submit.textContent = t.password_submit;
        submit.disabled = sending || state() !== "ready";
      });
    }

    var form = el("form", { class: "sifre-form", method: "post", action: "#", novalidate: true, onsubmit: send }, [
      field(current, t.password_current), field(next, t.password_new), field(repeat, t.password_repeat),
      el("p", { class: "not" }, t.password_rule),
      el("div", { class: "dugmeler" }, [submit]),
      line
    ]);
    return card("sifre-baslik", t.password_title, t.password_lede, [
      el("p", { class: "sifre-claude" }, t.password_claude),
      form
    ]);
  }

  function focusKey(key) {
    if (!sessionsBox) return;
    var target = sessionsBox.querySelector('[data-key="' + key + '"]');
    if (target) target.focus();
  }

  function closeOthers() {
    if (closing) return;
    closing = true;
    drawSessions();
    P.post("sessions/close-others", {}).then(function (answer) {
      var n = answer.status === 200 && answer.data && typeof answer.data.closed === "number" ? answer.data.closed : null;
      if (n === null) sessionsLine = { text: t.open_sessions_failed, bad: true };
      else {
        sessionsLine = { text: n > 0 ? P.fill(t.open_sessions_closed, { n: n }) : t.open_sessions_none_closed, bad: false };
        if (info) info = { sessions: Math.max(1, info.sessions - n), expires: info.expires, min_length: info.min_length };
      }
    }, function (error) {
      if (error && error.name === "SignedOut") throw error;
      sessionsLine = { text: t.open_sessions_failed, bad: true };
    }).catch(function () { /* signed out: the page is leaving */ }).then(function () {
      closing = false;
      confirming = false;
      drawSessions();
      focusKey("oturum-kapat");
    });
  }

  function drawSessions() {
    if (!sessionsBox) return;
    P.rebuild(sessionsBox, function () {
      var facts = info
        ? [el("p", { class: "acik-oturum-sayi" }, monoFill(t.open_sessions_count, { n: P.fmt.number(info.sessions) })),
          el("p", { class: "on-cumle" }, monoFill(t.open_sessions_ends, { time: P.fmt.stamp(info.expires) }))]
        : [el("p", { class: "yer-tutucu" }, t.open_sessions_unknown)];
      var buttons = confirming
        ? [el("button", { type: "button", "data-key": "oturum-onay", disabled: closing, onclick: closeOthers },
            t.open_sessions_confirm),
          el("button", { type: "button", class: "ikincil", "data-key": "oturum-vazgec", disabled: closing,
            onclick: function () { confirming = false; drawSessions(); focusKey("oturum-kapat"); } }, t.open_sessions_cancel)]
        : [el("button", { type: "button", class: "ikincil", "data-key": "oturum-kapat",
            onclick: function () { confirming = true; sessionsLine = null; drawSessions(); focusKey("oturum-onay"); } },
            t.open_sessions_close)];
      sessionsBox.appendChild(el("div", { class: "oturum-bilgi" }, facts));
      sessionsBox.appendChild(el("div", { class: "dugmeler" }, buttons));
      sessionsBox.appendChild(el("p", { class: "cevap" + (sessionsLine && sessionsLine.bad ? " kotu" : ""),
        role: "status", "aria-live": "polite" }, sessionsLine ? sessionsLine.text : ""));
    });
  }

  function sessionsCard() {
    sessionsBox = el("div", { class: "oturum-kutu" });
    drawSessions();
    return card("oturum-baslik", t.open_sessions_title, t.open_sessions_lede, [sessionsBox]);
  }

  function render(root, data) {
    info = data && typeof data.sessions === "number" ? data : null;
    confirming = false;
    closing = false;
    sessionsLine = null;
    P.rebuild(root, function () {
      root.appendChild(el("div", { class: "ayarlar" }, [
        el("div", {}, [el("h1", { class: "gosterim buyuk" }, upper(t.settings_title)),
          el("p", { class: "on-cumle" }, t.settings_lede)]),
        themeCard(),
        passwordCard(),
        sessionsCard()
      ]));
    });
  }

  if (window.PanelTheme && window.addEventListener) window.addEventListener(window.PanelTheme.EVENT, mark);

  P.sections.settings = {
    drawsWithout: true,
    render: render,
    // a later answer touches the sessions card only: the password fields and what is typed in them stay
    update: function (root, data) {
      info = data && typeof data.sessions === "number" ? data : info;
      drawSessions();
    }
  };
  P.settings = { passwordState: passwordState, passwordAnswer: passwordAnswer };
})();

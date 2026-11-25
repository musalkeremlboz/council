# COUNCIL Design System 0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the COUNCIL design system 0.2 under `brand/` as the single source: tokens, generated CSS variables, the Tek Kesik component set, Council Halka 0.2 with lowercase, three reusable motion scenes, an icon set, the emblem family helper, a living example page, a Turkish brand book, and the claude.ai design-system page generated from it.

**Architecture:** `brand/tokens.json` holds every value (in the list shape the claude.ai Design System page reads). `brand/build.py` turns it into `brand/css/tokens.css` and checks contrast. `brand/css/council.css` holds base styles and all components, using only `var(--…)`. `brand/font/build_font.py` records each glyph's primitives and writes `glifler.json`, which the "Kendini kuran yazı" scene draws from. The scenes are small ES modules under `brand/js/sahne/` that share `ortak.js` (reduced-motion, visibility and frame-loop guards). `brand/ornek/index.html` shows everything; `brand/denetle.py` checks it in headless Chrome.

**Tech Stack:** Python 3.11+ and pytest (existing). fontTools, skia-pathops and brotli only for the font tasks (local venv, never a project dependency; those tests `importorskip`). Vanilla JS ES modules, tested with `node --test`. HTML/CSS/SVG. No external libraries, no bundler, no network fonts.

**Spec:** `docs/tasarim/2026-11-26-tasarim-sistemi.md` (approved 2026-11-26). Reference prototypes: `docs/tasarim/2026-11-26-tasarim-sistemi-ekler/` (starting points only; port, do not copy wholesale).

**Branch:** work on `tasarim-sistemi`, cut from `main`. Commit after every task. Do not push.

**Font venv (font tasks only):**
```bash
python3 -m venv ~/.cache/council-brand-venv
~/.cache/council-brand-venv/bin/pip install fonttools skia-pathops brotli pytest
```

## Global Constraints

- Single source: every color, size, spacing, radius and motion value lives in `brand/tokens.json`; no hex literal outside `tokens.json` and the generated `tokens.css` (SVG logo files excepted).
- Corners: only `0`, full circle (`999px`/`50%`), or the 45° cut. No `box-shadow`, no `linear-gradient`/`radial-gradient`/`conic-gradient`, no other `border-radius` values.
- Tek Kesik: `k = h × 2/7`; sizes 44px/k12px, 32px/k9px (fine pointer only; becomes 44/12 under `(pointer:coarse)`), 56px/k16px. Clickable ⇒ cut; not clickable ⇒ no cut.
- Kor (`#E8421F`) is one thing per screen. Text on kor is `kor-ustu` (`#111416`), never white.
- Contrast: text ≥ 4.5:1 in both themes; ≥ 3:1 for text ≥ 24px, control borders, focus ring.
- Touch targets ≥ 44px. Focus always visible. `prefers-reduced-motion` gives a static, complete equivalent. `forced-colors` falls back to a plain border. Without JS everything shows in its final state (hiding only under the `.js` root class).
- Motion: durations 70 / 140 / 240 / 420 ms, scene transition ≤ 840 ms, identity moment ≤ 1.8 s with first-screen text readable within 1.2 s; easings `cubic-bezier(.2,0,0,1)` (open/in) and `cubic-bezier(.4,0,1,1)` (close/out), linear for rotation. No infinite loops; zero frames while idle; scroll-driven scene ≤ 450vh with a skip link; each scene file ≤ 15 KB.
- Only halka, kesik and dalga move. No scale, bounce, shadow, zoom, glow.
- Fonts load from local files (`brand/font/`), never Google Fonts.
- Content: no AI-tool product names (Claude, Hermes, Antigravity, ChatGPT, Codex, Gemini) and no personal information anywhere under `brand/`. Examples are generic ("toplantı kararı", "proje notu").
- Council Halka uppercase glyphs, digits and existing punctuation do not change; `brand/logo/*.svg` regenerate byte-identical.
- Panel (`council/panel/`) is not touched; `pytest -q` stays green.
- Turkish copy in UI and brand book; code identifiers may be Turkish, kept short.

## Review Focus

1. **A long Turkish label on a phone** ("Hafızayı bu cihaza bağla" at 375px): the button grows in height, the cut stays a clean 45° at the top-right, nothing overflows horizontally. Pinned in Task 2 (example markup) and Task 11 (overflow check).
2. **Turkish casing**: `İ/i` and `I/ı` map to the right glyphs in Halka 0.2, and uppercase styles render "i" as "İ" (pages carry `lang="tr"`). Pinned in Task 5.
3. **Reduced motion switched on while the page is open**: running scenes snap to their static state at once. Pinned in Task 7 (`azaltmaIzle`).
4. **A scene off screen or in a background tab**: no frames are drawn, the scroll listener is detached. Pinned in Task 7 (`cizimDongusu`, `gorunurlukBekcisi`).
5. **JavaScript blocked or failing**: logo, headings and scenes show in their final state. Pinned in Task 3 (CSS lint: hiding rules only under `.js`) and Task 8.

---

## File Structure

```
brand/
  README.md                 brand book (Turkish)                          Task 12
  tokens.json               all values, Design System list shape          Task 1
  build.py                  tokens.json → css/tokens.css, contrast check  Task 1
  css/tokens.css            GENERATED                                      Task 1
  css/council.css           base + all components                          Tasks 2–4
  font/build_font.py        Halka 0.2 + glifler.json                       Tasks 5–6
  font/CouncilHalka.{ttf,woff2}, font/glifler.json   GENERATED             Tasks 5–6
  font/DMSans.ttf, DMMono-*.ttf, OFL-*.txt  copied from council/panel/static/fonts  Task 1
  logo/amblem.py            emblem family helper                           Task 9
  logo/build_logo.py        uses amblem.py; output unchanged               Task 9
  simge/build_simge.py, simge/*.svg                                        Task 10
  js/package.json           {"type":"module"}                              Task 7
  js/sahne/ortak.js         shared guards                                  Task 7
  js/sahne/yazi-kur.js      "Kendini kuran yazı"                           Task 8
  js/sahne/cizgi-soz.js     "Çizgi ve söz"                                 Task 8
  js/sahne/kurul-turu.js    "Kurul turu"                                   Task 8
  js/ozellikler.json        the six parts' state                           Task 8
  ornek/index.html          living example page                            Task 11
  denetle.py                headless Chrome checks                         Task 11
  tasarim_sayfasi.py        writes the claude.ai Design System files       Task 13
tests/
  test_brand_tokens.py, test_brand_css.py, test_brand_font.py, test_brand_logo.py,
  test_brand_simge.py, test_brand_js.py, test_brand_ornek.py, test_brand_icerik.py,
  test_brand_tasarim_sayfasi.py
  js/brand_sahne.test.mjs
  fixtures/halka-0.1-buyuk.json   0.1 outlines snapshot                    Task 5
```

---

### Task 1: Tokens and generated CSS variables

**Files:**
- Create: `brand/tokens.json`, `brand/build.py`, `brand/css/tokens.css` (generated), `tests/test_brand_tokens.py`
- Copy: `council/panel/static/fonts/{DMSans.ttf,DMMono-Regular.ttf,DMMono-Medium.ttf,OFL-DMSans.txt,OFL-DMMono.txt}` → `brand/font/`

**Interfaces:**
- Produces: `brand/build.py` functions `load_tokens(path: Path) -> dict`, `contrast(fg: str, bg: str) -> float` (WCAG 2.x relative-luminance ratio, hex in), `contrast_failures(tokens: dict) -> list[str]`, `css_from_tokens(tokens: dict) -> str`, `main() -> int` (writes `brand/css/tokens.css`, returns 1 if `contrast_failures` is non-empty). Constant `CONTRAST_PAIRS: list[tuple[str, str, float]]` (fg token, bg token, minimum).
- Produces CSS custom properties used by every later task: `--<color-name>` for every color token (e.g. `--zemin`, `--kor-ustu`, `--murekkep-bas`, `--pasif-zemin`, `--ton`), `--ara-1 … --ara-16`, `--kose-0`, `--kose-tam`, `--sure-bas`, `--sure-tepki`, `--sure-panel`, `--sure-sahne`, `--sure-gecis-en-cok`, `--egri-ac`, `--egri-kapa`, `--font-display`, `--font-sans`, `--font-mono`, and one class per text style `.yazi-<name>` (e.g. `.yazi-baslik-xl`).
- Theme switching in `tokens.css`: light on `:root`; dark under `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {…} }` and again under `:root[data-theme="dark"]`. Line 1 is exactly `/* COUNCIL — generated from tokens.json */`.

- [ ] **Step 1: Write the failing tests** in `tests/test_brand_tokens.py`:
  - `test_every_family_is_a_token_list`: `color`, `spacing`, `radius`, `motion` each have `{"tokens": [...]}`, every entry has `name`, `value`, `usage`; `color.themes == [{"id":"light",…},{"id":"dark",…}]`; names unique across families.
  - `test_spec_values`: `kor` light/dark `#E8421F`; `kor-ustu` `#111416`; `murekkep-bas` `{"light":"#2E3438","dark":"#D3D7D2"}`; `kor-bas` `#F25A38`; `pasif-zemin` `{"light":"#E2E4E1","dark":"#23282B"}`; `pasif-yazi` `{"light":"#5B6166","dark":"#9AA0A4"}`; `ton` `{"light":"rgb(17 20 22 / .07)","dark":"rgb(244 245 243 / .08)"}`; radius names exactly `{"kose-0","kose-tam"}`; spacing `ara-1…ara-16` = 4,8,12,16,24,32,48,64 px; motion `sure-bas 70ms`, `sure-tepki 140ms`, `sure-panel 240ms`, `sure-sahne 420ms`, `sure-gecis-en-cok 840ms`, `egri-ac cubic-bezier(.2,0,0,1)`, `egri-kapa cubic-bezier(.4,0,1,1)`; the 15 colors of 0.1 with the values in the spec's second color table.
  - `test_text_styles`: `type.groups` contains the 8 styles of the spec's type table with those exact sizes, line heights, weights and letter spacing; `type.fonts` lists `fonts/CouncilHalka.woff2`, `fonts/DMSans.ttf`, `fonts/DMMono-Regular.ttf`.
  - `test_contrast_function`: `round(contrast("#111416", "#F4F5F3"), 1) >= 17.0`; `contrast("#FFFFFF", "#E8421F") < 4.5`; `contrast("#111416", "#E8421F") >= 4.5`.
  - `test_no_contrast_failures`: `contrast_failures(load_tokens(...)) == []`, with `CONTRAST_PAIRS` covering at least: murekkep, murekkep-2, murekkep-3, kor-metin, basari, uyari, hata on zemin and on yuzey (4.5); kor-ustu on kor and on kor-bas (4.5); pasif-yazi on pasif-zemin (4.5); cizgi-guclu on zemin (3.0).
  - `test_generated_css_is_current`: `css_from_tokens(load_tokens(...)) == (brand/css/tokens.css).read_text()`; first line as above; contains `:root[data-theme="dark"]`.

- [ ] **Step 2: Run** `python -m pytest tests/test_brand_tokens.py -q` → FAIL (files missing).
- [ ] **Step 3: Write `brand/tokens.json`** (values from the spec; `usage` text in Turkish, from the spec and 0.1) **and implement `brand/build.py`**. `rgb(… / a)` values are skipped by the contrast check (they are fills, not text pairs).
- [ ] **Step 4: Run** `python brand/build.py && python -m pytest tests/test_brand_tokens.py -q` → PASS.
- [ ] **Step 5: Copy the DM fonts** (with their OFL texts) into `brand/font/`.
- [ ] **Step 6: Commit** `feat(brand): tokens.json as single source, generated tokens.css, contrast check`.

### Task 2: Base styles and the Tek Kesik button

**Files:**
- Create: `brand/css/council.css`, `tests/test_brand_css.py`
- Reference: `docs/tasarim/2026-11-26-tasarim-sistemi-ekler/dugme-tek-kesik.css`

**Interfaces:**
- Consumes: Task 1 variables.
- Produces classes: `.c-dugme` (primary), modifiers `.c-dugme--kor`, `--ikincil`, `--hayalet`, `--k` (small), `--b` (large); child `.c-dugme__halka` (busy spinner); states `:disabled`/`[aria-disabled="true"]`, `[aria-busy="true"]`, `[data-durum="hafizada"]`. CSS custom properties on the button: `--h`, `--k0`, `--k` (registered with `@property --k { syntax: "<length>"; inherits: true; initial-value: 12px }`). `@font-face` rules for "Council Halka", "DM Sans", "DM Mono" pointing to `../font/…`.

- [ ] **Step 1: Write the failing tests** in `tests/test_brand_css.py` (plain text checks over `council.css`, helper `rules(css) -> list[tuple[selector, body]]`):
  - `test_no_forbidden_decoration`: no `box-shadow`, no `-gradient(`, no hex color literal, no `rgb(`/`hsl(` literal.
  - `test_only_allowed_radii`: every `border-radius` value ∈ {`0`, `50%`, `var(--kose-0)`, `var(--kose-tam)`}.
  - `test_button_sizes`: `.c-dugme` sets `--h:44px` and `--k0:12px`; `.c-dugme--k` `--h:32px;--k0:9px`; `.c-dugme--b` `--h:56px;--k0:16px`; a `@media (pointer:coarse)` block resets `.c-dugme--k` to `--h:44px;--k0:12px`; `min-width:96px`.
  - `test_button_motion`: hover rule is inside `@media (hover:hover)` and sets `--k: calc(var(--k0) + 4px)`; `:active` sets `--k: calc(var(--k0) - 4px)` with `var(--sure-bas)`; the transition uses `var(--sure-tepki)` and `var(--egri-ac)`; disabled sets `--k:0px`.
  - `test_focus_and_fallbacks`: `:focus-visible` uses `var(--kor-metin)`; a `@media (forced-colors: active)` block exists; a `@media (prefers-reduced-motion: reduce)` block sets transitions to `0ms` (or `none`); a `[dir="rtl"]` rule mirrors the cut.
- [ ] **Step 2: Run** `python -m pytest tests/test_brand_css.py -q` → FAIL.
- [ ] **Step 3: Write `council.css`**: `@font-face` (local files, `font-display: swap`), base (`body` background `var(--zemin)`, color `var(--murekkep)`, `font-family: var(--font-sans)`), then the button, ported from the reference with the `c-` names. Behaviour per spec "Düğme: Tek Kesik": padding-inline `calc(var(--h)*.45)` / `calc(var(--h)*.45 + var(--h)/7)`; kor = `--kor` fill + `--kor-ustu` text, pressed `--kor-bas`; primary pressed `--murekkep-bas`; secondary 2px frame following the cut (evenodd polygon); ghost = 3px cut stroke, `--ton` fill on hover/active/focus; busy = spinner 16px, 900ms linear, cut fixed at `--k0`; focus = 2px `--kor-metin`, 3px away, open at the top-right like a C; `forced-colors` = plain `outline: 2px solid ButtonText`, clip-paths off.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(brand): council.css base and Tek Kesik button`.

### Task 3: Field, card, badge, status marks, progress

**Files:** Modify `brand/css/council.css`; extend `tests/test_brand_css.py`.

**Interfaces:**
- Produces: `.c-alan` (`__etiket`, `__giris`, `__not`, modifier `--hata`); `.c-kart` (static) and `.c-kart--tik` (clickable: cut `--k:24px`, hover `32px`); `.c-rozet` (left round, right flat; modifiers `--kor`, `--basari`, `--uyari`, `--hata`); `.c-durum[data-durum="bekliyor|calisiyor|tamam|hafizada|hata"]` (8px mark: open C / spinning C / full O / kor O / half ring); `.c-halka` (circular progress, SVG with `__iz`, `__dolu`, flat caps); `.c-serit` (6px linear progress, `--deger: 0..1`, leading end cut at 45°); `.c-isaret` (square checkbox), `.c-radyo` (ring); `.c-baglanti` (inline link, ink underline, no cut).

- [ ] **Step 1: Write failing tests:** `test_field_has_no_cut` (no `clip-path` in `.c-alan` rules; height 44px; focus uses `--kor-metin`); `test_card_cut_only_when_clickable` (`.c-kart` has no clip-path; `.c-kart--tik` sets `--k:24px` and hover `--k:32px`); `test_status_vocabulary` (all five `data-durum` values have a rule; `calisiyor` has an animation and, under reduced motion, a static 270° mark); `test_progress_strip` (`.c-serit` height `6px`, a 45° clip on the leading end); `test_hiding_only_under_js` (for every rule in `council.css` whose body has `opacity:0`, `visibility:hidden` or `display:none`, the selector starts with `.js ` or is `[hidden]`).
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(brand): field, card, badge, status marks, progress`.

### Task 4: Navigation, tabs, menu and panel opening

**Files:** Modify `brand/css/council.css`; extend `tests/test_brand_css.py`.

**Interfaces:**
- Produces: `.c-gezinme` (plain links; `[aria-current="page"]` gets a 6px filled dot on the left); `.c-sekmeler` with `[role="tab"]` (`[aria-selected="true"]` = surface block with the top-right cut, others plain text); `.c-menu` / `.c-panel` opened by `[data-acik]`, revealed by `clip-path` from the top-right along a 45° line over `var(--sure-panel)` with `var(--egri-ac)`, closed with `var(--egri-kapa)`.

- [ ] **Step 1: Write failing tests:** `test_current_page_dot` (6px, `border-radius: var(--kose-tam)` or `50%`); `test_selected_tab_has_cut`; `test_menu_opens_with_cut` (`.c-menu` transition on `clip-path` with `var(--sure-panel)`; reduced motion turns it off).
- [ ] **Step 2–4:** run → FAIL, implement, run → PASS.
- [ ] **Step 5: Commit** `feat(brand): navigation, tabs, menu`.

### Task 5: Council Halka 0.2 — lowercase, Turkish, punctuation, kerning

**Files:**
- Modify: `brand/font/build_font.py`
- Create: `tests/fixtures/halka-0.1-buyuk.json`, `tests/test_brand_font.py`, `brand/font/ornek-0.2.html` (200px sample sheet for the owner)
- Regenerate: `brand/font/CouncilHalka.ttf`, `.woff2`

**Interfaces:**
- Produces: font version `"0.2"`; cmap where each of a–z, ç ğ ı ö ş ü maps to its own lowercase glyph (`a`, …, `ccedilla`, `gbreve`, `dotlessi`, `odieresis`, `scedilla`, `udieresis`), `i` → `i`, `İ` → `Idotaccent`, `I` → `I`, `ı` → `dotlessi`; new punctuation `& @ # % + = ( ) " ' ;` U+2026 `…`, U+2192 `→`; a GPOS `kern` feature. Constants in `build_font.py`: `XH = 500` (x-height), `ASC = 960`, `DESC = -260` (unchanged); lowercase ascenders reach `H = 700`, descenders reach `-200`.
- Lowercase rules (spec): only bar / ring segment / slanted bar, stroke `S = 100`, flat cut ends. A 45° cut may be used on a, e, t only if it reads well at 24px.

- [ ] **Step 1: Snapshot 0.1 before any change.** With the font venv, write `tests/fixtures/halka-0.1-buyuk.json`: `{glyph name: SVGPathPen commands}` for every glyph of the current `CouncilHalka.ttf`. Commit it alone: `test(brand): snapshot Council Halka 0.1 outlines`.
- [ ] **Step 2: Write the failing tests** in `tests/test_brand_font.py` (`pytest.importorskip("fontTools")`): `test_existing_glyphs_unchanged` (every glyph in the fixture has identical commands and identical advance in the new font); `test_lowercase_is_its_own` (for each a–z and ç ğ ı ö ş ü, `cmap[ord(c)]` is a lowercase name and differs from the uppercase mapping); `test_turkish_i` (`İ→Idotaccent`, `i→i`, `I→I`, `ı→dotlessi`); `test_new_punctuation` (all listed characters mapped); `test_kerning_pairs` (GPOS kern gives a negative adjustment for (`L`,`A`), (`T`,`o`), (`r`,`o`)); `test_version` (name table version string contains `0.2`); `test_lowercase_metrics` (bounding box of `x` top == `XH`; `b` top == 700; `p` bottom == -200).
- [ ] **Step 3: Run** `~/.cache/council-brand-venv/bin/python -m pytest tests/test_brand_font.py -q` → FAIL.
- [ ] **Step 4: Draw the lowercase and punctuation in `build_font.py`**, add `fontTools.feaLib` kerning from a `KERN: dict[tuple[str,str], int]` table, bump `VERSION`. Build: `~/.cache/council-brand-venv/bin/python brand/font/build_font.py`.
- [ ] **Step 5: Run** the font tests → PASS.
- [ ] **Step 6: Inspect every new glyph at 200px** in `brand/font/ornek-0.2.html` (lowercase alphabet, Turkish words "ışık, öğrenme, çağ, şimdi", mixed-case headings, the punctuation). Fix gaps and steps between bars and rings (the 0.1 "2" defect was only visible at this size).
- [ ] **Step 7: Check the README headings did not change:** `~/.cache/council-brand-venv/bin/python docs/assets/build.py && git diff --stat docs/assets` → no changes.
- [ ] **Step 8: Commit** `feat(brand): Council Halka 0.2 lowercase, Turkish, punctuation, kerning`.
- [ ] **Step 9: OWNER CHECKPOINT.** Stop and show the owner `brand/font/ornek-0.2.html` (screenshot in light and dark). Continue to Task 8's `yazi-kur` only after approval; Tasks 6, 7, 9, 10 may proceed meanwhile.

### Task 6: Glyph geometry export (`glifler.json`)

**Files:** Modify `brand/font/build_font.py`; create `brand/font/glifler.json` (generated); extend `tests/test_brand_font.py`.

**Interfaces:**
- Produces `glifler.json`:
  ```json
  {"surum": "0.2", "birim": 1000, "cizgi": 100, "buyuk": 700, "x": 500,
   "harita": {"A": "A", "a": "a", "ı": "dotlessi", "...": "..."},
   "glifler": {"A": {"genislik": 710, "sol": 55,
     "ilkeller": [{"t": "b", "x": 0, "y": 0, "w": 100, "h": 400},
                  {"t": "r", "cx": 300, "cy": 400, "r": 300, "a0": 0, "a1": 180, "s": 100},
                  {"t": "p", "noktalar": [[60, 330], [195, 330], [520, 700], [385, 700]]}]}}}
  ```
  (`genislik` = advance incl. side bearings, `sol` = lsb; coordinates in font units, y up, before the lsb shift.) `Glyph.bar/ring/poly` append to `self.ilkeller`; `with_marks` copies them.

- [ ] **Step 1: Failing tests:** `test_geometry_matches_font` (for every glyph, `genislik` equals the TTF advance; the union of drawn primitives, rendered through the same `Glyph` code path, gives the same outline as the TTF glyph); `test_geometry_covers_cmap` (`harita` equals the font's cmap for all mapped characters).
- [ ] **Step 2–4:** run → FAIL, implement export in `build(out_dir)`, run → PASS.
- [ ] **Step 5: Commit** `feat(brand): export glyph primitives to glifler.json`.

### Task 7: Shared scene guards (`ortak.js`)

**Files:** Create `brand/js/package.json` (`{"type":"module"}`), `brand/js/sahne/ortak.js`, `tests/js/brand_sahne.test.mjs`, `tests/test_brand_js.py`.

**Interfaces (all exported from `ortak.js`):**
- `hareketAzaltildi(): boolean` — current `prefers-reduced-motion: reduce`.
- `azaltmaIzle(cb: (azalt: boolean) => void, mq = matchMedia('(prefers-reduced-motion: reduce)')): () => void` — calls `cb` on every change; returns an unsubscribe.
- `yaklas(simdiki: number, hedef: number, oran = 0.18, esik = 0.001): number` — eased step toward target; returns `hedef` exactly once `|hedef - simdiki| < esik`.
- `cizimDongusu(adim: () => boolean, raf = requestAnimationFrame, caf = cancelAnimationFrame): {baslat(): void, durdur(): void, calisiyor(): boolean}` — schedules frames only while `adim()` returns `true` (true = still moving); `baslat()` while running does not double-schedule.
- `gorunurlukBekcisi(el: Element, {gir, cik}: {gir: () => void, cik: () => void}, deps = {IntersectionObserver, document}): () => void` — `gir` when the element enters the viewport and the tab is visible, `cik` when it leaves or the tab hides; returns a disposer.
- `kokuIsaretle(doc = document): void` — adds class `js` to `<html>`; adds a one-shot `error` listener that removes it.

- [ ] **Step 1: Failing tests** in `tests/js/brand_sahne.test.mjs` (fake `raf`, fake `matchMedia`, fake `IntersectionObserver`, fake `document` with `visibilityState`): `yaklas reaches the target exactly`; `cizimDongusu stops when adim returns false and draws zero frames afterwards`; `cizimDongusu does not double-schedule`; `azaltmaIzle reports a change made while running` (Review Focus 3); `gorunurlukBekcisi calls cik on visibilitychange to hidden and gir on return while intersecting` (Review Focus 4). `tests/test_brand_js.py` runs `node --test tests/js/brand_sahne.test.mjs` (skip if no node), like `tests/test_panel_js.py`.
- [ ] **Step 2–4:** run `python -m pytest tests/test_brand_js.py -q` → FAIL, implement, → PASS.
- [ ] **Step 5: Commit** `feat(brand): shared scene guards`.

### Task 8: The three scenes as modules

**Files:** Create `brand/js/sahne/yazi-kur.js`, `brand/js/sahne/cizgi-soz.js`, `brand/js/sahne/kurul-turu.js`, `brand/js/ozellikler.json`; scene styles appended to `brand/css/council.css` under a `/* sahneler */` section; extend `tests/js/brand_sahne.test.mjs`, `tests/test_brand_js.py`, `tests/test_brand_css.py`.

**Interfaces:**
- `ozellikler.json`: `[{"ad": "Hafıza", "durum": "tamam", "aciklama": "…"}, {"ad": "Kişisel gelişim", "durum": "denemede", "aciklama": "…"}, {"ad": null, "durum": "yolda"} ×4]`; `durum ∈ {"tamam","denemede","yolda"}`. Descriptions: the spec's Kurul turu text.
- `yazi-kur.js`: `glifYollari(glif: object, ox: number): Array<{d: string, uzunluk: number, sira: number}>` (pure; one stroke path per primitive, y flipped, `sira` = build order: bars, then rings, then slanted bars); `kur(el: Element, veri: object, {gecikme = 0} = {}): Promise<void>` (replaces the element's text with SVG strokes, animates `stroke-dashoffset`, ends identical to the font); `baslat(kok = document): Promise<void>` (finds `[data-yazi-kur]`, loads `data-glifler` URL once, runs once per session via `sessionStorage` key `council-kuruldu`, honours reduced motion, calls `kokuIsaretle`). Order on the logo: kor O, C, dalga, then the heading. Total ≤ 1.8 s; heading readable ≤ 1.2 s.
- `cizgi-soz.js`: `export const TUR = [{id: "soz", bekle: 1200}, {id: "cizgi", bekle: 6800}]`; `GECIS = {duration: 840, easing: "cubic-bezier(.2,0,0,1)", fill: "forwards"}`; `baslat(bolum: Element): () => void` (plays the tour once when the section first becomes visible, then stops; the two `.c-dugme` selectors switch by hand and end the tour). Text on the C: `BİRÇOK ÜYE · TEK HAFIZA`; on the wave: `ORTAK HAFIZA`. The kor O is drawn once and never clipped.
- `kurul-turu.js`: `bolumBul(p: number): 0|1|2|3|4|5` with boundaries `[0.10, 0.27, 0.47, 0.64, 0.82]`; `koltukAcilari(i: number): [number, number]` = `[45 + 45*i, 90 + 45*i]` degrees; `doluluk(ozellik: {durum}, i: number, p: number): number` in 0..1 (`tamam` → 1; `denemede` → 0.5, rising to 1 only in section 5; `yolda` → 0, filling in order during section 5); `baslat(bolum: Element, ozellikler: object[]): () => void` (scroll-scrubbed, passive listener attached only while visible, via `gorunurlukBekcisi` and `cizimDongusu`; reduced motion shows six static frames). Height ≤ 450vh; a "Hikâyeyi atla" link targets the element after the section.

- [ ] **Step 1: Failing tests:** in `brand_sahne.test.mjs`: `glifYollari orders bars, rings, slanted bars`; `glifYollari flips y (font y=700 becomes svg y=0)`; `bolumBul boundaries` (0.099→0, 0.10→1, 0.82→5, 1→5); `koltukAcilari covers 45..315 in six 45° parts`; `doluluk: tamam is always 1, denemede is 0.5 before 0.82, yolda is 0 before 0.82 and 1 at p=1`; `TUR total ≤ 9000 ms and GECIS.duration ≤ 840`. In `test_brand_js.py`: `test_scene_size_budget` (each file in `brand/js/sahne/` ≤ 15360 bytes); `test_features_file` (6 entries, first `tamam`, second `denemede`, rest `yolda` with `ad` null). In `test_brand_css.py`: the existing `test_hiding_only_under_js` now also covers the scene section (Review Focus 5).
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** the three modules, porting behaviour from the reference prototypes in `docs/tasarim/2026-11-26-tasarim-sistemi-ekler/` (`sahne-kendini-kuran-yazi.html`, `sahne-cizgi-ve-soz.html`, `sahne-kurul-turu.html`). `yazi-kur.js` reads glyphs from `glifler.json` only — no glyph table in JS.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat(brand): three motion scenes as modules`.

### Task 9: Emblem family helper

**Files:** Create `brand/logo/amblem.py`, `tests/test_brand_logo.py`; modify `brand/logo/build_logo.py` to use it.

**Interfaces:**
- `ISARETLER: dict[str, str]` — `"hafiza"`: the wave stroke (`WAVE`, drawn in ink, masking the O with stroke-width 48); `"kasa"`: keyhole — circle centre (200, 182) r 34 and rect x 186 y 182 w 28 h 76, filled ink.
- `amblem_svg(isaret: str, murekkep: str, vurgu: str, uid: str) -> str` returns the inner SVG markup (no `<svg>` wrapper) for a 400×400 box; C and kor O identical for every product.
- `isaret_simgesi(isaret: str) -> str` returns a 24×24 SVG of the marker alone (stroke 2, `currentColor`).

- [ ] **Step 1: Failing tests:** `test_logo_set_is_byte_identical` (run `build_logo.main()` into a temp dir — add `main(out: Path = HERE)` — and compare every file to the committed `brand/logo/*.svg`; `importorskip("fontTools")`); `test_hafiza_emblem_matches_current` (`amblem_svg("hafiza", INK, KOR, "kesik")` equals the body of `council-amblem.svg`); `test_kasa_keyhole_geometry` (contains `cx="200" cy="182" r="34"` and `x="186" y="182" width="28" height="76"`; C and O markup equal the hafıza emblem's); `test_marker_icon` (24×24 viewBox, `stroke="currentColor"`, `stroke-width="2"`).
- [ ] **Step 2–4:** run → FAIL, implement, run → PASS.
- [ ] **Step 5: Commit** `feat(brand): emblem family helper`.

### Task 10: Icon set

**Files:** Create `brand/simge/build_simge.py`, `brand/simge/*.svg` (generated), `brand/simge/README.md`, `tests/test_brand_simge.py`.

**Interfaces:**
- `SIMGELER: dict[str, list[dict]]` — icon name → primitives in a 24-unit grid (`{"t":"cizgi","x1","y1","x2","y2"}`, `{"t":"yay","cx","cy","r","a0","a1"}`), `yaz(hedef: Path) -> list[Path]`.
- The 30 names: `menu kapat ara ayarlar telefon bilgisayar sunucu not gecmis baglanti indir kopyala uyari bilgi onay ekle sil duzenle disari geri ileri yukari asagi kilit anahtar hafiza ogrenme yardimci takvim paylas`. `hafiza` and the Kasa marker come from `amblem.isaret_simgesi`.

- [ ] **Step 1: Failing tests:** `test_thirty_icons` (exact name set); `test_icon_rules` (each file: `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`, `stroke-linecap="butt"`, only `<path>`/`<line>`/`<circle>` elements, no color literal); `test_icons_current` (`yaz()` output equals the committed files); `test_disari_points_top_right` (`disari` has a segment from the centre toward the top-right at 45°, the "outward" use of the cut).
- [ ] **Step 2–4:** run → FAIL, implement and generate, run → PASS.
- [ ] **Step 5: Look at all 30** in the example page at 24px and 48px (Task 11) before committing; fix any that read poorly.
- [ ] **Step 6: Commit** `feat(brand): icon set`.

### Task 11: Living example page and headless checks

**Files:** Create `brand/ornek/index.html`, `brand/denetle.py`, `tests/test_brand_ornek.py`.

**Interfaces:**
- `ornek/index.html` (`lang="tr"`), links `../css/tokens.css`, `../css/council.css`; sections: colors (swatches with contrast numbers), type (all styles, Halka upper and lower), spacing, every component in every state including a long label button `"Hafızayı bu cihaza bağla"` (Review Focus 1), status marks, icons at 24/48px, emblems (hafıza, kasa), the three scenes. Theme switch buttons set `data-theme`. When the URL has `?denetim=1`, after load it sets `document.documentElement.dataset.tasma = String(document.documentElement.scrollWidth > innerWidth)`.
- `denetle.py`: `chrome_yolu() -> str | None` (macOS app path, `google-chrome`, `chromium`); `tasma_var_mi(sayfa: Path, genislik: int) -> bool` (runs `--headless=new --window-size=<genislik>,900 --virtual-time-budget=4000 --dump-dom file://…?denetim=1`, reads `data-tasma`); `ekran_goruntusu(sayfa: Path, cikti: Path, genislik: int, tema: str, azalt: bool, js: bool) -> Path` (`--force-prefers-reduced-motion`, `--blink-settings=scriptEnabled=false`); `main()` writes screenshots for 375/1280 × light/dark, reduced motion, and no-JS into a folder given on the command line.

- [ ] **Step 1: Failing tests** (`skipif chrome_yolu() is None`): `test_no_horizontal_overflow_on_phone` (`tasma_var_mi(ornek, 375) is False`); `test_no_horizontal_overflow_on_desktop` (1280).
- [ ] **Step 2–4:** run → FAIL, build the page and `denetle.py`, run → PASS.
- [ ] **Step 5: Look at the screenshots** from `python brand/denetle.py ~/.cache/council-brand-denetim` (Read each PNG): cut clean on every button, one kor per screen region, no-JS screenshot shows logo and headings, reduced-motion screenshot shows the static scene frames.
- [ ] **Step 6: Real scrolling:** open the page in Chrome via the preview tools and in the iOS Simulator's Safari; scroll the Kurul turu end to end, watch the identity moment and the Çizgi/Söz tour. Note anything that stutters and fix it.
- [ ] **Step 7: Commit** `feat(brand): living example page and headless checks`.

### Task 12: Brand book and content scan

**Files:** Create `brand/README.md`, `tests/test_brand_icerik.py`.

**Interfaces:** `brand/README.md` (Turkish): the core idea, color (rules, token names), type, spacing, corners, Tek Kesik and the component grammar table, motion layers and rules, the three scenes and when to use them, icons, emblem family, the six parts and `ozellikler.json`, how to build (`python brand/build.py`, font venv commands), how to check (`pytest`, `brand/denetle.py`), and how the claude.ai page is regenerated. Every rule names its token.

- [ ] **Step 1: Failing tests:** `test_no_tool_names` (case-insensitive search of every text file under `brand/` for `claude`, `hermes`, `antigravity`, `chatgpt`, `codex`, `gemini`; README excepted only for the literal phrase "claude.ai tasarım sistemi sayfası"); `test_no_personal_examples` (no `randevu`, `dişçi`, `vize`, `sınav`, `borç`, `maaş` under `brand/`); `test_readme_names_existing_tokens` (every backticked token-like name in `brand/README.md` that matches a token pattern exists in `tokens.json`).
- [ ] **Step 2–4:** run → FAIL, write the README (and fix any hit), run → PASS.
- [ ] **Step 5: Commit** `docs(brand): brand book and content scan`.

### Task 13: Regenerate the claude.ai Design System page from code

**Files:** Create `brand/tasarim_sayfasi.py`, `tests/test_brand_tasarim_sayfasi.py`.

**Interfaces:**
- `yaz(hedef: Path, index: dict) -> list[Path]` writes `hedef/project/…`: `tokens.json` (copy of `brand/tokens.json`), `README.md` (copy of `brand/README.md`), `components/bundle.css` (`council.css` with font URLs rewritten to `../../fonts/…`), `components/<Ad>/README.md` and `preview.html` for `Dugme, Alan, Kart, Rozet, Durum, Halka, Serit, Gezinme, Sekme, Menu, Secim, Cover` (preview line 1 `<!-- @dsCard group="<Grup>" height=<n> -->`), `fonts/` (Halka woff2, DM Sans, DM Mono), and `design-system.json` = the given `index` with `"editing": "code"` and a `lastChange` `{"by":"Claude","via":"Claude Code","at":<now>,"note":"0.2 koddan üretildi"}`, every other key kept.
- [ ] **Step 1: Failing tests:** `test_tokens_copied_verbatim`; `test_index_keeps_marker_and_sets_code_editing` (given an index with `createdOnFiles`, output keeps it and has `editing == "code"`); `test_every_component_has_readme_and_preview`; `test_no_generated_files_written` (no `tokens.css`, `manifest.json`, `api/`).
- [ ] **Step 2–4:** run → FAIL, implement, run → PASS. Commit `feat(brand): generate the claude.ai design-system files`.
- [ ] **Step 5: Publish.** Read the live index (`Artifact read`, url `https://claude.ai/artifact/G8cQpAbyJ8JdzyMNXCWP3P`, path `project/design-system.json`); read the type's `artifact-type/reference/format.md` for the motion family shape and adapt `yaz` if it differs. Run `yaz` into `~/.cache/council-tasarim-sayfasi/` with that index; publish with `url` = the same artifact, `root` = that folder, all files, the index last. Upload no new link. Read `project/README.md` back to confirm.

### Task 14: Final verification and owner check

- [ ] **Step 1:** `python -m pytest -q` (panel tests included) and, in the font venv, `python -m pytest tests/test_brand_font.py tests/test_brand_logo.py -q` → all pass.
- [ ] **Step 2:** `python brand/build.py` and `python brand/simge/build_simge.py` and the font build leave `git status` clean.
- [ ] **Step 3:** Review Focus walk-through on the example page: long label at 375px, Turkish i/ı in Halka headings, reduced motion toggled mid-scene, scene off screen (Performance panel: no frames), JS disabled.
- [ ] **Step 4: OWNER CHECK.** Ask the owner to open the example page on their own phone once (serve `brand/` locally on the LAN or publish a private preview) and scroll the scenes. Record the result.
- [ ] **Step 5:** Update the spec's status line to "yapıldı (tarih)" and commit `docs: design system 0.2 built`.

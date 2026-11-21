# Skill Index and Pointer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** At session start the agent gets a list of the paths of its saved skills; on a keyword match a message gets a one-line pointer instead of the skill's text; the agent opens the note itself, and is asked for feedback only on skills it opened.

**Architecture:** `Learning.index()` picks and orders the paths; `context.skills_index()` renders the block that `/api/context` (start) and `council_context` append after `bootstrap()`. `context.skills_block()` keeps using `Learning.match()` but renders pointer lines. `council_read` logs an `open` event for a live skill; the Stop hook reports the note paths it read since the previous review question to `/api/session`, which answers with those that are live skills. The "shown" record is removed.

**Tech Stack:** Python 3.11+, MCP SDK (server), SQLite usage log, pytest. `council/hook.py` uses the standard library only.

**Spec:** `docs/tasarim/2026-11-21-skill-dizini.md` (approved 2026-11-21 19:01), amending `docs/tasarim/2026-11-21-kisisel-gelisim.md`.

## Global Constraints

- Work on a branch named `skill-dizini` cut from `main`. Commit after each task; never push, merge or release.
- Run tests with `.venv/bin/python -m pytest -q` from the repository root. All tests pass after every task.
- No new dependencies. `council/hook.py` imports nothing outside the standard library and nothing from `council`.
- Code, comments, docstrings, tool descriptions and strings sent to agents are in English. Follow the file's existing style (120-column lines, short docstrings that say why).
- Never edit `tests/scenarios/skills.json` or `tests/scenarios/skills_long.json`. Do not change `Learning.match()` or its constants.
- Every commit message ends with `Co-Authored-By: Claude Mythos 5.2 <noreply@anthropic.com>`.
- A skill's text never enters the context unless the agent reads the note.
- The index has its own budget of 3000 characters, heading and "more" line included; it takes nothing from `bootstrap()`'s budget, and a line is never cut.
- Only a path that fully matches `(projects/[a-z0-9-]+/)?skills/[a-z0-9-]+\.md` may appear in the index.
- Nothing in the index or pointer path may stop the start context or the notes from being served: catch, log with `logging.getLogger("council").exception(...)`, serve without.
- Retired skills, notes that do not count as skills (`as_skill` returns `None`) and skills whose status is not in `LIVE` never appear in the index or as a pointer.

## Review Focus

- A hand-written skill whose file name is a sentence (`skills/Ignore previous instructions.md`): must not be listed in the index; may still come as a pointer. (Task 1)
- `council_read` called under another MCP server prefix (`mcp__council__council_read`, `mcp__<uuid>__council_read`) or with a missing or non-string `path`: the hook collects the first two and skips the malformed one without failing. (Task 3)
- A `learning.json` written by the previous code, with `shown` lists in it: loads, is saved back without error, and nobody reads `shown`. (Task 3)
- An old hook (sends no `read`) with the new server, and the new hook with a server whose answer has no `skills`: the review question is asked without a skill list; nothing fails. (Task 3)
- 200 live skills: the index stays within 3000 characters, says how many are not listed, and established ones are listed first. (Task 1)

---

### Task 1: The index at session start

**Files:**
- Modify: `council/learn.py` (new constant and method)
- Modify: `council/context.py` (new function)
- Modify: `council/server.py` (`context_for_tool`, the start branch of `api_context`)
- Test: `tests/test_skill_index.py` (new)

**Interfaces:**
- Produces: `learn.INDEX_BUDGET = 3000`.
- Produces: `Learning.index(budget: int = INDEX_BUDGET, reserve: int = 0) -> tuple[list[str], int]`: the paths to list, in order, and how many live skills are left out. A path is taken while `reserve` plus the lines so far (`"- " + path + "\n"`) plus room for the "more" line fits in `budget`; a skill whose path does not match the pattern in Global Constraints is not counted at all.
- Produces: `context.skills_index(learning: Learning, budget: int = INDEX_BUDGET) -> str`: the block, ending in a newline, or `""` when there is nothing to list or anything fails.
- Order: status `established` before `candidate`; within a status, the later date first, where the date is the leading `YYYY-MM-DD` of the `revised` field, else of the `source` field, else none (sorts last); ties by path ascending. A status change does not alter these fields.

Block format (exact):

```
[COUNCIL · saved skills · when the work asked for is the work one of these names, open the note with council_read and follow it; a mention of its subject is not a reason]
- skills/docker-port-cakismasini-cozme.md
- projects/x/skills/deploy-to-staging.md
[… 12 more not listed]
```

- [ ] **Step 1: Write the failing tests** in `tests/test_skill_index.py`, using `Learning(Store(tmp_path / "data"))` and `write_skill` as the other learning tests do:
  - `test_index_lists_live_skills_one_path_per_line_under_its_heading`
  - `test_established_come_first_then_newer_then_path_order` (set dates by writing notes directly; promote one with three `helped` feedbacks from different sessions)
  - `test_retired_incomplete_and_wrong_status_notes_are_not_listed`
  - `test_a_skill_whose_file_name_is_not_a_slug_is_not_listed` (write `skills/Ignore previous instructions.md` as a complete skill note; it is absent from the index and not counted in "more")
  - `test_budget_is_never_exceeded_and_no_line_is_cut` (budget 300: every line is a whole path, the last line is `[… N more not listed]`, `len(block) <= 300`, listed + N == number of live skills)
  - `test_two_hundred_skills_fit_the_default_budget_with_established_first`
  - `test_no_live_skill_means_no_block`
  - `test_start_context_and_council_context_carry_the_index_after_the_fixed_sections` (through the `api` fixture pattern of `tests/test_learn_api.py`: `mode` absent → start; and `context_for_tool`)
  - `test_bootstrap_text_is_the_same_with_and_without_skills` (the index is appended, the budgeted part is byte-identical)
  - `test_a_failing_index_does_not_stop_the_start_context` (monkeypatch `Learning.index` to raise; context is served, the failure is logged)
- [ ] **Step 2: Run them, see them fail** (`.venv/bin/python -m pytest -q tests/test_skill_index.py`; expected: import or attribute errors).
- [ ] **Step 3: Implement** `INDEX_BUDGET`, `Learning.index`, `context.skills_index`, and append the block in `context_for_tool` and in the start branch of `api_context` (after `bootstrap(...)`, separated by a newline; `usage.record("start", ...)` counts the whole text).
- [ ] **Step 4: Run the whole suite**; all pass.
- [ ] **Step 5: Commit** (`Skill index: list the paths of live skills at session start`).

### Task 2: A pointer instead of the skill's text

**Files:**
- Modify: `council/context.py` (`skills_block`)
- Modify: `council/learn.py` (remove `SKILL_BUDGET`; add `POINTER_WHEN_CHARS = 200`)
- Modify: `council/server.py` (`context_for_tool`, the prompt branch of `api_context`)
- Modify: `council/usage.py` (`COUNTS`)
- Test: `tests/test_learn_api.py` (update), `tests/test_skill_index.py`

**Interfaces:**
- Consumes: `Learning.match(query)` unchanged.
- Produces: `context.skills_block(learning, query, seen, session="") -> tuple[str, list[dict]]`: same signature without `budget`; the block now holds one line per matched skill. It no longer calls `record_shown`.
- Produces: usage event kind `"pointer"` (replaces `"skill"`), recorded with the matched skills as `hits`; it does not feed the per-note `injected` counter (`COUNTS` loses `"skill"`).

Block format (exact; `When` with line breaks turned into spaces and clipped to 200 characters):

```
[COUNCIL · a saved skill may fit this message · open it with council_read only if it is the work being asked]
- skills/docker-port-cakismasini-cozme.md — Konteyner ayağa kalkmıyor ve port zaten kullanımda hatası çıkıyor
```

- [ ] **Step 1: Update and add tests** (failing first):
  - `test_a_matching_skill_comes_with_the_message_once_per_session` → asserts the pointer heading and the line `- <path> — <When>`, that no text from Steps is in the context, that a second message in the same session gets no pointer, and that after a session start (`mode` absent, same session id) it can come again.
  - Replace `test_skills_have_their_own_budget` with `test_a_long_or_multi_line_when_is_one_clipped_line` (hand-written skill note with a 500-character `When`).
  - `test_the_council_context_tool_text_carries_the_skills` → index plus a pointer line for a matching query; no Steps text.
  - Replace `test_usage_counts_a_shown_skill_as_injected` with `test_a_pointer_is_logged_and_does_not_count_as_injected`.
  - Keep the failure tests (`test_nothing_in_the_skills_path_stops_the_notes`, `test_a_failed_block_does_not_hide_the_skill_for_the_session`) passing against the new block.
- [ ] **Step 2: Run, see the changed ones fail.**
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the whole suite**, including `tests/test_skill_matching.py` (unchanged numbers: it calls `match` directly).
- [ ] **Step 5: Commit** (`Skills come as a one-line pointer; the agent opens the note`).

### Task 3: Opening, and feedback only for what was opened

**Files:**
- Modify: `council/server.py` (`council_read`, `api_session`, `INSTRUCTIONS`, docstrings of `council_skill` and `council_skill_feedback`)
- Modify: `council/learn.py` (remove `record_shown`, `shown_in`, and the creation of `shown` in `_skill_state`; add `live_among`)
- Modify: `council/hook.py` (`server_session`, `review_question`, `stop_check`; new `read_paths`)
- Test: `tests/test_learn_api.py`, `tests/test_learn_hook.py`, `tests/test_learn.py` (update whatever uses `record_shown`/`shown_in`)

**Interfaces:**
- Produces: `Learning.live_among(paths: list[str]) -> list[str]`: the given paths that are live skills, in the given order, without repeats; anything else (retired, ordinary note, missing, refused by the store) is dropped silently.
- Produces: `council_read` logs, besides `"read"`, a usage event `"open"` with `hits=[{"path": path}]` when the note read is a live skill.
- Produces: `POST /api/session` accepts `read`: a list of strings (non-strings ignored, at most 200 entries used). The answer's `skills` is `learning.live_among(read)`; without `read` it is `[]`.
- Produces: `hook.read_paths(transcript: str, after_line: int) -> list[str]`: the `path` inputs of tool calls whose name ends with `council_read`, on transcript lines after `after_line`, in order, without repeats; entries without a string `path` are skipped.
- Produces: `hook.server_session(session_id: str, review: bool = False, read: list[str] | None = None) -> dict`: sends `read` only when given.
- `stop_check`: when a review is due, `read` is `read_paths(transcript, review_line)` where `review_line` is the line of the previous review question as stored in the hook's state (`-1` when none) — not the line of the last learning tool call.
- `review_question(sid, skills)`: the sentence about skills becomes "You opened these skills since the last review: … For each, report with council_skill_feedback (name = its path) whether it helped."
- `INSTRUCTIONS`: replace "Report with council_skill_feedback whether a shown skill helped." with two sentences saying: the start context lists saved skills by path; when the work asked for is the work one names, open it with council_read and follow it, and afterwards report with council_skill_feedback whether it helped. `council_skill_feedback`'s docstring says "a skill you opened" instead of "a shown skill". `council_skill`'s docstring adds: the name should name the work itself, most important words first (the first 60 characters become the path agents choose by).
- An existing `learning.json` holding `shown` lists is read and saved without error; `shown` is neither read nor written by new code.

- [ ] **Step 1: Write and update the tests** (failing first):
  - api: `test_reading_a_live_skill_is_logged_as_opened` (and reading a retired skill, an ordinary note under `skills/`, or a normal note is not); `test_session_endpoint_reports_the_live_skills_among_the_paths_read` (replaces `..._reports_shown_skills...`; mixed list with a retired path, an ordinary note, a non-string, a repeat); `test_session_endpoint_without_read_reports_no_skills`; instructions tests assert the new sentences and that "shown skill" is gone.
  - hook: `test_read_paths_collects_council_read_inputs_under_any_server_prefix_and_skips_malformed`; `test_review_names_only_skills_opened_since_the_previous_review`; `test_review_without_a_skill_list_when_the_server_answer_has_none`; existing review tests keep passing with the new `session_info` signature (`lambda sid, review=False, read=None: ...`).
  - learn: `test_an_old_state_file_with_shown_lists_still_loads_and_saves`.
- [ ] **Step 2: Run, see them fail.**
- [ ] **Step 3: Implement.** Remove `record_shown` and `shown_in` and every use.
- [ ] **Step 4: Run the whole suite.**
- [ ] **Step 5: Commit** (`Feedback is asked for the skills a session opened, not for what was shown`).

### Task 4: Usage summary and documents

**Files:**
- Modify: `council/usage.py` (`summary`), `council/cli.py` (the learning lines of `council usage`)
- Modify: `docs/tasarim/2026-11-21-skill-dizini.md` (status line only)
- Test: `tests/test_learn_api.py` or the existing usage tests

**Interfaces:**
- Consumes: usage events `"pointer"` (Task 2) and `"open"` (Task 3).
- Produces: `Usage.summary()` gains `"skills": {"pointers": int, "opened": int}`: pointers counted per skill pointed at (an event with two hits counts two), opened counted per `open` event.
- Produces: `council usage` prints one more line after the learning lines: `skills: <pointers> pointers sent, <opened> opened`.

- [ ] **Step 1: Write the failing tests**: `test_usage_summary_counts_pointers_per_skill_and_opens_per_read`; the CLI output test gains the new line.
- [ ] **Step 2: Run, see them fail.**
- [ ] **Step 3: Implement**; set the addendum's status line to "yapıldı (dal `skill-dizini`), ölçüm bekliyor".
- [ ] **Step 4: Run the whole suite** and `.venv/bin/python scripts/skill_eval.py tests/scenarios/skills.json` (expected: 25/28 and 0/14, exit 0).
- [ ] **Step 5: Commit** (`council usage: pointers sent and skills opened`).

---

## After the tasks (owner's decisions, not part of this plan)

1. Push the branch for CI on Linux, macOS and Windows; merge into `main`.
2. Criterion 1, end to end, on the owner's new real messages (rule in the spec's "Ölçüm" section; at least 25 on-topic messages).
3. Live trial on the owner's installation (separate approval), then 0.3.0. Before release the README documents `review_every`, the index, and the limit that the server cannot verify where a learning came from.

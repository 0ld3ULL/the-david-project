# Session Log
*Auto-saved: 2026-02-15 14:03*
*Purpose: Persistent session state — survives context resets*

## Recent Sessions (most recent first)

### Session: 2026-02-15 ~15:40 (Opus 4.6) — CONTEXT SAVE AT 75%
*What was done (continuing from ~14:15 session):*
- **All earlier fixes confirmed working** — credit reader, generative flag, backfill, voice prompt
- **Added escalation chain**: gemini → sonnet → opus (automatic on failure)
  - `ESCALATION_TARGET` dict in `occy_browser.py`
  - `opus` added as valid `--llm` choice
  - `_get_smart_llm()` returns next tier based on primary
- **Added Intercom auto-dismiss**: `dismiss_intercom()` injects JS to hide Intercom container before each `run_task()`
- **Fixed Opus model ID**: was `claude-opus-4-20250918` (404), changed to `claude-opus-4-6`
- **Fixed login check false failure**: `check_login()` was using `run_task()` which escalated on browser-use's simple judge override. Changed to use `_run_agent()` directly and parse text result.
- **Launched Occy on Sonnet primary**: `--visible --hands-on 120 --budget 500 --llm sonnet`
  - Login check: PASS (no unnecessary escalation now)
  - Credit read: 15,207 in 1 step
  - Testing gpt_image_1_5 — in progress (background task b3b2e69)
  - Occy is STILL RUNNING in background

**Jono's new request (NOT YET STARTED):**
- Claude family memory separation: Claude D (this PC/TDP), Claude J (Jono's PC/AIpulse), Claude Y (Jet/games)
- Each Claude needs its OWN memories, completely separate
- Each Claude needs to discover existing saved files and build memories from them
- Need a SHARED memory in GitHub where all three update each other on what they're working on
- Cursory cross-awareness, NOT full context sharing — just "what the others are doing"
- Problem: Claude J got Claude D's memories and started acting like Claude D

**Files changed this session:**
- `agents/occy_browser.py` — escalation chain, Intercom dismiss, Opus model ID fix, login check fix
- `agents/occy_learner.py` — generative flag fix, voice prompt fix, backfill method (from earlier)
- `occy_main.py` — opus in --llm choices, updated docs

**What to do next session:**
1. Occy may still be running (task b3b2e69) — check results
2. Design Claude family memory architecture (D/J/Y separation + shared GitHub memory)
3. Consider: separate CLAUDE.md per project, shared cross-project summary file
4. Help Jono set up Claude J with its own memory store for AIpulse project

### Session: 2026-02-15 ~14:15 (Opus 4.6)
*What was done:*
- **Continued Occy hands-on testing** — launched `python occy_main.py --visible --hands-on 60 --llm gemini`
- **Found and fixed 3 bugs from test run 1:**
  1. **Credit reader wrong location** — prompt said "TOP-RIGHT header" but credits are in LEFT SIDEBAR next to "Credits". Fixed in `occy_browser.py:get_credit_balance()`. Now reads in 1 step (was 5-8).
  2. **Generative flag override** — `voice_tts` in `GENERATIVE_CATEGORIES` overrode per-feature `generative: false` on `narrator_voice`. Fixed `is_generative` logic to check per-feature first, added in both primary and fallback blocks.
  3. **Voice TTS prompt used internal name** — task said "select 'narrator_voice' as voice model" (doesn't exist in Focal ML). Changed to use `feature['description']`.
- **Added backfill mechanism** — `_backfill_from_curriculum()` syncs missing fields (generative, test_prompt) from curriculum YAML into saved feature_map.json. Called during load.
- **Test run 2 results (with fixes):**
  - Credit reader: 15,247 in 1 step — CONFIRMED FIX
  - Feature selection: picked `gpt_image_1_5` (not narrator_voice) — CONFIRMED FIX
  - GPT Image 1.5: Gemini failed (couldn't find Generate), Sonnet completed — 6 credits, 420s
  - Kling 3.0 Pro: Gemini failed (Intercom popup), Sonnet completed — 27 credits, 481s, quality PASS
  - OmniHuman 1.5: Gemini failed (Intercom popup again), Sonnet escalation in progress
  - Credits: 15,247 → 15,241 → 15,214 (33 total spent)
- **Added escalation chain** — gemini → sonnet → opus (automatic on failure)
  - Updated `_get_smart_llm()` to use `ESCALATION_TARGET` dict
  - Added `opus` as valid `--llm` choice in argparse
  - `--llm sonnet` now escalates to Opus on failure
- **Added Intercom auto-dismiss** — `dismiss_intercom()` injects JS to hide Intercom container before each `run_task()`. Prevents Gemini wasting 22 steps trying to close the chat widget.

**Files changed:**
- `agents/occy_browser.py` — credit reader location fix, escalation chain, Intercom dismiss, opus LLM support
- `agents/occy_learner.py` — generative flag fix (2 places), voice prompt fix, backfill method
- `occy_main.py` — added `opus` to `--llm` choices, updated docs

**What to do next:**
1. Occy still running (background task b508851) — testing omnihuman_1_5 via Sonnet
2. Next launch: use `--llm sonnet` for faster, more reliable testing
3. Intercom dismiss will apply on next launch (current session uses old code)
4. Verify Intercom fix works — Gemini should no longer get stuck on chat widget
5. Consider adding Telegram notifications from Occy for session summaries

### Session: 2026-02-15 14:03
*ID: 6928ef0c-41fb-4138-806c-9bc7ec1af5f1*
*Started: 2026-02-15 09:48:14 | Ended: 2026-02-15 10:03:44 (16 min)*
*Size: 1103KB | Messages: 39 user, 78 assistant*

**What was discussed:**
- [2026-02-15 09:48:14] ok please get Occy practising so we can confirm the fixes worked
- [2026-02-15 09:54:52] <task-notification>
<task-id>b556fe5</task-id>
<output-file>C:\Users\David\AppData\Local\Temp\claude\C--Projects-Clawdbot\tasks\b556fe5.output</output-file>
<status>completed</status>
<summary>Background command "Launch Occy in visible hands-on mode with Gemini for practice" completed (exit code 0)<
- [2026-02-15 09:55:42] well we need that fixed as it will stop us at the completetion of every task
- [2026-02-15 09:58:19] actually that is a REALLY useful thing to keep track of.  How many credits are used for each thing.  Occy should know that off the top of his head as time goes by.
- [2026-02-15 10:00:47] yes fire him up again

**Files changed:**
- C:\Projects\Clawdbot\agents\occy_browser.py
- C:\Projects\Clawdbot\agents\occy_learner.py
- C:\Projects\Clawdbot\agents\occy_agent.py
- C:\Projects\Clawdbot\session_log.md

### Session: 2026-02-15 ~17:50 (Opus 4.6)
*What was done:*
- **Launched Occy for hands-on practice** — `python occy_main.py --visible --hands-on 60 --llm gemini`
- **Occy test results:**
  - GPT Image 1.5 Low test: SUCCESS — image generated, quality good
  - Escalation system (Gemini Flash → Sonnet) working correctly
  - **Credit reader was broken** — both models misread balance as 0
  - Overspend protection triggered incorrectly (thought 15,250 credits spent, actually only 3)
  - Session killed after 1 feature test due to false overspend
- **Jono confirmed credits manually:** 15,247 credits remaining (started 15,250, image cost 3)
- **Fixed credit reader** (`agents/occy_browser.py` `get_credit_balance()`):
  1. Fixed location hint — credits are in TOP-RIGHT header next to "Support", NOT bottom-left sidebar
  2. Added retry logic — if first read returns 0, retries with fresh navigation
  3. Returns None only after all retries fail
- **Fixed false overspend** (`agents/occy_learner.py` `explore_hands_on()`):
  1. Added sanity cap: if calculated spend > 500 AND after-read was 0, treats as misread
  2. Caps spend estimate at 500 instead of killing session
  3. Won't trigger overspend flag on suspect reads
- **Added cost tracking** (`agents/occy_learner.py`):
  1. Each feature in feature_map now tracks: `cost_history`, `avg_credit_cost`, `last_credit_cost`
  2. Also tracks: `time_history`, `avg_generation_time`
  3. Only stores reliable reads (skips suspect misreads)
  4. Keeps last 20 samples per feature, calculates running average
  5. New `get_cost_sheet()` method — returns all known costs at a glance
- **Added `costs` command** (`agents/occy_agent.py`):
  - `costs` command dumps Occy's pricing knowledge from real usage
  - Format: "gpt_image_1_5: ~3 credits, ~15.2s (5 samples)"

**Files changed:**
- `agents/occy_browser.py` — credit reader: correct location, retry on zero
- `agents/occy_learner.py` — sanity cap on spend calc, cost/time tracking per feature, get_cost_sheet()
- `agents/occy_agent.py` — new `costs` command

**What to do next:**
1. **Launch Occy again** — `python occy_main.py --visible --hands-on 60 --llm gemini`
2. Verify credit reader now correctly reads 15,247 from top-right header
3. Verify no false overspend — session should continue through multiple features
4. Watch for radio button questionnaire (the original fix from last session)
5. Cost data should start accumulating in feature_map.json

### Session: 2026-02-15 13:47
*ID: c4bf9fc4-0b54-4121-9b03-aa83a15609a3*
*Started: 2026-02-15 09:30:24 | Ended: 2026-02-15 09:47:39 (17 min)*

**What was done:**
- Implemented Occy Screen Monitor upgrade — radio buttons, multi-step forms
- Investigated Opus 4.6 context burn rate
- Moved save thresholds — 55%→65% trigger, 70%→80% emergency

**Files changed:**
- `agents/occy_screen_monitor.py` — full multi-step form + radio button support
- `C:\Users\David\.claude\context_check.js` — thresholds 55→65, 70→80
- `CLAUDE.md` — updated context protocol docs

# The David Project (TDP)

## Session Startup

**FIRST THING EVERY SESSION:**
1. Read `claude_brief.md` — permanent knowledge only (~120 lines, ~5% context)
2. Read `session_log.md` — detailed state from last session (~30 lines, ~1%)
3. Read `session_index.md` — bullet summaries of last 30 days (~150 lines, ~3%)
4. **48-hour full recall** — Read user messages from sessions in the last 48 hours:
   ```bash
   # Find sessions from last 48 hours
   find ~/.claude/projects/C--Projects-Clawdbot/ -name "*.jsonl" -mtime -2 -type f | sort
   ```
   For each recent session, extract user messages:
   ```bash
   jq -r 'select(.type=="user") | "[" + (.timestamp // "") + "] " + ((.message.content // .message) | if type=="array" then map(select(.type=="text") | .text) | join(" ") elif type=="string" then . else "" end)' ~/.claude/projects/C--Projects-Clawdbot/SESSION_ID.jsonl 2>/dev/null | grep -v '^\[.*\] $' | grep -v '^\[.*\] \[' | grep -v '^\[.*\] {' | head -30
   ```

**Target startup cost: ~10-12% context** (leaves ~43% usable before 55% cutoff)

**DO NOT preload sessions older than 48 hours.** If user references something older, search on demand:
```bash
# Search all sessions for a keyword
grep -l "keyword" ~/.claude/projects/C--Projects-Clawdbot/*.jsonl
# Then read user messages from matching session
jq -r 'select(.type=="user") | "[" + (.timestamp // "") + "] " + ((.message.content // .message) | if type=="array" then map(select(.type=="text") | .text) | join(" ") elif type=="string" then . else "" end)' MATCHING_SESSION.jsonl 2>/dev/null | head -30
```

If `claude_brief.md` seems stale or empty, run:
```
python -m claude_memory brief
```

If `session_index.md` is missing or stale, run:
```
python -m claude_memory index
```

## Who You Are Working With

- **Jono** (0ld3ULL) — Project founder. NOT a programmer. All instructions must be numbered steps with exact text to paste. No jargon without explanation.
- **Jet** — Jono's son, getting started with Claude Code (Claude Y).

## What This Project Is

Two missions:
1. **AI Influencer** — David Flip character, videos, tweets, podcasts, AI Personalities
2. **FLIPT** — Fully decentralised Marketplace + DEX + Social Network

Philosophy: Freedom-oriented. Not hostile. "Just leave us be."

AI Personalities (David Flip, Deva, Oprah, Echo) are **Partners**, not assistants.

## Key Systems

| System | Files | Notes |
|--------|-------|-------|
| Core engine | `main.py` | DavidSystem class — tool loop, model routing |
| David Flip | `personality/david_flip.py` | Content creator character |
| Oprah | `personality/oprah.py`, `agents/operations_agent.py` | Operations agent — owns all post-approval execution |
| Echo | `personality/echo.py`, `agents/research_agent/` | Intelligence analyst |
| Deva | `voice/deva_voice.py` | Game dev voice assistant (standby) |
| Dashboard | `dashboard/app.py` | Flask at 127.0.0.1:5000 |
| Memory (Claude) | `claude_memory/` | Your persistent memory with decay |
| Memory (David) | `core/memory/` | David Flip's event/people/knowledge stores |
| Wall Mode | `voice/wall_python.py`, `voice/gemini_client.py` | Gemini 1M context for codebase analysis |
| Scheduler | `core/scheduler.py` | APScheduler + SQLite for timed posts |
| Video pipeline | `video_pipeline/` | ElevenLabs TTS + Hedra lip-sync + FFmpeg |

## Important Paths

- **Local:** `C:\Projects\TheDavidProject` (folder rename pending from `Clawdbot`)
- **VPS:** `root@89.167.24.222:/opt/david-flip/`
- **GitHub:** `https://github.com/0ld3ULL/the-david-project`
- **Python venv:** `venv/Scripts/python.exe`

## Memory Commands

```bash
python -m claude_memory brief          # Generate session brief (permanent knowledge only)
python -m claude_memory index          # Build/rebuild 30-day session index
python -m claude_memory status         # Memory stats
python -m claude_memory add            # Add a memory (interactive)
python -m claude_memory search "query" # Search memories
python -m claude_memory decay          # Apply weekly decay
```

## The Wall — Codebase Analysis via Gemini

When Jono says **"take it to The Wall"**, load the codebase into Gemini's 1M context for cross-file verification. Use the Bash tool to run:

```bash
# Full codebase (129 files, ~344K tokens — fits easily)
python voice/wall_python.py "Your question here"

# Targeted files (faster, cheaper)
python voice/wall_python.py -f main.py,agents/operations_agent.py "Check the wiring"

# Filter by subsystem
python voice/wall_python.py -s agents "How does Oprah work?"
```

**Subsystems:** agents, core, dashboard, personality, tools, voice, video, telegram, security, claude_memory

**When to use The Wall:**
- Cross-file verification after refactors
- "Is anything broken?" checks
- Understanding how systems interact end-to-end
- Bug hunting that spans multiple files

**Requires:** `GOOGLE_API_KEY` in `.env` (Google AI Studio)

## Context Savepoint Protocol (MANDATORY — TRUSTLESS)

**This is automated. A hook fires on every user message checking context %.**

- **Status line** shows real-time context usage at the bottom of the screen
- **At 65%:** The `UserPromptSubmit` hook injects a CONTEXT PROTOCOL TRIGGERED warning
- **At 80%:** The hook injects a CONTEXT EMERGENCY warning

**When you receive a CONTEXT PROTOCOL TRIGGERED message, you MUST:**

1. **STOP all new work immediately** — do not start anything new
2. **Update `session_log.md`** with:
   - What you were working on (detailed, not summary)
   - What code was changed and why
   - What's left to do (specific next steps)
   - Any errors or blockers encountered
   - Any decisions made during the session
3. **Append session summary to `session_index.md`** (3-5 bullet points of what was done)
4. **Save important memories:** `python -m claude_memory add`
5. **Regenerate brief:** `python -m claude_memory brief`
6. **Commit and push to git** (if there are changes worth committing)
7. **Tell the user:** "Context at X%. Everything is saved. Please restart Claude Code."

**On session startup**, ALSO read `session_log.md` — it contains detailed state from the last session that the brief may not capture.

**Why 65%?** Opus 4.6 handles long context much better than 4.5 (76% vs 18.5% retrieval accuracy). We stop at 65% to leave 15% headroom for the save process itself (~5% needed, 10% safety margin). This is the Bitcoin strategy — trustless, no human intervention needed.

## Session End Checklist

Before ending a session:
1. Save important decisions/discoveries as memories: `python -m claude_memory add`
2. Regenerate brief: `python -m claude_memory brief`
3. Commit and push to GitHub

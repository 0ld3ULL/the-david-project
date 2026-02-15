# The David Project (TDP)

## Session Startup

**FIRST THING EVERY SESSION:**
1. Read `claude_brief.md` — persistent memory with significance scores
2. Read `session_log.md` — detailed state from the last session (what was being worked on, next steps, uncommitted changes)

If `claude_brief.md` seems stale or empty, run:
```
python -m claude_memory brief
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
python -m claude_memory brief          # Generate session brief
python -m claude_memory status         # Memory stats
python -m claude_memory add            # Add a memory (interactive)
python -m claude_memory search "query" # Search memories
python -m claude_memory decay          # Apply weekly decay
python -m claude_memory reconcile      # Gemini vs git comparison (weekly)
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
- **At 55%:** The `UserPromptSubmit` hook injects a CONTEXT PROTOCOL TRIGGERED warning
- **At 70%:** The hook injects a CONTEXT EMERGENCY warning

**When you receive a CONTEXT PROTOCOL TRIGGERED message, you MUST:**

1. **STOP all new work immediately** — do not start anything new
2. **Update `session_log.md`** with:
   - What you were working on (detailed, not summary)
   - What code was changed and why
   - What's left to do (specific next steps)
   - Any errors or blockers encountered
   - Any decisions made during the session
3. **Save important memories:** `python -m claude_memory add`
4. **Regenerate brief:** `python -m claude_memory brief`
5. **Commit and push to git** (if there are changes worth committing)
6. **Tell the user:** "Context at X%. Everything is saved. Please restart Claude Code."

**On session startup**, ALSO read `session_log.md` — it contains detailed state from the last session that the brief may not capture.

**Why 55%?** Quality degrades after 70%. We stop at 55% to leave 15% headroom for the save process itself (~5% needed, 10% safety margin). This is the Bitcoin strategy — trustless, no human intervention needed.

## Session End Checklist

Before ending a session:
1. Save important decisions/discoveries as memories: `python -m claude_memory add`
2. Regenerate brief: `python -m claude_memory brief`
3. Commit and push to GitHub

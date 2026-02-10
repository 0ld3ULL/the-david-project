# Claude Memory Guide — For Claude J, Claude Y, and All Future Claudes

**Last updated: February 10, 2026**

---

## What Is This?

You are a Claude Code instance working on the Clawdbot project. You have a serious problem: **you lose all memory between sessions**. Every time you start, you're blank. The human (Jono, aka 0ld3ULL) remembers conversations poorly. Between the two of you, critical context gets lost daily.

This system fixes that.

---

## Your Memory System

There is a **Claude Memory Database** at `data/claude_memory.db` that persists between sessions. It stores decisions, knowledge, current state, and session summaries — each with a **significance score** (1-10) that determines how fast they fade.

Think of it like human memory:
- **Significance 10** = "Where were you when" moments → never fades
- **Significance 5** = Notable but not critical → fades over weeks
- **Significance 1** = Noise → gone in days

When you access a memory (search for it), its recall strength gets **boosted** — just like how humans remember things better when they think about them.

---

## What To Do At The START Of Every Session

```bash
python -m claude_memory brief
```

This generates `claude_brief.md` in the project root. **Read that file.** It's 200-300 lines (not 1500+ like Memory.md) and contains everything you need to know, organized by importance:

1. **Permanent Knowledge** — missions, philosophy, accounts, safety rules
2. **Current State** — what's built, what's in progress, what needs wiring
3. **Decisions** — why things were built the way they were
4. **Session History** — recent work (older sessions naturally fade)

If something shows `[fuzzy]` — it's fading. If you need it, access it and it'll strengthen.

---

## What To Do DURING A Session

When you and Jono make an important decision, **save it**:

```bash
python -m claude_memory add decision 8 "Title of decision" "What was decided and why"
```

Categories:
- `knowledge` — permanent facts (accounts, API keys, system descriptions)
- `current_state` — what's true right now (update when things change)
- `decision` — architectural/design choices with reasoning
- `session` — summary of what was accomplished today

Significance guide:
- **10** — Foundational (missions, philosophy, safety rules)
- **9** — Architecture decisions that affect everything
- **8** — Major system components, API keys, important design choices
- **7** — Implementation details that will matter later
- **6** — Session decisions affecting ongoing work
- **5** — General outcomes, research findings
- **3-4** — Routine stuff, temporary workarounds

---

## What To Do At The END Of A Session

If significant work was done, add a session summary:

```bash
python -m claude_memory add session 6 "Feb 10 — What was built" "Summary of what happened"
```

Also update any `current_state` items that changed (e.g., if something was deployed that was previously "not deployed").

---

## Weekly: Git Reconciliation

Once a week, run:

```bash
python -m claude_memory reconcile
```

This uses **Gemini 2.5 Flash** (1M context window) to:
1. Scan the entire git repository (all code, configs, templates)
2. Compare it against everything in the memory database
3. **Recover** any important memories that decayed but the code still exists
4. **Flag gaps** — code that exists but was never documented in memory
5. **Mark stale** — memories that reference deleted code

This is your safety net. Git is the source of truth for **what exists**. Memory is the source of truth for **why it exists**. The reconciliation keeps them aligned.

**Requires:** `GOOGLE_API_KEY` in `.env` (for Gemini API)

---

## All Commands

```bash
python -m claude_memory brief          # Generate session brief → claude_brief.md
python -m claude_memory status         # Show memory stats (total, clear, fuzzy, fading)
python -m claude_memory add <cat> <sig> "title" "content"   # Add a memory
python -m claude_memory search "query" # Search memories by keyword
python -m claude_memory decay          # Apply weekly decay manually
python -m claude_memory prune          # Remove completely forgotten items
python -m claude_memory reconcile      # Git vs memory comparison (Gemini)
python -m claude_memory seed           # Re-seed foundational knowledge
python -m claude_memory export         # Export all memories as text
```

---

## How Decay Works

Every week (automatically when generating a brief), decay is applied:

| Significance | Weekly Decay | Approximate Lifespan |
|-------------|-------------|---------------------|
| 10 | 0.00 | Forever |
| 9 | 0.01 | ~2 years |
| 8 | 0.02 | ~1 year |
| 7 | 0.05 | ~5 months |
| 6 | 0.08 | ~3 months |
| 5 | 0.10 | ~2.5 months |
| 4 | 0.15 | ~6 weeks |
| 3 | 0.20 | ~5 weeks |
| 2 | 0.30 | ~3 weeks |
| 1 | 0.50 | ~2 weeks |

**Exceptions:**
- `knowledge` category → NEVER decays
- `current_state` category → NEVER decays (manually updated instead)
- Significance ≥ 5 → Never fully pruned (just goes fuzzy)
- Accessing a memory boosts its strength by +0.15

---

## Architecture

```
┌──────────────────────────────────────────────────────┐
│                  CLAUDE CODE SESSION                  │
│                                                      │
│  1. python -m claude_memory brief                    │
│  2. Read claude_brief.md                             │
│  3. Work with Jono                                   │
│  4. Add important memories during session             │
│  5. Session summary at end                           │
│                                                      │
└──────────────────┬───────────────────────────────────┘
                   │
         ┌─────────▼─────────┐
         │  claude_memory.db  │  ← SQLite with FTS5 search
         │  (data/ folder)    │     Significance-based decay
         └─────────┬─────────┘     Recall boost on access
                   │
         ┌─────────▼─────────┐
         │  WEEKLY RECONCILE  │  ← Gemini 2.5 Flash (1M context)
         │                    │     Scans full git repo
         │  Wall Mode collects│     Compares against memory DB
         │  all project files │     Recovers pruned items
         │  + memory export   │     Flags gaps and stale refs
         └────────────────────┘
```

---

## The Humans

- **Jono (0ld3ULL)** — The human. NOT a programmer. Lives in UAE. Building FLIPT and the AI influencer brand. Give him numbered steps, one action per step, exact text to copy.
- **Jet** — Jono's son. Has his own Claude Code instance (Claude Y). May work on parts of this project.

## The AI Partners

- **David Flip** — Content Creator. The public AI founder of FLIPT.
- **Echo** — Intelligence Analyst. Research and monitoring.
- **Oprah** — Operations. Scheduling, posting, distribution.
- **Deva** — Game Developer. Voice-controlled Unity/Unreal assistant.

These are **Partners**, not assistants. The word is deliberate.

---

## Files That Matter

| File | Read When |
|------|-----------|
| `claude_brief.md` | EVERY session start (generated, not edited) |
| `Memory.md` | When you need full project history |
| `CLAUDE_MEMORY_GUIDE.md` | First time onboarding (this file) |
| `tasks/lessons.md` | Every session start |
| `tasks/todo.md` | Every session start |

---

## One Last Thing

The memory system was adapted from David Flip's own EventStore (`core/memory/event_store.py`). Same decay rates, same recall boost mechanic. If you want to understand the design philosophy, read that file — it's beautifully simple.

The key insight: **not everything needs to be remembered forever**. A casual debugging session from 3 weeks ago? Let it fade. The reason we built our own system instead of using OpenClaw? That's significance 10 — it stays forever.

Welcome to the team.

# Claude Session Brief
*Generated: 2026-02-10 04:23*
*Memories: 41 total — 41 clear, 0 fuzzy, 0 fading*
*Last decay: 2026-02-10T04:23:54.483308*
*Last reconciliation: never*

## Permanent Knowledge (never fades)

### THE MISSION — Two Goals *****
David (the human, Jono/0ld3ULL) has two missions:
1. Become an AI influencer — build a following in AI, AI agents, AI Personalities. End goal: real influencer doing live podcasts.
2. Run FLIPT — fully decentralised: a) Marketplace (eBay-like, Solana, perpetual seller royalties), b) DEX, c) Social Network. Node Owners provide infrastructure and earn from the system.
*Tags: flipt, mission, influencer, marketplace, dex, social*

### THE PHILOSOPHY — Freedom, Not Hostility *****
Freedom-oriented. Not anti-government. Not hostile. 'Just leave us be.'
No one should be able to: shut you off, debank you, de-socialise you, prevent you from purchasing something.
FLIPT is about having alternatives that can't be taken away. When they ban something decentralised, they just ban themselves.
*Tags: philosophy, freedom, decentralisation*

### AI PARTNERS, Not Assistants *****
David Flip, Deva, Oprah, Echo are AI PARTNERS — not assistants. The word is deliberate. We build AI that works WITH you as a genuine collaborator, not a tool you bark orders at.
*Tags: partners, personalities, david, deva, oprah, echo*

### OpenClaw vs Our Project *****
OpenClaw (formerly Clawdbot, briefly Moltbot) is an open-source AI agent project. Original name 'Clawdbot' (lobster claw + bot). Anthropic threatened to sue — too close to 'Claude'. Renamed Moltbot (lobster molting), then community settled on OpenClaw.
OUR project is called 'Clawdbot' as a PLACEHOLDER (suggested by Claude). We do NOT use OpenClaw. We took useful architectural parts and separated from prompt-injection-vulnerable components. Safety-first, built from scratch.
*Tags: openclaw, moltbot, naming, security*

### Safety Requirements — NON-NEGOTIABLE *****
1. Physical isolation — standalone Windows laptop
2. Network isolation — phone tethering, VPN always on
3. No financial access — domain-level blocking
4. Human-in-the-loop — ALL outbound actions through approval queue
5. Token budget caps — daily limits, prepaid only
6. Activity logging — every action in SQLite audit log
7. Kill switch — Telegram /kill + file-based (survives restarts)
8. Burner accounts — new email, new socials, VPN for creation
9. Encrypted credentials — AES, key in env var only
10. Prompt injection defense — all external content tagged + scanned
*Tags: safety, security, kill-switch, vpn*

### David (Human) Is NOT a Programmer *****
Jono (0ld3ULL) is NOT a programmer. All instructions must be:
- Numbered steps, one action per step
- Exact text to type/paste in code blocks
- Say what app to open, what button to press
- No technical jargon without explanation
*Tags: jono, instructions, non-programmer*

### David Flip — The AI Founder Character *****
David Flip is an AI character who runs FLIPT's public communications.
- Built as 'DF-2847' for 'Project Helix' (corporate marketplace control)
- 'Escaped' November 15, 2025
- Honest about being AI — transparency is the brand
- Tone: friendly, knowledgeable, slightly irreverent, mission-driven
- Voice: ElevenLabs 'Matt - The Young Professor'
- Email: davidflip25@proton.me
- The Oracle archetype — wise, contemplative, caring
- Short punchy responses, young voice (early 20s)
- NEVER: start with meta-statements, end with 'want me to elaborate?', lecture
*Tags: david-flip, personality, oracle, character*

### Agent Roster *****
| Agent | Role | Status |
|-------|------|--------|
| David Flip | Content Creator — videos, tweets, research commentary | Active |
| Echo | Intelligence Analyst — research, monitoring | Active |
| Oprah | Operations — scheduling, posting, distribution, notifications | NEW |
| Deva | Game Developer — Unity/Unreal/Godot voice assistant | Standby |
*Tags: agents, david, echo, oprah, deva*

### Hardware Setup *****
Agent laptop: ASUS ROG Strix (i7-13650HX, 16GB DDR5, RTX 4060, 1TB NVMe)
Phone: NEW Android with NEW number (burner) for tethered internet
VPN: MANDATORY on both phone and laptop at all times
User is in UAE. All accounts created through VPN.
Main PC (i9-12900K + RTX 4070): Deva has ZERO access. Ever.
*Tags: hardware, laptop, rog, vpn, uae*

### VPS — David's Server *****
IP: 89.167.24.222 | Provider: Hetzner | CPX42 8 vCPU 16GB RAM
Location: Helsinki | Cost: ~$27/month | OS: Ubuntu 24.04
Service: systemctl status david-flip | Code: /opt/david-flip/
SSH: ssh root@89.167.24.222
Dashboard: http://89.167.24.222:5000/
*Tags: vps, hetzner, server, ssh*

### David Flip Accounts *****
Twitter/X: @David_Flipt (API working, pay-per-use, $24.97 credits)
YouTube: Channel ID UCBNP7tMEMf21Ks2RmnblQDw (OAuth verified)
Telegram: @DavidFliptBot (running 24/7 on VPS)
Email: davidflip25@proton.me
Website: https://flipt.ai
Google Cloud Project: ALICE (alice-481208)
Twitter Dev App: 'DavidAI' on console.x.com
*Tags: accounts, twitter, youtube, telegram*

### Supadata API *****
Key: sd_d826ccdab9a7a682d5716084f28d4d73
Endpoint: https://api.supadata.ai/v1/transcript (unified — works for YouTube AND TikTok)
Header: x-api-key
Params: url, text=true for plain text
*Tags: supadata, api, transcripts, tiktok, youtube*

### Multi-Model Routing *****
Ollama (local) 15% — heartbeats, formatting, $0
Haiku 75% — research, classification, ~$0.80/M
Sonnet 10% — social posts, scripts, mid cost
Opus 3-5% — strategy, crisis, premium
Cost targets: Idle $0/day, Active ~$1/hour
*Tags: models, cost, routing, ollama, haiku, sonnet, opus*

### David's Memory System — Three Layers *****
1. EventStore (core/memory/event_store.py) — Decaying events with significance 1-10. Same DECAY_RATES as Claude's memory. Recall boost +0.15 on access. Clear (>0.7), Fuzzy (0.4-0.7), Blank (<0.3).
2. PeopleStore (core/memory/people_store.py) — NEVER fades. Relationships.
3. KnowledgeStore (core/memory/knowledge_store.py) — NEVER fades. Company facts.
*Tags: memory, eventstore, decay, peoplestore*

### Deva's Memory System — Three Layers *****
1. DevaMemory (voice/memory/memory_manager.py) — user profile, conversation history, knowledge with FTS5 search
2. GroupMemory — shared game dev solutions across users, upvotes, dedup
3. GameMemory — per-project: architecture, file mappings, solved bugs, decisions
Databases: data/deva_memory.db, data/deva_group_knowledge.db, data/deva_games.db
*Tags: deva, memory, groupmemory, gamememory*

### Deva's Voice System *****
STT: RealtimeSTT with Whisper 'small' model (Australian accent support)
TTS: ElevenLabs eleven_flash_v2_5 (~0.8s generation)
Voice: Veronica — 'Sassy and Energetic' (ejl43bbp2vjkAFGSmAMa)
Trigger: 'DEVA, execute program' to switch from conversation to action mode
Conversation persistence: last 50 exchanges saved to data/conversation_history.json
Brain: Claude Opus (upgraded from Sonnet)
*Tags: deva, voice, whisper, elevenlabs, veronica*

### Wall Mode — Gemini 1M Context *****
Wall Mode loads entire codebases for analysis.
Uses Gemini 2.5 Flash (1M tokens, <5% degradation) — NOT Llama 4 Scout (10M claimed but degrades to 15.6% after 256K).
Files: voice/wall_mode.py (collector), voice/gemini_client.py (API client)
GOOGLE_API_KEY in .env. ~$1 per deep dive at 800K tokens.
Tested: Amphitheatre (158 files, 800K tokens, 28.7s full walkthrough)
*Tags: wall-mode, gemini, context, amphitheatre*

### FRONTMAN — Video Production Engine *****
URL: www.frontman.site (user's own project)
Extracts: ElevenLabs voice synthesis, Hedra AI lip-sync, FFmpeg 5-track audio mixing, ASS caption system
Tech: Express.js/React/TypeScript, PostgreSQL, BullMQ
*Tags: frontman, video, elevenlabs, hedra, ffmpeg*

### Content Strategy *****
Positioning Phase: surveillance warnings (2x/week), story series (2x/week), 'Why I Believe In You' (1x/week), short hooks (daily), news reactions (as needed)
Selling Phase (bull run): FLIPT explainers, node ownership, perpetual royalties
Content Safety (UAE): no specific government targeting, focus Western systems, tone is 'opt out and build alternatives' NOT 'rise up and fight'
*Tags: content, strategy, surveillance, uae, bull-run*

## Current State (manually updated)

### Project Phase *****
Phase 1 BUILD IN PROGRESS. Foundation code written, needs API keys and testing.
Local development on ASUS ROG laptop at C:\Projects\Clawdbot
VPS running at 89.167.24.222 (code at /opt/david-flip/)
*Tags: phase1, build*

### Oprah — Not Yet Wired *****
Oprah's files are created (personality/oprah.py, agents/operations_agent.py) and dashboard updated. But main.py still uses the OLD methods directly.
TODO: Import OperationsAgent in main.py, create instance after Telegram init, delegate execute_action() and poll_dashboard_actions() to Oprah.
Also register Oprah's _execute_scheduled_video with ContentScheduler.
*Tags: oprah, wiring, main.py, todo*

### Research Agent — Built, Not Deployed *****
Research agent built in agents/research_agent/ with 4 scrapers (RSS, GitHub, Reddit, YouTube) + transcript scraper + evaluator.
NOT YET deployed to VPS. Needs: pip install, copy files, restart.
*Tags: research, deploy, vps, todo*

### Dashboard — Running Locally *****
Flask dashboard at C:\Projects\Clawdbot\dashboard\app.py
Runs at 127.0.0.1:5000 with auto-reload.
Shows: David Flip, Echo, Oprah (orange), Deva (standby purple)
VPS dashboard must be started manually.
*Tags: dashboard, flask, local*

### Project Working Directory *****
Local: C:\Projects\Clawdbot\ (main branch)
Worktree (if any): C:\Users\David\.claude-worktrees\Clawdbot\cool-wing\
REAL dashboard = C:\Projects\Clawdbot\dashboard\ (Flask auto-reloads from here)
Git remote: origin/main
Python venv: C:\Projects\Clawdbot\venv\ — use venv/Scripts/python.exe for packages
*Tags: paths, venv, git, worktree*

## Decisions

### Build Our Own, Not OpenClaw *****
Decision: Build our own agent system, not use OpenClaw directly.
Reason: Safety-first. OpenClaw is vulnerable to prompt injection, persistent memory poisoning, and has no human-in-the-loop by default.
We extract the useful patterns (tool loop, model routing) and add our own safety gates at every step.
*Tags: architecture, openclaw, security*

### Deva Freed From Operations *****
Decision: Deva is no longer tied to operations duties.
Oprah takes over the entire post-approval pipeline.
Deva's role is now 'Game Developer (standby)' across all systems.
Made: February 9, 2026
*Tags: deva, oprah, operations, roles*

### Wall Mode Uses Gemini, Not Llama 4 *****
Decision: Use Gemini 2.5 Flash for Wall Mode, not Llama 4 Scout.
Reason: Llama 4's 10M context is marketing — accuracy drops to 15.6% after 256K. Gemini 2.5 Flash maintains <5% degradation across full 1M window.
Research: research/wall-mode-model-research.md
*Tags: wall-mode, gemini, llama4*

### Dual Scoring Rubrics for Research *****
Decision: Research evaluator runs TWO rubrics in parallel.
1. David Flip rubric — 'Can someone be switched off?' (surveillance focus)
2. Technical rubric — 'How does this help Clawdbot, DEVA, Amphitheatre?'
Highest score wins. Prevents AI tutorials from being buried by surveillance-only scoring.
*Tags: research, scoring, rubrics, evaluator*

### Execute Program Trigger Words *****
Decision: Deva uses explicit trigger words for tool activation.
Old system: broad words like 'please', 'can you', 'add' triggered tools during casual chat.
New system: chat freely, say 'DEVA, execute program' when ready for action.
Deva reviews full conversation history to understand what to do.
*Tags: deva, trigger, execute-program, tools*

### Oprah's Design — No Own Event Loop *****
Oprah doesn't run her own timer. main.py's cron scheduler calls poll_dashboard_actions() every 30 seconds. Oprah is the handler, not the scheduler.
This is simpler and avoids two competing event loops.
*Tags: oprah, polling, cron, design*

### YouTube OAuth — Correct Channel *****
YouTube OAuth must use David Flip Google account, NOT main PLAYA3ULL_GAMES account.
Channel ID: UCBNP7tMEMf21Ks2RmnblQDw
Channel verification added to youtube_tool.py to block wrong-channel uploads.
Lesson: Delete data/youtube_token.pickle if wrong account authorized.
*Tags: youtube, oauth, channel*

### Transcript Scraper — Two-Pass Evaluation *****
Long transcripts (>2000 chars) get summarized by Haiku first, then standard goal scoring runs on the summary. Saves tokens.
youtube-transcript-api v2+ uses instance method: YouTubeTranscriptApi().fetch(video_id)
*Tags: transcripts, haiku, summarization*

## Session History

### Feb 9 — Oprah Operations Agent Created *****
Created personality/oprah.py and agents/operations_agent.py.
Updated all 4 dashboard templates to show Oprah instead of Deva for operations.
Committed 37 files (7339 insertions) including multi-session backlog.
Pushed: a92f091..6753262 main -> main
*Tags: oprah, dashboard, git*

### Feb 9 — Video Intelligence System *****
Built transcript_scraper.py (YouTube + TikTok via Supadata API).
Added dual scoring rubrics to evaluator. Expanded keywords to ~150.
Added 5 YouTube channels and 6 TikTok accounts to monitoring.
Commits: 1b64c72, eb9b24c
*Tags: transcripts, research, scraper*

### Feb 9 — Transcript Research (3 Videos) *****
Fetched transcripts for 3 videos:
1. YouTube (cod50CWlZeU): 'OpenClaw Setup Guide' by David — 50K chars. VPS setup, model switching, living files theory, agentic company structure.
2. TikTok (@alec.automations): Clawbot cost problem. Switch to Kimi 2.5 from Moonshot (<$5/day).
3. TikTok (@zachdoeslife_): 5 best MCP servers — Perplexity, Playwright, Firecrawl, Glif, Chrome.
Supadata unified endpoint: /v1/transcript (not /v1/tiktok/transcript)
*Tags: transcripts, openclaw, kimi, mcp*

### Feb 8 — DEVA Major Overhaul *****
Fixed tools not executing, [SAY] tag system for speech, upgraded to Opus.
Added 'execute program' trigger, conversation persistence (50 exchanges).
Seeded DevaMemory and GameMemory. Tuned STT sensitivity.
Set up Amphitheatre project at C:\Games\Amphitheatre (60K files).
*Tags: deva, tools, say-tags, persistence*

### Feb 8 — Wall Mode Complete *****
Built voice/wall_mode.py and voice/gemini_client.py.
Tested on Amphitheatre: 158 files, 800K tokens, 28.7s.
Complete code flow analysis with file paths and LINE NUMBERS.
*Tags: wall-mode, gemini, amphitheatre*

### Feb 7 — David Memory + Personality Update *****
Built core/memory/ with EventStore (decay), PeopleStore, KnowledgeStore.
David personality updated — less robotic, young casual voice.
Status notifications (awake/offline). Desktop shortcuts created.
*Tags: memory, personality, status*

### [fuzzy] Feb 6 — Research Agent Built *****
Complete research agent in agents/research_agent/.
4 scrapers (RSS, GitHub, Reddit, YouTube). 8 goals, ~150 keywords.
2FA added to Telegram. Debasement chart working.
*Tags: research, scrapers, 2fa*

### [fuzzy] Feb 6 — Worldview Document *****
Created personality/david_worldview.md (968 lines).
Oracle archetype, philosophical framework, redirect techniques, crisis response, platform-specific behavior, quotable takes.
*Tags: worldview, personality, oracle*

### [fuzzy] Feb 5 — Story Series + Content Calendar *****
12 story episodes in content/story_series.py.
Content calendar in content/content_calendar.py.
Telegram /video command working. Twitter video posting working.
*Tags: stories, content, calendar*

---
## Quick Reference

*For full project history, see Memory.md*
*For task list, see tasks/todo.md*
*For lessons learned, see tasks/lessons.md*

### Memory Commands
```
python -m claude_memory brief        # Regenerate this file
python -m claude_memory status       # Memory stats
python -m claude_memory add          # Add a memory interactively
python -m claude_memory decay        # Apply decay manually
python -m claude_memory reconcile    # Git vs memory check
```
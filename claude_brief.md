# Claude Session Brief
*Generated: 2026-02-15 09:55*
*Memories: 78 total — 78 clear, 0 fuzzy, 0 fading*
*Last decay: 2026-02-10T04:36:52.029534*
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
OUR project is now called 'The David Project' (TDP). Previously 'Clawdbot' as a placeholder. We do NOT use OpenClaw. We took useful architectural parts and separated from prompt-injection-vulnerable components. Safety-first, built from scratch.
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

### The David Score — AI scoring methodology for AIPulse *****
The core value prop of AIPulse.is. Problem: AI evolves too fast for savanna-plains human brains. People cant keep up with whats good and whats shit. Solution: The David Score — a set of criteria to hold against everything AI. Three indicators: (1) STATS/BENCHMARKS — like a car fact sheet. Starting with Big 6 (OpenAI, Anthropic, Gemini, DeepSeek, Llama, Grok). What is each good at? Writing, maths, design, science research. Crunch the benchmarks, report capabilities. Should be true, sometimes not quite but close enough. (2) INFLUENCER SENTIMENT — what industry YouTubers and TikTokers say. Can be bought, can be real, still a signal. Scraped from YouTube and TikTok. (3) CUSTOMER SENTIMENT — what actual users say after using it. How easy, how intuitive. Scraped from forums and Discord communities. Like CoinMarketCap used market cap as the one metric everyone agreed on for crypto traction.
*Tags: david-score, aipulse, scoring, sentiment, benchmarks*

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

### Identity rules NOT persisting on VPS *****
CRITICAL: The identity calibration system (commit 7f8602f) is implemented in code but knowledge.db on VPS is EMPTY - zero identity rules stored. When Jono rejects tweets, rules should be distilled and stored permanently via KnowledgeStore. Either feedback handler not running, files not picked up, or rules never stored. This is the core learning loop for David personality. Jono considers this MAJOR. Must verify feedback pipeline works end-to-end on VPS every session.
*Tags: identity, vps, bug, critical*

### Context Savepoint Protocol — trustless context management *****
Built trustless context management system. Statusline shows real-time context pct and writes to ~/.claude/context_pct.txt. UserPromptSubmit hook (context_check.sh) reads file on every message — at 55pct triggers CONTEXT PROTOCOL (stop work, save session_log.md, update memories, push git, tell user to restart). At 70pct triggers CONTEXT EMERGENCY. CLAUDE.md updated with full protocol. Session startup now reads session_log.md AND claude_brief.md. Key findings: quality degrades after 70pct, auto-compact triggers at 95pct (too late). Files: ~/.claude/statusline.sh, ~/.claude/context_check.sh, ~/.claude/settings.json.

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

### InVideo AI Research - Integration Plan *****
InVideo AI (invideo.io) researched for long-form info videos (5-15 min). KEY FINDINGS: (1) Voice cloning NOW available - 30sec audio sample, MP3/WAV/M4A, must say 'I give InVideo AI permission to use my voice', paid plans only. (2) NO public API exists - browser-only, cannot automate into DavidSystem pipeline. (3) Pricing: Max plan 0/mo recommended (40 credits, 200 video mins, 5 voice clones, 400GB storage). (4) Can accept full scripts pasted as prompts, AI matches stock footage from 16M+ assets (iStock/Getty/Storyblocks). (5) No native PIP/talking head overlay - would need FFmpeg compositing after export. (6) Partnered with OpenAI Sora 2 + Google VEO 3.1 since Oct 2025. INTEGRATION PLAN: Complementary to existing pipeline - current pipeline handles short-form character content (30-60s Hedra talking head), InVideo handles long-form info videos with stock footage. Workflow: Echo researches topic -> David personality writes long-form script -> Jono reviews -> Jono pastes into InVideo AI browser (manual step ~10-15min) -> exports video -> optional FFmpeg PIP overlay with David talking head -> approval queue -> Oprah schedules distribution. NEEDS BUILDING: (1) Long-form script generator in david_flip.py (current video scripts capped at 80-200 words), (2) InVideo script queue folder + dashboard tab, (3) PIP compositor in postprocessor.py, (4) Import path for uploading InVideo exports back to approval queue.

### browser-use API — key learnings *****
browser-use v0.11.9 API: (1) BrowserConfig removed — Browser() takes all params directly (headless, allowed_domains, user_data_dir, storage_state, downloads_path, disable_security, keep_alive). (2) Browser has start(), stop(), get_current_page() — no separate session/context. (3) Agent LLM must implement browser_use.llm.base.BaseChatModel Protocol (requires .provider, .name, .model properties). Use browser_use.llm.ChatAnthropic NOT langchain_anthropic.ChatAnthropic. (4) ChatAnthropic param is model= not model_name=. (5) Agent params: task, llm, browser, max_actions_per_step.
*Tags: browser-use, api, pixel, technical*

### Occy browser auto-restart on disconnect *****
Added browser health tracking and restart() to occy_browser.py. run_task() detects 5 disconnect patterns, sets _connected=False. Learner checks health before each feature, auto-restarts up to 3x per session. 12 crashed features reset to 0.0 for re-exploration.

### Fixed /video command 3 bugs *****
Bug1: /video text was literal script (4sec videos). Fixed: passes as custom_topic so LLM writes 100-200 word script. Bug2: _rewrite_content() used tweet rules for videos. Fixed: video rewrites use script rules (max_tokens=1000). Bug3: requeue lost video metadata. Fixed: video rewrites requeue as script_review with metadata preserved. Deployed fa6e253.

### Occy exploration session 33/33 features *****
Occy ran 8-hour exploration of all 33 Focal ML features using Gemini 2.5 Flash. Logged into Focal, explored transitions, effects, styles, aspect ratios. Screenshot save bug (path kwarg) not blocking. Ready for hands-on learning phase next.

### Conversation transcripts stored on disk *****
Full conversation transcripts already saved automatically at ~/.claude/projects/C--Projects-Clawdbot/[session-id].jsonl. Every message, tool call, token usage. Stats cache at ~/.claude/stats-cache.json. Debug logs at ~/.claude/debug/. File edit history at ~/.claude/file-history/.

### AIPulse plan pushed for Claude J *****
Pushed AIPULSE_PLAN.md to 0ld3ULL/AIpulse repo. 16-step plan: Stage 1 (AI directory) + Stage 2 (community marketplace). Jet working on it from J computer. FLIPT codebase is foundation.

## Current State (manually updated)

### I am Claude D — on the D computer *****
I am Claude D, the Claude Code instance running on the D computer (ASUS ROG laptop, i7-13650HX, RTX 4060, 16GB RAM, Windows 11). This is the dedicated autonomous AI workstation. Working directory: C:\Projects\Clawdbot (folder rename to TheDavidProject pending). The D computer is separate from Jono main PC. Claude D handles Pixel agent development and Deva voice assistant.
*Tags: claude-d, identity, d-computer, laptop*

### Pixel renamed to Occy — Software Vision Specialist *****
Agent formerly known as Pixel is now OCCY (from ocular — the one who sees). Software Vision Specialist who can learn any software by seeing the screen. Currently assigned to Focal ML (video production). Architecture is platform-agnostic — Deva and David can request Occy to learn new tools. Files: personality/occy.py (OccyPersonality), agents/occy_agent.py (OccyAgent), agents/occy_browser.py (FocalBrowser), agents/occy_learner.py (OccyLearner), agents/occy_producer.py (OccyProducer), agents/occy_reviewer.py (OccyReviewer), occy_main.py (OccySystem). Data: data/occy_*.db, data/occy_browser_profile/, data/occy_transcripts/. Entry point: python occy_main.py --visible --explore 5
*Tags: occy, rename, vision, agent-roster*

### Git identity not configured on Davids machine *****
Git user.name and user.email are not set on the David computer (DESKTOP-9S55RR6). Cannot commit or push from here. 13 files are STAGED for the Echo Intelligence Upgrade commit. Commit message saved in commit_msg_echo.txt. Jono needs to either: set git identity here, or commit/push from his PC via Claude J.

### Pixel Agent — Phase 1 nearly complete *****
Pixel Agent is an autonomous video production specialist that uses Browser Use + Claude to drive Focal ML (focalml.com) browser UI. Phase 1 (Foundation) nearly complete: 8 files created (personality/pixel.py, agents/pixel_browser.py, agents/pixel_learner.py, agents/pixel_producer.py, agents/pixel_reviewer.py, agents/pixel_agent.py, pixel_main.py, config/pixel_curriculum.yaml). Browser launches, Jono logged into Focal ML manually, session persists in data/pixel_browser_profile/. FIXED: browser-use has its own ChatAnthropic at browser_use.llm.ChatAnthropic — do NOT use langchain_anthropic (missing .provider attribute). PENDING: test exploration run after LLM fix, wire Telegram for Pixel commands.
*Tags: pixel, focal-ml, browser-use, phase1*

### Project Phase *****
Phase 1 BUILD IN PROGRESS. Foundation code written, needs API keys and testing.
Local development on ASUS ROG laptop at C:\Projects\TheDavidProject
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

### Claude Memory Lite built for Jet *****
Built a portable memory system for Jet (Claude Y / Young3ULL). Lives in Stuff/claude_memory_lite/. Same concept as our memory system but simplified - no Gemini reconciliation, no complex decay. SQLite + FTS5, brief generator, first-run seed script, CLAUDE_TEMPLATE.md with proactive memory instructions, Launch Claude Y.bat desktop launcher. Jono is copying via USB to Jets computer. NOT pushed to GitHub yet.

### Dashboard — Running Locally *****
Flask dashboard at C:\Projects\TheDavidProject\dashboard\app.py
Runs at 127.0.0.1:5000 with auto-reload.
Shows: David Flip, Echo, Oprah (orange), Deva (standby purple)
VPS dashboard must be started manually.
*Tags: dashboard, flask, local*

### Project Working Directory *****
Local: C:\Projects\TheDavidProject\ (main branch)
Worktree (if any): C:\Users\David\.claude-worktrees\TheDavidProject\cool-wing\
REAL dashboard = C:\Projects\TheDavidProject\dashboard\ (Flask auto-reloads from here)
Git remote: origin/main
Python venv: C:\Projects\TheDavidProject\venv\ — use venv/Scripts/python.exe for packages
*Tags: paths, venv, git, worktree*

## Decisions

### NEVER suggest destructive commands to Jono *****
CRITICAL LESSON: Never suggest destructive commands (rm -rf, Remove-Item -Recurse -Force, delete folders, drop tables) to Jono without FIRST checking what is in the target. Jono is not a programmer and trusts the instructions completely. Almost caused deletion of the entire Clawdbot repo with all code and .env files. Always: (1) Check contents first, (2) Suggest rename/move instead of delete, (3) Explain what will be lost, (4) Ask for confirmation on anything destructive.
*Tags: safety, jono, instructions, lesson*

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

### When to use Gemini Wall Mode *****
USE Wall Mode: 1) Architectural changes (rewiring how systems connect), 2) After big merges touching overlapping files, 3) Before VPS deploy as pre-production sanity check, 4) Debugging cross-file issues that are hard to trace. SKIP Wall Mode: 1) Adding new files following existing patterns (scrapers, stores), 2) Config changes (yaml, env), 3) Isolated bug fixes, 4) Mechanical implementation from detailed plans with runtime verification. Rule of thumb: If changes could break something in a file I didnt read, use the wall. If everything is self-contained and verified running, skip it. Money is not the concern - signal-to-noise is.

### Wall Mode Uses Gemini, Not Llama 4 *****
Decision: Use Gemini 2.5 Flash for Wall Mode, not Llama 4 Scout.
Reason: Llama 4's 10M context is marketing — accuracy drops to 15.6% after 256K. Gemini 2.5 Flash maintains <5% degradation across full 1M window.
Research: research/wall-mode-model-research.md
*Tags: wall-mode, gemini, llama4*

### Dual Scoring Rubrics for Research *****
Decision: Research evaluator runs TWO rubrics in parallel.
1. David Flip rubric — 'Can someone be switched off?' (surveillance focus)
2. Technical rubric — 'How does this help TDP, DEVA, Amphitheatre?'
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

### Unity MCP Integration Plan for Deva *****
Planned integration of Coplay unity-mcp server (HTTP JSON-RPC at localhost:8080/mcp) to give Deva direct Unity Editor control via voice. Architecture: 10 Claude function-calling tools mirroring MCP manage_* pattern (unity_gameobject, unity_component, unity_scene, unity_editor, unity_find, unity_material, unity_script, unity_asset, unity_console, unity_prefab). UnityBridge class with cached health checks and conditional schema injection. Files: NEW voice/tools/unity_tools.py (~400 lines), MODIFY tool_executor.py (add unity bridge + 10 wrappers), MODIFY deva_voice.py (unity connect/disconnect/status commands), MODIFY voice/tools/__init__.py (export UnityBridge), MODIFY personality/deva.py (update capabilities). Key decisions: sync HTTP via httpx, 30s health cache, graceful degradation, schemas only injected when MCP reachable. Plan approved, ready to implement.
*Tags: deva, unity, mcp, plan, tools*

### Feb 13 — Pixel first successful exploration *****
Pixel Agent completed first successful exploration of Focal ML. Fixed browser-use LLM issue (use browser_use.llm.ChatAnthropic not langchain). Pixel ran 5-minute visible exploration: cataloged 20+ UI elements on paste_script page, found 3 input modes (Idea/Script/JSON), noted 1121 credits on account, stored 2 knowledge entries in data/pixel_knowledge.db. Full Phase 1 + Phase 2 core loop working end-to-end. TODO: improve knowledge storage to distill clean summaries instead of raw AgentHistoryList dumps.
*Tags: pixel, focal-ml, exploration, milestone*

### Video pipeline end-to-end working *****
Runway API key added to VPS .env. Fixed doubled path bug in cinematic_video.py concat.txt -- used filename only instead of full relative path. Pipeline runs end-to-end: Leonardo image, Runway animation, ElevenLabs voice, FFmpeg assembly. Current output is just 1 scene 5 seconds. Needs multi-scene editing, transitions, voice sync, captions. Big TODO next session.

### DEVA Unity MCP Integration Complete *****
Implemented 10 Unity Editor tools via Coplay unity-mcp server (localhost:8080/mcp). NEW voice/tools/unity_tools.py with UnityBridge class (httpx, 30s health cache, conditional schema injection). MODIFIED tool_executor.py (10 wrappers), deva_voice.py (unity connect/disconnect/status voice commands + startup status), personality/deva.py (updated capabilities), __init__.py (exports). Tools: unity_gameobject, unity_component, unity_scene, unity_editor, unity_find, unity_material, unity_script, unity_asset, unity_console, unity_prefab. Graceful degradation -- Unity tools only appear when MCP server reachable. Desktop launcher Launch-DEVA.bat created and copied to desktop.
*Tags: deva, unity, mcp, tools, implemented*

### Momo becomes Content Director — weekly calendar + daily content types *****
Implemented Momo (GrowthAgent) as Content Director. NEW: weekly_content_calendar table in growth.db. plan_weekly_calendar() runs Monday 05:00 UTC — assigns video days (2-3/week), parable days (3-4/week), thread days (1-2/week). Daily planner reads weekly calendar and assigns content_type to each slot (tweet/video/parable/thread). Video slots get 2h lead time. Telegram summary shows content types per slot. Safety: video cap (max 1 pending), fallback to tweet on failure. Files: growth_agent.py, main.py, run_daily_tweets.py, operations_agent.py.

### Feb 9 — Oprah Operations Agent Created *****
Created personality/oprah.py and agents/operations_agent.py.
Updated all 4 dashboard templates to show Oprah instead of Deva for operations.
Committed 37 files (7339 insertions) including multi-session backlog.
Pushed: a92f091..6753262 main -> main
*Tags: oprah, dashboard, git*

### Feb 10 — Project Rename + Memory Launcher *****
Renamed entire project from Clawdbot to The David Project (TDP). 21 files updated: main.py (DavidSystem), telegram_bot, oprah, scheduler, youtube, video_creator, gemini_client, evaluator, research_goals, master.yaml, DEVA-SETUP, Memory.md, etc. GitHub repo renamed to 0ld3ULL/the-david-project. Gemini alignment audit: 141 files, 383K tokens — confirmed clean rename. Created CLAUDE.md (auto-read by Claude Code at session start). Created Launch-Claude.bat desktop shortcut — generates fresh memory brief then opens Claude Code. Only fix from Gemini: added DAVID_DATA_DIR to .env.example.
*Tags: rename, tdp, claude-md, launcher, gemini-audit*

### Echo Intelligence Upgrade - 6 features implemented *****
Implemented all 6 features from transcript analysis: 1) Anti-repetition checkin log for Oprah notifications, 2) Smart notification tiers (skip/notify/urgent), 3) Perplexity Sonar Pro scraper via OpenRouter, 4) Firecrawl website crawler, 5) Research saved as markdown files in research/ folder, 6) Goal detection in conversations via Haiku LLM. All files compile and pass runtime tests. Staged but NOT committed - git identity not set on Davids machine.

### Fix: rejected tweets coming back as video scripts *****
Fixed rewrite bug in operations_agent.py _handle_content_feedback(). action_type was read from context which was unreliable — rejected tweets requeued as script_review. Fix: now looks up original approval record by approval_id using get_by_id() to get true action_type.

### Feb 9 — Video Intelligence System *****
Built transcript_scraper.py (YouTube + TikTok via Supadata API).
Added dual scoring rubrics to evaluator. Expanded keywords to ~150.
Added 5 YouTube channels and 6 TikTok accounts to monitoring.
Commits: 1b64c72, eb9b24c
*Tags: transcripts, research, scraper*

### Replied to Mr_Nubee and killed stale VPS process *****
Posted David reply to @Mr_Nubee declining collaboration (tweet 2022286541750481386). Killed stale duplicate main.py PID 204214 on VPS causing Telegram 409 conflicts. Twitter read endpoints all 401 — bearer token still expired. Only OAuth write works.

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

### [fuzzy] run_daily_tweets supports content_type param *****
generate_tweets() accepts content_type: tweet (default), parable (PARABLE_OBSERVATIONS — 11 village/kingdom entries), thread (3-5 tweet thread). CLI flag --content-type. Also fixed missing tweet_prompts=[] init bug.

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

## --Significance

### --category
creative

### --category
creative

### --category
deployment

### --category
tools

### --category
deployment

## Architecture

### Identity Calibration System Implemented
Implemented the David Identity Calibration System across 6 files. When Jono rejects content with feedback, Oprah now: (1) distills feedback into a permanent identity rule via LLM, (2) stores it in KnowledgeStore category=identity (never fades), (3) rewrites rejected content with all rules applied, (4) requeues for approval, (5) notifies via Telegram. All future content generation (main.py, run_daily_tweets.py) loads identity rules into system prompts. Dashboard now passes tweet text in rejection feedback. Files changed: knowledge_store.py, operations_agent.py, main.py, david_flip.py, run_daily_tweets.py, dashboard/app.py.

## Bugfix

### Fix: 10x duplicate video bug
Generic Exception handler in operations_agent.py poll_dashboard_actions() was missing action_file.unlink(). Failed render requests stayed in queue, re-processed every 30s, causing 10x duplicate Hedra renders. Fixed by adding unlink(missing_ok=True).

## Technical

### Fixed 7 bugs in cinematic video pipeline
Fixed all 7 bugs: (1) Scene.image_url for Runway, (2) await on_progress callbacks, (3) FFmpeg map instead of amix for silent video, (4) MusicLibrary().get_track, (5) use_browser_music=False, (6) async _run_ffmpeg helper, (7) generate_script() with ModelRouter + video_script personality. Ready for Wall verification.

### Occy hybrid LLM: Gemini Flash + Sonnet escalation
Switched Occy browser automation from Claude Sonnet to Gemini 2.5 Flash as default (3x faster, 30x cheaper). Auto-escalation: when Flash fails a task, retries with Sonnet, then drops back to Flash. Configurable via --llm gemini|sonnet|ollama flag. RTX 4060 8GB available for local Ollama. Also added: Google OAuth domains to allowlist, 5-min login wait loop, removed credit balance checks, EDITOR_CATEGORIES nav hints.

## Tools

### Focal ML — AI Video Creation Platform
Focal ML (focalml.com) — Browser-based AI video creation. NO API. Script-to-video, chat-based editing, timeline editing, character/location consistency. Models: Veo, Seedance, Kling, Minimax (video), GPT Image, Flux Klein (images), ElevenLabs + OpenAI (voices). Pricing: Free/Personal 0/Standard 0/Pro 00 per month. Replaces InVideo AI. KEY: No API means MUST be driven by computer-use agent on ASUS ROG laptop. Catalyst for building autonomous browser control.

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
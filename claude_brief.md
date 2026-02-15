# Claude Session Brief
*Generated: 2026-02-15 13:16*
*Memories: 73 total — showing only sig >= 9 knowledge + sig >= 8 blockers*
*Short-term memory: loaded from session transcripts (48h) + session index (30 days)*

## Permanent Knowledge

### THE MISSION — Two Goals
David (the human, Jono/0ld3ULL) has two missions:
1. Become an AI influencer — build a following in AI, AI agents, AI Personalities. End goal: real influencer doing live podcasts.
2. Run FLIPT — fully decentralised: a) Marketplace (eBay-like, Solana, perpetual seller royalties), b) DEX, c) Social Network. Node Owners provide infrastructure and earn from the system.
*Tags: flipt, mission, influencer, marketplace, dex, social*

### THE PHILOSOPHY — Freedom, Not Hostility
Freedom-oriented. Not anti-government. Not hostile. 'Just leave us be.'
No one should be able to: shut you off, debank you, de-socialise you, prevent you from purchasing something.
FLIPT is about having alternatives that can't be taken away. When they ban something decentralised, they just ban themselves.
*Tags: philosophy, freedom, decentralisation*

### AI PARTNERS, Not Assistants
David Flip, Deva, Oprah, Echo are AI PARTNERS — not assistants. The word is deliberate. We build AI that works WITH you as a genuine collaborator, not a tool you bark orders at.
*Tags: partners, personalities, david, deva, oprah, echo*

### OpenClaw vs Our Project
OpenClaw (formerly Clawdbot, briefly Moltbot) is an open-source AI agent project. Original name 'Clawdbot' (lobster claw + bot). Anthropic threatened to sue — too close to 'Claude'. Renamed Moltbot (lobster molting), then community settled on OpenClaw.
OUR project is now called 'The David Project' (TDP). Previously 'Clawdbot' as a placeholder. We do NOT use OpenClaw. We took useful architectural parts and separated from prompt-injection-vulnerable components. Safety-first, built from scratch.
*Tags: openclaw, moltbot, naming, security*

### Safety Requirements — NON-NEGOTIABLE
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

### David (Human) Is NOT a Programmer
Jono (0ld3ULL) is NOT a programmer. All instructions must be:
- Numbered steps, one action per step
- Exact text to type/paste in code blocks
- Say what app to open, what button to press
- No technical jargon without explanation
*Tags: jono, instructions, non-programmer*

### The David Score — AI scoring methodology for AIPulse
The core value prop of AIPulse.is. Problem: AI evolves too fast for savanna-plains human brains. People cant keep up with whats good and whats shit. Solution: The David Score — a set of criteria to hold against everything AI. Three indicators: (1) STATS/BENCHMARKS — like a car fact sheet. Starting with Big 6 (OpenAI, Anthropic, Gemini, DeepSeek, Llama, Grok). What is each good at? Writing, maths, design, science research. Crunch the benchmarks, report capabilities. Should be true, sometimes not quite but close enough. (2) INFLUENCER SENTIMENT — what industry YouTubers and TikTokers say. Can be bought, can be real, still a signal. Scraped from YouTube and TikTok. (3) CUSTOMER SENTIMENT — what actual users say after using it. How easy, how intuitive. Scraped from forums and Discord communities. Like CoinMarketCap used market cap as the one metric everyone agreed on for crypto traction.
*Tags: david-score, aipulse, scoring, sentiment, benchmarks*

### Memory Architecture — 3 Layer System
Session startup uses 3 layers: (1) Brief (~150 lines) — permanent knowledge (sig>=9) + active blockers (sig>=8) ONLY. No decisions, sessions, or historical info. (2) Session Index (session_index.md, 30 days) — bullet summaries of every session, auto-appended on save. Rebuild: python -m claude_memory index. (3) 48h full recall — read actual user messages from JSONL transcripts for last 2 days only. Older sessions searched on-demand via grep+jq. Target startup cost: ~13-17% context (down from ~30%). Usable window: ~38-42% before 55% cutoff.

### David Flip — The AI Founder Character
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

### Agent Roster
| Agent | Role | Status |
|-------|------|--------|
| David Flip | Content Creator — videos, tweets, research commentary | Active |
| Echo | Intelligence Analyst — research, monitoring | Active |
| Oprah | Operations — scheduling, posting, distribution, notifications | NEW |
| Deva | Game Developer — Unity/Unreal/Godot voice assistant | Standby |
*Tags: agents, david, echo, oprah, deva*

### Hardware Setup
Agent laptop: ASUS ROG Strix (i7-13650HX, 16GB DDR5, RTX 4060, 1TB NVMe)
Phone: NEW Android with NEW number (burner) for tethered internet
VPN: MANDATORY on both phone and laptop at all times
User is in UAE. All accounts created through VPN.
Main PC (i9-12900K + RTX 4070): Deva has ZERO access. Ever.
*Tags: hardware, laptop, rog, vpn, uae*

### VPS — David's Server
IP: 89.167.24.222 | Provider: Hetzner | CPX42 8 vCPU 16GB RAM
Location: Helsinki | Cost: ~$27/month | OS: Ubuntu 24.04
Service: systemctl status david-flip | Code: /opt/david-flip/
SSH: ssh root@89.167.24.222
Dashboard: http://89.167.24.222:5000/
*Tags: vps, hetzner, server, ssh*

### David Flip Accounts
Twitter/X: @David_Flipt (API working, pay-per-use, $24.97 credits)
YouTube: Channel ID UCBNP7tMEMf21Ks2RmnblQDw (OAuth verified)
Telegram: @DavidFliptBot (running 24/7 on VPS)
Email: davidflip25@proton.me
Website: https://flipt.ai
Google Cloud Project: ALICE (alice-481208)
Twitter Dev App: 'DavidAI' on console.x.com
*Tags: accounts, twitter, youtube, telegram*

### Supadata API
Key: sd_d826ccdab9a7a682d5716084f28d4d73
Endpoint: https://api.supadata.ai/v1/transcript (unified — works for YouTube AND TikTok)
Header: x-api-key
Params: url, text=true for plain text
*Tags: supadata, api, transcripts, tiktok, youtube*

### Identity rules NOT persisting on VPS
CRITICAL: The identity calibration system (commit 7f8602f) is implemented in code but knowledge.db on VPS is EMPTY - zero identity rules stored. When Jono rejects tweets, rules should be distilled and stored permanently via KnowledgeStore. Either feedback handler not running, files not picked up, or rules never stored. This is the core learning loop for David personality. Jono considers this MAJOR. Must verify feedback pipeline works end-to-end on VPS every session.
*Tags: identity, vps, bug, critical*

## Active Blockers & State

### I am Claude D — on the D computer
I am Claude D, the Claude Code instance running on the D computer (ASUS ROG laptop, i7-13650HX, RTX 4060, 16GB RAM, Windows 11). This is the dedicated autonomous AI workstation. Working directory: C:\Projects\Clawdbot (folder rename to TheDavidProject pending). The D computer is separate from Jono main PC. Claude D handles Pixel agent development and Deva voice assistant.
*Tags: claude-d, identity, d-computer, laptop*

### Pixel renamed to Occy — Software Vision Specialist
Agent formerly known as Pixel is now OCCY (from ocular — the one who sees). Software Vision Specialist who can learn any software by seeing the screen. Currently assigned to Focal ML (video production). Architecture is platform-agnostic — Deva and David can request Occy to learn new tools. Files: personality/occy.py (OccyPersonality), agents/occy_agent.py (OccyAgent), agents/occy_browser.py (FocalBrowser), agents/occy_learner.py (OccyLearner), agents/occy_producer.py (OccyProducer), agents/occy_reviewer.py (OccyReviewer), occy_main.py (OccySystem). Data: data/occy_*.db, data/occy_browser_profile/, data/occy_transcripts/. Entry point: python occy_main.py --visible --explore 5
*Tags: occy, rename, vision, agent-roster*

### Git identity not configured on Davids machine
Git user.name and user.email are not set on the David computer (DESKTOP-9S55RR6). Cannot commit or push from here. 13 files are STAGED for the Echo Intelligence Upgrade commit. Commit message saved in commit_msg_echo.txt. Jono needs to either: set git identity here, or commit/push from his PC via Claude J.

### Project Phase
Phase 1 BUILD IN PROGRESS. Foundation code written, needs API keys and testing.
Local development on ASUS ROG laptop at C:\Projects\TheDavidProject
VPS running at 89.167.24.222 (code at /opt/david-flip/)
*Tags: phase1, build*

### Oprah — Not Yet Wired
Oprah's files are created (personality/oprah.py, agents/operations_agent.py) and dashboard updated. But main.py still uses the OLD methods directly.
TODO: Import OperationsAgent in main.py, create instance after Telegram init, delegate execute_action() and poll_dashboard_actions() to Oprah.
Also register Oprah's _execute_scheduled_video with ContentScheduler.
*Tags: oprah, wiring, main.py, todo*

### Research Agent — Built, Not Deployed
Research agent built in agents/research_agent/ with 4 scrapers (RSS, GitHub, Reddit, YouTube) + transcript scraper + evaluator.
NOT YET deployed to VPS. Needs: pip install, copy files, restart.
*Tags: research, deploy, vps, todo*

---
## Memory Commands
```
python -m claude_memory brief          # Regenerate this file
python -m claude_memory index          # Rebuild 30-day session index
python -m claude_memory status         # Memory stats
python -m claude_memory add <cat> <sig> "title" "content"
python -m claude_memory search "query" # Search memories
python -m claude_memory decay          # Apply decay manually
```
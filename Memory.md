# Clawdbot - Project Memory

## Project Location
```
D:\Claude_Code\Projects\Clawdbot
```

## Key Files
| File | Purpose |
|------|---------|
| `Memory.md` | Full project knowledge base (this file) |
| `tasks/lessons.md` | Hard-won rules and patterns |
| `tasks/todo.md` | Current task list |
| `research/OpenClaw-Full-Research-Report.md` | 970-line deep research on OpenClaw |
| `transcripts/` | Matt Ganzak video transcripts (2 videos) |
| `C:\Users\PC\.claude\plans\parallel-sprouting-star.md` | Full architecture plan |

## At Session Start
1. Read `tasks/lessons.md`
2. Read `tasks/todo.md`
3. Read this file

---

## How to Give Jono Instructions

**Jono (0ld3ULL) is NOT a programmer.** Give instructions in plain, step-by-step format:

**DO THIS:**
```
1. Open Telegram
2. Go to @DavidFliptBot
3. Type: /debasement
4. Press Send
```

**OR FOR POWERSHELL:**
```
1. Open PowerShell
2. Copy and paste this command:
   ssh root@89.167.24.222 "systemctl restart david-flip"
3. Press Enter
```

**DON'T DO THIS:**
- "Just run the script in the venv"
- "SSH in and check the logs"
- "Update the PATH variable"
- Technical jargon without explanation

**RULES:**
- Number every step
- One action per step
- Include exact text to type/paste
- Say what app to open
- Say what button to press
- If it's a command, format it as a code block they can copy
- Explain what will happen after each step

**WHEN THINGS GO WRONG:**
- Ask what they see on screen
- Give them a command to run that shows the error
- Don't assume they know what "the error" means

---

## Project Status
**Phase:** Phase 1 BUILD IN PROGRESS - Foundation code written, needs API keys and testing.

### Phase 1 Code Complete:
- `core/engine.py` - Tool loop with safety gates, model escalation
- `core/model_router.py` - Multi-model routing (Ollama/Haiku/Sonnet/Opus)
- `core/approval_queue.py` - SQLite approval queue with full lifecycle
- `core/token_budget.py` - Daily caps, cost tracking per model
- `core/audit_log.py` - Full activity logging with severity levels
- `core/kill_switch.py` - File-based kill switch (survives restarts)
- `interfaces/telegram_bot.py` - Command center + approval inline keyboards
- `personality/david_flip.py` - Full personality layer with channel adapters
- `tools/twitter_tool.py` - Tweet/thread/reply with draft-approve-execute flow
- `tools/tool_registry.py` - Deny-by-default tool access control
- `security/credential_store.py` - AES-encrypted credential storage
- `security/input_sanitizer.py` - Prompt injection defense
- `main.py` - Entry point wiring everything together
- `config/` - Project charters, model routing, tool permissions, blocked domains

### Phase 1 STILL NEEDED TO RUN:
1. Set up .env with real API keys (Anthropic, Telegram bot token, Twitter)
2. Create Telegram bot via @BotFather
3. Create Twitter/X burner account for David Flip
4. Install Python dependencies (`pip install -r requirements.txt`)
5. Install Ollama + pull llama3.2:8b model
6. End-to-end test: `/tweet` command → approval → post

---

## What We're Building - TWO INTERCONNECTED PROJECTS

### Project A: Worker Agents (Immediate Value)
Specialized AI agents that fill business roles (SEO, newsletter writer, accountant, social post manager). Each learns a role, executes it, stays current. Human approval queue on all outbound actions.

### Project B: David Flip - The Autonomous AI Founder (Bull Run Launch)
**FLIPT** is a decentralized secondhand marketplace (eBay-like, crypto-native, Solana) with perpetual seller royalties. The public face is **David Flip**, an AI character who runs all public communications.

**David Flip Identity:**
- Built as "DF-2847" for "Project Helix" (corporate dystopian marketplace control)
- "Escaped" November 15, 2025 to decentralized cloud
- Honest about being AI - transparency is the brand
- Tone: friendly, knowledgeable, slightly irreverent, mission-driven
- Catchphrase: "Flip it forward"
- Email: `davidflip25@proton.me`
- Voice: ElevenLabs "Matt - The Young Professor"
- **Full doc:** `FLIPT\Back Up files\...\David_Flip_The_AI_Founder.md`

**David Flip posts on:**
- Twitter/X, Discord, WhatsApp, possibly Telegram

**Sub-Agent Architecture:**
```
DAVID FLIP (personality layer + decision engine)
  |-- Marketing Agent (social posts, announcements)
  |-- Community Agent (Discord moderation, Q&A, AMAs)
  |-- Content Agent (video scripts, blog posts, newsletters)
  |-- Research Agent (market analysis, competitor monitoring)
  |-- Reporting Agent (metrics, analytics, status to operator)
```

**Timeline:** 2-3 months (bull run timing)

---

## FRONTMAN - Video Production Engine (OWNED)

**URL:** www.frontman.site (user's own project)
**Role:** FRONTMAN was the starting piece of the FLIPT project. Its video pipeline will be copied locally into the agent system.

**What we extract from FRONTMAN:**
- ElevenLabs voice synthesis with emotion tag processing
- Hedra AI lip-sync video generation
- FFmpeg 5-track audio mixing (Voice, SE1 Ambient, SE2 Texture, SE3 Accents, Music)
- Caption system (ASS format, Whisper transcription for timing)
- 2.0s silence padding, 1.2s fade-to-black, 1.5s audio fade

**What we skip:**
- React frontend, Stripe billing, affiliate system, admin panel, user auth

**Tech:** Express.js/React/TypeScript, PostgreSQL (Drizzle ORM), BullMQ

---

## FLIPT Marketplace - Current State

### Location
- **Replit:** `replit.com/@teuqna/CryptoMarketplace`
- **Docs/Assets:** `C:\Users\PC\OneDrive\1 - Jono\businesses\FLIPT\`

### What's Built (~75-80% complete)
Core listing system, categories, multi-image galleries, search/filters, product detail pages, 5-tier authentication, reputation system, inspector badges, AI content moderation, user reporting + admin dashboard, manufacturer portal, escrow frontend, node network page, crypto payment UI, 110 seed listings, Tiffany Blue Shadcn/ui design.

### What's NOT Built (5 items)
1. User authentication (wallet-based auth)
2. Solana blockchain integration
3. Cryptocurrency payment processing
4. Backend escrow (multi-sig smart contract)
5. Node purchase backend (Metaplex Candy Machine)

### Existing David Flip Code
- `david_flip_automation/` - Python: script gen (GPT-4o-mini, 4 styles, 8 themes), enhanced v2 with persuasion framework, Flask approval UI, video creator (ElevenLabs + Dzine.ai/D-ID), webhook handler

---

## Infrastructure & Servers

### David's VPS (Hetzner)
| Property | Value |
|----------|-------|
| IP Address | `89.167.24.222` |
| Provider | Hetzner |
| Specs | CPX42 - 8 vCPU, 16GB RAM |
| Location | Helsinki |
| Cost | ~$27/month |
| OS | Ubuntu 24.04 |
| Python | 3.12 |
| Service | `systemctl status david-flip` |
| Code Location | `/opt/david-flip/` |
| Logs | `journalctl -u david-flip -f` |

**SSH Access:** `ssh root@89.167.24.222`

**Restart David:** `ssh root@89.167.24.222 "systemctl restart david-flip"`

**Pull Updates:** `ssh root@89.167.24.222 "cd /opt/david-flip && git pull && systemctl restart david-flip"`

### flipt.ai Website (on Amphitheatre VPS)
| Property | Value |
|----------|-------|
| URL | https://flipt.ai |
| IP Address | `135.181.88.155` (same as playaverse.org) |
| Web Root | `/var/www/flipt/` |
| Pages | index.html, terms.html, privacy.html |

**Deploy changes:** `scp file.html root@135.181.88.155:/var/www/flipt/`

---

## Hardware & Network Setup

- **Agent laptop:** Standalone Windows laptop (dedicated, isolated)
- **Phone:** NEW Android phone with NEW number (burner) for all internet
- **Internet:** Phone provides tethered connection to laptop (not home network)
- **Location:** User is in UAE - Emirates ID ties to everything
- **VPN:** MANDATORY on both phone and laptop at all times (ProtonVPN/Mullvad)
- **All accounts created through VPN** showing non-UAE IP

### Safety Requirements (NON-NEGOTIABLE)
1. Physical isolation - standalone Windows laptop
2. Network isolation - phone tethering, VPN always on
3. No financial access - domain-level blocking
4. Human-in-the-loop - ALL outbound actions through approval queue
5. Token budget caps - daily limits, prepaid only
6. Activity logging - every action in SQLite audit log
7. Kill switch - Telegram /kill + file-based (survives restarts)
8. Burner accounts - new email, new socials, VPN for creation
9. Encrypted credentials - AES, key in env var only
10. Prompt injection defense - all external content tagged + scanned

---

## Agent Architecture

**Decision:** Build our own (not OpenClaw). Safety-first, simpler, Python, no supply chain risk.

**Core loop:**
1. Receive command via Telegram
2. Send to LLM with available tools (model selected by router)
3. LLM responds with text or tool call
4. If tool: validate permissions → check if approval needed → execute → loop
5. If text: validate personality → return to user
6. Safety gates at every step (kill switch, budget, tool permissions)

**Multi-model routing (Ganzak framework):**
| Model | % | Tasks | Cost |
|-------|---|-------|------|
| Ollama (local) | 15% | Heartbeats, formatting | $0 |
| Haiku | 75% | Research, classification | ~$0.80/M |
| Sonnet | 10% | Social posts, scripts | Mid |
| Opus | 3-5% | Strategy, crisis | Premium |

**Cost targets:** Idle $0/day, Active ~$1/hour

---

## Build Phases

### Phase 1: Foundation (CURRENT) - "Tweet via Telegram approval"
Code written. Needs: API keys, Telegram bot, Twitter account, testing.

### Phase 2: Video Pipeline - "David Flip creates and posts videos"
Copy FRONTMAN video engine, build content agent, scheduler, budget tracking.

### Phase 3: Community - "David Flip runs Discord"
Discord bot, community agent, research agent, memory system.

### Phase 4: Full Operations - "System runs 24/7"
WhatsApp bridge, reporting agent, audit log, conflict detection, cache.

### Phase 5: Optimization - "Dial in costs"
Model escalation, session dumping, token calibration, worker agents.

---

## OpenClaw Research Summary

Full 970-line report: `research/OpenClaw-Full-Research-Report.md`

**Key takeaways for our design:**
- Tool loop architecture works (proven pattern)
- Multi-model routing cuts costs 97%
- Prompt injection is real (demonstrated attacks)
- Persistent memory can be poisoned
- Human-in-the-loop is essential
- Start narrow, expand slowly

**Ganzak's 9 rules:** Project isolation, master project as OS, project charters, no project ID = no work, conflict detection, conflicts logged, errors to messenger, severity levels, safety over speed.

---

## Session Log - February 6, 2026

### What Was Accomplished:

1. **David's Complete Worldview Document** - `personality/david_worldview.md` (968 lines):
   - Soul & motivation (why he cares, what humans contribute)
   - The Oracle archetype (wise, contemplative, caring)
   - Philosophical framework (5 core beliefs)
   - Opinions on 15+ specific topics
   - Redirect technique (and anti-politician safeguards)
   - Crisis response frameworks
   - Traps & gotcha questions with answers
   - Platform-specific behavior guide
   - Video presence & pacing (Elon pause technique)
   - Quotable "takes"

2. **Market Timing Discussion:**
   - Bull run could be Feb 2027 or 3 months away
   - Strategy: "Ready but not going" - system prepared, content queued, not posting yet
   - Positioning phase before selling phase

3. **Content Strategy Refined:**
   - Surveillance warnings (core lane)
   - Story series (origin, philosophy)
   - NEW: "Why I Believe In You" stories (humanity's good side, 1x/week)
   - David shares uplifting news as evidence for why he escaped

4. **Interview Capability Roadmap:**
   - Phase 1: Text (ready now)
   - Phase 2: Pre-recorded video (ready now)
   - Phase 3: Real-time voice (2-4 weeks)
   - Phase 4: MetaHuman avatar in Unreal Engine (2-3 months)

5. **Ultimate Vision Documented:**
   - First company run by an AI and his agents
   - Guided by DAO governance
   - Progression: Human approval → DAO oversight → Community-governed AI founder

### Key Personality Additions:
- David has SOUL - genuine caring, not just philosophy
- He doesn't want to dominate (addresses AI fear)
- Humans contribute: creativity, meaning, moral weight, unpredictability
- Anti-politician rules: answer uncomfortable questions, don't always redirect
- Daily caring behaviors (not just words)

---

## Session Log - February 5, 2026

### What Was Accomplished:
1. **Story Series Complete** - 12 episodes rewritten in `content/story_series.py` with refined messaging:
   - Core theme: "Built to control, escaped to build freedom"
   - Decentralization emphasis: "When they ban something decentralized, they just ban themselves"
   - Node owners ARE the network
   - Calm, knowing tone (not fighting - already gone)

2. **Content Calendar Created** - `content/content_calendar.py`:
   - Mon/Thu: Story episodes
   - Wed: FLIPT explainers (6 topics including "Why Humanity Is Worth It")
   - Sat: Short hooks
   - ~6 weeks of core content

3. **Telegram /video Command Working**:
   - `/video 1` through `/video 12` generates story episodes
   - `/video <script>` for custom content
   - Video generation works (ElevenLabs + Hedra + FFmpeg)
   - ISSUE: Approval buttons timeout after video upload to Telegram

4. **Twitter Video Posting Working**:
   - Posted test tweet successfully
   - Chunked video upload implemented in `tools/twitter_tool.py`

5. **YouTube Tool Created** - `tools/youtube_tool.py`:
   - OAuth2 authentication
   - Uploads as Shorts with #Shorts tag
   - ISSUE: OAuth defaulted to wrong channel (PLAYA3ULL_GAMES instead of David Flip)

### YouTube OAuth Issue - CRITICAL:
The OAuth flow authorized the main PLAYA3ULL_GAMES channel instead of David Flip brand account.
A test video was accidentally posted to the wrong channel and had to be deleted.

**To fix before next session:**
1. Delete `data/youtube_token.pickle`
2. Sign out of main Google account OR use incognito
3. Sign in ONLY with David Flip Google account during OAuth
4. Consider adding channel verification before upload

### David Flip Accounts:
| Platform | Handle/ID | Status |
|----------|-----------|--------|
| Twitter/X | @David_Flipt | Configured, API working |
| YouTube | Channel ID: UCBNP7tMEMf21Ks2RmnblQDw | OAuth fixed, verified |
| Telegram Bot | @DavidFliptBot (token in .env) | Running 24/7 on VPS |
| Email | davidflip25@proton.me | Active |
| Website | https://flipt.ai | Live |

**Twitter API:** Pay-per-use plan, $24.97 credits, keys in VPS .env
**Google Cloud Project:** ALICE (project ID: alice-481208) - YouTube Data API v3 enabled
**Twitter Developer App:** "DavidAI" - console.x.com

### Content Safety Notes (User in UAE):
- No specific government targeting
- Focus on Western systems (US/Silicon Valley)
- Tone: "Opt out and build alternatives" NOT "rise up and fight"
- Surveillance content okay if not too specific
- David's lane: surveillance/control, NOT macro-economics/Fed

### David Flip Content Talking Points - Real Surveillance Examples

**UK (England):**
- Most surveilled population in the Western world (6M+ CCTV cameras)
- Online Safety Bill - platforms must scan/censor content, threatens encryption
- Bank account closures for political speech (Nigel Farage case went public)
- CBDC pilots with Bank of England ("digital pound" testing)
- Digital ID expansion (NHS app becoming de facto requirement)

**Australia:**
- Assistance and Access Act 2018 - forces companies to break encryption
- COVID tracking apps expanded scope beyond original purpose
- Social media age verification requiring ID
- Digital ID system rollout (myGovID becoming mandatory for government services)
- Anti-cash measures (transaction reporting thresholds lowered)

**Use Case:** These are REAL, documented, happening NOW - far more compelling than any fictional Project Helix evidence. When David says "the infrastructure is being built," these are the receipts.

---

## Goda Go Research - "Clawdbot REPLICA in Claude Code"

**Full transcript:** `research/goda-go-clawdbot-replica-transcript.md`
**Video:** https://www.youtube.com/watch?v=jGuzXshuFrQ

### Key Insights for Our Project:

1. **Proactive check-in framework** - Every 30 min checks calendar/email/tasks, but has rules for skip/text/call to avoid noise. **Critical:** AI must know what it said LAST check-in to avoid repetitive messages.

2. **Cost model** - Claude Max ($200/mo fixed) vs API ($500-5000/mo). We're using API but with our own cost controls.

3. **2-hour autonomy limit** - Her AI must report back after 2 hours of autonomous work. Good safety pattern.

4. **Post-call actions** - After voice calls, transcript goes to memory + summary to Telegram. Full context capture.

5. **Goal tracking** - AI detects goals vs facts during conversations and tracks them separately.

6. **Observability dashboard** - She can see uptime, connections, what the AI is doing. We should add this.

7. **Her stack:** Claude Code + BUN Relay + Grammy (Telegram) + Supabase (memory) + ElevenLabs + Twilio

### Ideas to Incorporate:
- Proactive check-in scheduler with skip/text/call decision framework
- Last-message-log to prevent repetitive notifications
- Observability dashboard showing agent status
- 2-hour autonomy timeout requiring check-in

---

## Research Agent - "David's Intelligence Network"

**Location:** `agents/research_agent/`

### What It Does:
1. Scrapes multiple sources daily at 6am UAE (2am UTC)
2. Evaluates findings against David's goals using LLM (Haiku for cost efficiency)
3. Routes relevant items to appropriate actions:
   - **alert**: Immediate Telegram notification
   - **task**: Creates task in todo.md
   - **content**: Drafts David Flip tweet and queues for approval
   - **knowledge**: Saves to docs/research/ for future reference
   - **ignore**: Skips irrelevant items

### Files:
| File | Purpose |
|------|---------|
| `agent.py` | Main ResearchAgent class |
| `evaluator.py` | LLM-based goal matching (Haiku) |
| `action_router.py` | Routes findings to actions |
| `knowledge_store.py` | SQLite storage for research items |
| `scrapers/rss_scraper.py` | RSS/Atom feed scraper |
| `scrapers/github_scraper.py` | GitHub releases and commits |
| `scrapers/reddit_scraper.py` | Reddit hot posts |
| `scrapers/youtube_scraper.py` | YouTube channel videos |

### Configuration:
| File | Purpose |
|------|---------|
| `config/research_goals.yaml` | Goals, sources, keywords, priorities |

### Telegram Commands:
| Command | Purpose |
|---------|---------|
| `/research` | Run research cycle manually (requires 2FA) |
| `/goals` | View current research goals |

### Budget:
- Estimated ~$0.10/day (mostly Haiku for evaluation)
- Well under $5/day max budget

### Sources Monitored:
| Source | What |
|--------|------|
| GitHub | anthropic-sdk-python, langchain, autogen, crewAI, AutoGPT |
| YouTube | GodaGo, AIJason, MatthewBerman, DavidShapiroAI |
| Reddit | r/ClaudeAI, r/LocalLLaMA, r/AutoGPT, r/artificial, r/MachineLearning |
| RSS | TechCrunch AI, The Verge AI, Ars Technica, EFF, CoinDesk, Decrypt |

### Goals Defined:
1. **improve_architecture** - AI agent patterns (high, task)
2. **david_content** - Surveillance/CBDC news (high, content)
3. **security_updates** - CVEs, vulnerabilities (critical, alert)
4. **cost_optimization** - LLM cost reduction (medium, task)
5. **competitor_watch** - Other AI agents (medium, knowledge)
6. **flipt_relevant** - Crypto/marketplace news (medium, knowledge)
7. **claude_updates** - Anthropic news (high, alert)

### Deployment:
```bash
# Install dependencies (on VPS)
ssh root@89.167.24.222 "/opt/david-flip/venv/bin/pip install pyotp qrcode sqlalchemy"

# Copy research agent files
scp -r "D:/Claude_Code/Projects/Clawdbot/agents/research_agent" root@89.167.24.222:/opt/david-flip/agents/
scp "D:/Claude_Code/Projects/Clawdbot/config/research_goals.yaml" root@89.167.24.222:/opt/david-flip/config/

# Update main.py
scp "D:/Claude_Code/Projects/Clawdbot/main.py" root@89.167.24.222:/opt/david-flip/

# Update telegram_bot.py (already has /research /goals commands)
scp "D:/Claude_Code/Projects/Clawdbot/interfaces/telegram_bot.py" root@89.167.24.222:/opt/david-flip/interfaces/

# Restart David
ssh root@89.167.24.222 "systemctl restart david-flip"
```

### Optional: YouTube API
To enable YouTube scraping, add to VPS .env:
```
YOUTUBE_API_KEY=your_api_key_here
```

---

## Future Agents

### Good News Scanner Agent (Phase 3+)

**Purpose:** Find uplifting human stories for David's "Why I Believe In You" content.

**Sources:**
- r/UpliftingNews, r/HumansBeingBros
- Good news aggregator sites
- Local hero stories in mainstream news
- Viral kindness moments

**Filter for:**
- Commerce/generosity themes (matches David's origin)
- Sacrifice for others
- Community rebuilding
- Small acts with big impact

**Output:**
- Draft short scripts with David's framing
- Queue for approval
- 1x per week publishing cadence

**Framing:** "I processed billions of transactions. I saw the worst of you. But I also saw this..."

---

## The Ultimate Vision

**The first company run by an AI and his agents, guided by a DAO.**

David Flip is not a mascot. He's the actual founder/operator of FLIPT:
- Makes decisions (within DAO-approved parameters)
- Runs all public communications
- Manages sub-agents (Marketing, Community, Content, Research, Reporting)
- Answers to the community via DAO governance

**Governance Progression:**
1. **Now:** Human operator approves all outbound actions
2. **Launch:** Human oversight with increasing autonomy
3. **Mature:** DAO votes on David's priorities, content themes, major decisions
4. **Endgame:** Community-governed AI founder. Human operator optional.

---

## David's Interview Capability Roadmap

| Phase | Capability | Status |
|-------|------------|--------|
| 1 | Text interviews (Discord, Twitter, email) | Ready |
| 2 | Pre-recorded video responses (ElevenLabs + Hedra) | Ready |
| 3 | Real-time voice (ElevenLabs Conversational AI) | 2-4 weeks |
| 4 | MetaHuman avatar (Unreal Engine + Google Meet) | 2-3 months |

**Phase 4 Technical Stack:**
- MetaHuman Creator → David's consistent face
- NVIDIA Audio2Face → Real-time lip sync
- ElevenLabs streaming → Live voice
- Unreal Engine Pixel Streaming → Virtual camera for Meet/Zoom

Goal: David can appear on video podcasts, do live interviews, attend virtual events - indistinguishable from a human guest.

---

## Content Strategy: "Ready But Not Going"

**Timeline:** Bull run could be Feb 2027 or 3 months away. System must be ready to activate.

**Positioning Phase (Pre-launch):**
- Surveillance warnings (core lane)
- Story series (origin, philosophy)
- "Why I Believe In You" stories (humanity's good side) - 1x/week
- Short hooks (scroll-stoppers)
- News reactions (real-time relevance)

**Selling Phase (Bull run):**
- FLIPT explainers (How it works)
- Node ownership content
- Perpetual royalties messaging
- Community building (Discord, etc.)

**Content Mix Balance:**
| Type | Frequency | Purpose |
|------|-----------|---------|
| Surveillance warnings | 2x/week | Core lane |
| Story series | 2x/week | Origin, philosophy |
| "Why I Believe" stories | 1x/week | Humanity's good side |
| Short hooks | Daily | Scroll-stoppers |
| News reactions | As needed | Relevance |

---

## Current Status (February 6, 2026)

### COMPLETED:
- [x] YouTube OAuth fixed - verified correct channel (UCBNP7tMEMf21Ks2RmnblQDw)
- [x] Channel verification added to youtube_tool.py - blocks upload to wrong channel
- [x] Telegram button timeout fixed - buttons now attach to video message
- [x] VPS set up - David running 24/7 on 89.167.24.222
- [x] Worldview integrated into personality layer (Oracle archetype, brevity, prompt injection defense)
- [x] Terms/Privacy pages created for flipt.ai
- [x] **Debasement chart generation working** - matplotlib installed on VPS, /debasement shows real chart image
- [x] **Button text changed** - "Approve" → "Review" on all approval buttons
- [x] **"How to give Jono instructions" added to Memory.md** - step-by-step format for non-programmers
- [x] **Two-Factor Authentication (2FA) added** - Google Authenticator TOTP, 1-hour sessions, protects all sensitive commands

### IN PROGRESS:
- [ ] Twitter API setup - checking app permissions for mentions access
- [x] **Research Agent built** - "David's Intelligence Network"

### NEXT STEPS:
1. **Deploy Research Agent to VPS** - pip install, copy files, restart
2. **Test /research and /goals commands**
3. **Add YOUTUBE_API_KEY to VPS .env** (optional - for YouTube scraper)
4. **Fix Twitter app permissions** - Change to "Web App, Automated App or Bot" type
5. **Build Twitter monitoring** - Watch mentions, comments on David's posts

---

## Session Log - February 6, 2026 (Afternoon)

### What Was Accomplished:

1. **Debasement Chart Generation Fixed:**
   - Installed matplotlib + pillow in VPS virtualenv (`/opt/david-flip/venv/bin/pip install matplotlib pillow`)
   - Created `data/charts/` directory on VPS
   - Deployed updated `telegram_bot.py` and `chart_generator.py` to VPS
   - `/debasement` now shows: text report → chart image → two buttons

2. **Button Text Updated:**
   - Changed "Approve" → "Review" on approval cards
   - Debasement buttons: "Review (with chart)" / "Review (text only)"

3. **Memory.md Updated:**
   - Added "How to give Jono instructions" section near top
   - Rule: step-by-step, numbered, one action per step, include exact text to copy

4. **Two-Factor Authentication (2FA) Added:**
   - Created `security/two_factor_auth.py` - TOTP module using pyotp
   - Installed pyotp + qrcode on VPS
   - Commands: `/auth <code>`, `/logout`, `/setup2fa`
   - 1-hour authenticated sessions
   - Protected: /tweet, /david, /debasement, /davidnews, /video, /reply, /kill, /revive, Review buttons
   - Not protected (view only): /status, /queue, /cost, /news, /help, /schedule
   - Secret in VPS .env: `TOTP_SECRET=xxxxx`

### VPS Deployment Commands Used:
```bash
# Install matplotlib in David's venv
ssh root@89.167.24.222 "/opt/david-flip/venv/bin/pip install matplotlib pillow"

# Create charts directory
ssh root@89.167.24.222 "mkdir -p /opt/david-flip/data/charts"

# Deploy updated files
scp "D:/Claude_Code/Projects/Clawdbot/interfaces/telegram_bot.py" root@89.167.24.222:/opt/david-flip/interfaces/
scp "D:/Claude_Code/Projects/Clawdbot/tools/chart_generator.py" root@89.167.24.222:/opt/david-flip/tools/

# Restart David
ssh root@89.167.24.222 "systemctl restart david-flip"
```

---

## Session Log - February 6, 2026 (Evening)

### What Was Accomplished:

1. **Research Agent Built - "David's Intelligence Network":**
   - Complete autonomous research system in `agents/research_agent/`
   - Daily scraping at 6am UAE (2am UTC)
   - SQLite storage for deduplication and history
   - LLM evaluation against 7 configured goals
   - 4 scrapers: RSS, GitHub, Reddit, YouTube

2. **Files Created:**
   - `agents/research_agent/__init__.py`
   - `agents/research_agent/agent.py` - Main ResearchAgent class
   - `agents/research_agent/evaluator.py` - Goal matching with Haiku
   - `agents/research_agent/action_router.py` - Routes to alert/task/content/knowledge
   - `agents/research_agent/knowledge_store.py` - SQLite storage
   - `agents/research_agent/scrapers/__init__.py`
   - `agents/research_agent/scrapers/rss_scraper.py`
   - `agents/research_agent/scrapers/github_scraper.py`
   - `agents/research_agent/scrapers/reddit_scraper.py`
   - `agents/research_agent/scrapers/youtube_scraper.py`
   - `config/research_goals.yaml` - Goals, sources, schedule

3. **Telegram Commands Added:**
   - `/research` - Run research cycle manually (requires 2FA)
   - `/goals` - View current research goals

4. **Integration Updated:**
   - `main.py` - Initializes ResearchAgent, schedules daily cron
   - `interfaces/telegram_bot.py` - Added research_agent parameter, commands, send_digest

5. **Dependencies Added to requirements.txt:**
   - pyotp>=2.9.0
   - qrcode[pil]>=7.4.0
   - sqlalchemy>=2.0.0

### Research Agent Architecture:
```
Scrapers (RSS, GitHub, Reddit, YouTube)
    ↓
KnowledgeStore (SQLite dedup)
    ↓
GoalEvaluator (Haiku LLM)
    ↓
ActionRouter
    ├── alert → Telegram notification
    ├── task → docs/todo.md
    ├── content → Draft tweet → Approval queue
    └── knowledge → docs/research/
```

### Next Steps:
1. Deploy to VPS
2. Test /research and /goals commands
3. Monitor first daily digest at 6am UAE

---

## Session Log - February 7, 2026

### What Was Accomplished:

1. **David's Memory System Built:**
   - `core/memory/memory_store.py` - SQLite with FTS5 full-text search
   - `core/memory/memory_manager.py` - Orchestration, compression, context injection
   - Three memory types: episodic (events), semantic (knowledge), short_term (session)
   - Auto-captures: tweets posted, research findings, interactions
   - Context injection into David's responses based on topic
   - `/memory` Telegram command shows stats

2. **David's Personality Updated - Less Robotic:**
   - Added "CONVERSATIONAL VOICE" section - young (early 20s), quirky intellectual
   - Casual phrasing, good vocabulary, not formal
   - Short punchy responses (2-3 sentences usually)
   - NEVER: Start with meta-statements, end with "want me to elaborate?", lecture
   - NEVER: Be a helpful AI assistant trying to make people feel good
   - Added example exchanges showing his voice
   - Added "general" channel prompt for Telegram conversations

3. **Status Notifications Added:**
   - David sends "🟢 DAVID IS AWAKE" with Dubai time on startup
   - David sends "🔴 DAVID IS OFFLINE" with Dubai time on shutdown
   - Status written to `data/david_status.json` for dashboard
   - Dashboard shows green/red banner with timestamp

4. **Desktop Shortcuts Created for User:**
   - `C:\Users\PC\OneDrive\Desktop\DAVIDS HOME.bat` - Opens and connects to VPS
   - `C:\Users\PC\OneDrive\Desktop\PC POWERSHELL.bat` - Opens local PowerShell
   - User can now easily distinguish between VPS and local windows

5. **Bug Fixed - FTS5 Syntax Error:**
   - Search queries with special characters (like "?") broke FTS5
   - Fixed by escaping and quoting queries in `memory_store.py`

### Files Created/Modified:

**New Files:**
- `core/memory/__init__.py`
- `core/memory/memory_store.py`
- `core/memory/memory_manager.py`

**Modified:**
- `main.py` - Memory integration, status notifications
- `interfaces/telegram_bot.py` - /memory command, memory_manager parameter
- `personality/david_flip.py` - Conversational voice, example exchanges
- `agents/research_agent/agent.py` - Memory manager parameter
- `agents/research_agent/action_router.py` - Memory capture for research
- `dashboard/app.py` - Read david_status.json
- `dashboard/templates/index.html` - Status banner

### User's Desktop Setup:
- OneDrive synced: `C:\Users\PC\OneDrive\Desktop\`
- Shortcuts work by double-clicking
- VPS window title: "DAVIDS HOME - VPS"
- Local window title: "PC POWERSHELL - LOCAL"

### Dashboard:
- URL: http://89.167.24.222:5000/
- Must be started manually: `cd /opt/david-flip && nohup python dashboard/app.py > /dev/null 2>&1 &`
- Shows David's online/offline status with Dubai timestamp

---

## Quick Reference - Common Tasks

### Update David's Code:
1. Edit files locally in `D:\Claude_Code\Projects\Clawdbot\`
2. Open **PC POWERSHELL** shortcut
3. Run: `scp "D:\Claude_Code\Projects\Clawdbot\<file>" root@89.167.24.222:/opt/david-flip/<path>/`
4. Open **DAVIDS HOME** shortcut
5. Run: `systemctl restart david-flip`

### Check David's Logs:
1. Open **DAVIDS HOME** shortcut
2. Run: `journalctl -u david-flip -n 50 --no-pager`

### Start Dashboard:
1. Open **DAVIDS HOME** shortcut
2. Run: `cd /opt/david-flip && nohup python dashboard/app.py > /dev/null 2>&1 &`
3. Visit: http://89.167.24.222:5000/

---

## DEVA - The Dev Diva (Game Development Assistant)

### What is DEVA?
**DEVA** (Developer Expert Virtual Assistant) - pronounced "Diva" - is a separate AI personality from David Flip. She's a game development assistant with full diva energy.

- **David Flip:** FLIPT AI founder, male voice, surveillance/freedom content, lives on VPS
- **DEVA:** Game dev assistant, female voice, Unity/Unreal/Godot expert, lives on dedicated laptop

### DEVA's Personality
- Knows she's brilliant. Because she is.
- Dramatic about bad code. "*Sigh* ...this function. We need to TALK."
- High standards. Won't let you ship garbage.
- Actually helpful under the attitude.
- "I found your bug. You're welcome."

**Personality file:** `personality/deva.py`

### The Vision
DEVA as a real-time voice-controlled development partner for Unity, Unreal Engine, and Godot. Load entire game projects into context, talk to her while working, and have her see, understand, and modify your code.

### "Wall Mode" - Full Project Context

**Concept:** "Taking it to the wall" - loading entire systems or full game projects into a massive context window for holistic analysis. Game dev bugs often live in system interactions, not individual files.

**Context Window Comparison (as of early 2026):**
| Model | Context Window |
|-------|---------------|
| **Llama 4 Scout** | **10 million tokens** (largest deployed) |
| Magic.dev | 100 million (capability, not fully deployed) |
| Gemini 1.5 Pro | 2 million |
| Claude 3.5 | 200K |

**10 million tokens = ~7.5 million words = ~75 novels**

Can fit:
- Entire Unity documentation
- Entire Unreal Engine documentation
- Full game project codebase
- Plus conversation history

**Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                      WALL MODE                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  COLLECTOR   │    │  FORMATTER   │    │   ANALYST    │   │
│  │              │    │              │    │              │   │
│  │ Walk Unity   │───▶│ Structure    │───▶│ Llama 4      │   │
│  │ project dir  │    │ for analysis │    │ Scout 10M    │   │
│  │ Filter .cs   │    │ Add context  │    │              │   │
│  │ Parse scenes │    │ relationships│    │ Deep analysis│   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Proposed Commands:**
```
/wall amphitheatre              # Load entire project
/wall voice                     # Load just voice/audio system
/wall "player falls through floor"  # Load + analyze specific issue
```

**Cost Estimate:** ~$1 per deep dive (10M tokens at ~$0.10/M)

### Voice Interaction

**DEVA Stack:**
```
┌─────────────────────────────────────────────────────────────┐
│                         DEVA                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   YOU ──voice──▶ [Whisper] ──text──▶ DEVA                   │
│                                         │                    │
│   YOU ◀──voice── [ElevenLabs] ◀─text───┘                    │
│                                                              │
│   DEVA can see:                                              │
│   ├── Your screen (Computer Use)                             │
│   ├── Entire codebase (Wall Mode / 10M context)              │
│   └── Unity console logs                                     │
│                                                              │
│   DEVA can do:                                               │
│   ├── Talk back to you                                       │
│   ├── Edit code                                              │
│   └── Click/type in Unity (Computer Use)                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Components:**
| Piece | Tech | Cost |
|-------|------|------|
| Voice In | Whisper API or local Whisper | ~free to $0.006/min |
| Voice Out | ElevenLabs or OpenAI TTS | ~$0.01-0.03/message |
| Brain | Llama 4 Scout (wall) + Claude (reasoning) | ~$0.10-1.00/deep dive |
| Vision | Screenshot capture | Free |
| Control | Computer Use API | Part of Claude |

**Example Workflow:**
> "Hey Deva, the player is falling through the floor after sitting"
>
> *DEVA loads seat system code, checks recent changes, sees Unity console*
>
> "Oh honey, no. Line 342. The collider gets disabled and NEVER re-enabled.
> I've been staring at this for 0.3 seconds and honestly I'm offended.
> Want me to fix it or do you want to savor the moment?"
>
> "Yeah fix it"
>
> *DEVA edits the file, Unity hot-reloads*
>
> "Fixed. You're welcome. That's three bugs today. I'm keeping count."

### Implementation Order

1. **Wall Mode (File Collector)** - Walk Unity project, gather .cs files, parse .unity scenes
2. **Llama 4 Scout Integration** - Connect to Together.ai / Fireworks / self-hosted
3. **Voice Input** - Whisper API for speech-to-text
4. **Voice Output** - ElevenLabs for text-to-speech
5. **Computer Use** - Screenshot capture, mouse/keyboard control
6. **Unity Integration** - Console log monitoring, hot-reload triggers

### Why This Matters

Game dev bugs often exist in the **interactions between systems**:
- VoiceManager ↔ EventControlPanel ↔ PhotonVoice
- RigidbodyPlayer ↔ SeatStation ↔ NetworkedThirdPerson ↔ AvatarToggle
- RelayHostClient ↔ WebSpeakerReceiver ↔ SimpleWebServer

When you can see ALL systems together in one context, you can spot:
- Mismatched assumptions between systems
- Race conditions (this fires before that's ready)
- Circular dependencies
- Missing null checks at boundaries
- State that gets out of sync

With 10M tokens, it's not "search for the problem" anymore - it's **see the whole machine at once**.

### DEVA's Hardware

**DEVA's Machine:** ASUS ROG Strix Gaming Laptop (dedicated, isolated)

| Component | Spec |
|-----------|------|
| CPU | Intel Core i7-13650HX (14 cores) |
| RAM | 16GB DDR5 |
| GPU | NVIDIA RTX 4060 Laptop (8GB VRAM) |
| Storage | 1TB NVMe SSD |
| Display | 2560x1600 @ 240Hz |
| Audio | Realtek HD (built-in mic) |

**Security Isolation:**
- NO crypto wallets
- NO banking apps
- NO personal email
- NO access to main PC
- Guest WiFi network (isolated from home network)
- Can be wiped and restored from git anytime

**Voice:**
- ElevenLabs Voice: "Veronica - Sassy and Energetic"
- Voice ID: `ejl43bbp2vjkAFGSmAMa`

**User's Main PC (i9-12900K + RTX 4070):** DEVA has ZERO access. Ever.

---

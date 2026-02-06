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

## Future Agents

### Research Scraper Agent (Phase 3+)

**Problem:** Keeping up with all the changes in OpenClaw/Clawdbot ecosystem is hard. New videos, blog posts, GitHub updates, security patches daily.

**Solution:** A cheap/local scraper agent that:
- Monitors OpenClaw GitHub repo (commits, issues, releases)
- Watches key YouTube channels (Goda Go, etc.)
- Scans relevant subreddits, X/Twitter, blogs
- Updates our knowledge base automatically with summaries
- Runs daily on Ollama (free) or Haiku (cheap)

**"The best idea is a stolen one because you know it works."** - Friend's wisdom, 35 years ago

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

### IN PROGRESS:
- [ ] Twitter API setup - checking app permissions for mentions access

### NEXT STEPS:
1. **Fix Twitter app permissions** - Change to "Web App, Automated App or Bot" type
2. **Build Twitter monitoring** - Watch mentions, comments on David's posts
3. **Build Twitter reply flow** - Draft replies → Telegram approval → Post
4. **Test full Twitter flow** - /tweet → preview → approve → post

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

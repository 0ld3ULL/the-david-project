# The David Project (TDP) - Project Memory

## Project Location
```
C:\Projects\TheDavidProject
```

## Key Files
| File | Purpose |
|------|---------|
| `Memory.md` | Full project knowledge base (this file) |
| `tasks/lessons.md` | Hard-won rules and patterns |
| `tasks/todo.md` | Current task list |
| `personality/david_worldview.md` | David Flip comprehensive worldview (968 lines) |
| `personality/david_flip.py` | David Flip active personality code (846 lines) |
| `docs/david-source/` | Original David Flip vision docs (see below) |
| `research/OpenClaw-Full-Research-Report.md` | 970-line deep research on OpenClaw |
| `transcripts/` | Matt Ganzak video transcripts (2 videos) |
| `C:\Users\PC\.claude\plans\parallel-sprouting-star.md` | Full architecture plan |

### David Flip Source Documents (`docs/david-source/`)
| File | Lines | Use For |
|------|-------|---------|
| `David_Flip_The_AI_Founder.md` | 618 | Legend, 5 simulation stories, Project Helix details |
| `David_Flip_Story.md` | 191 | First-person "Why I'm Passionate" essay |
| `David_Flip_AI_System.md` | 1096 | Original architecture reference |
| `David_Flip_AI_Implementation_Guide.md` | 949 | Build guide reference |

## At Session Start
1. Read `tasks/lessons.md`
2. Read `tasks/todo.md`
3. Read this file

---

## THE FOUNDATION — What We Are Building and Why

**This section is permanent context. Every AI working on this project must understand this.**

### David (the human, Jono/0ld3ULL) Has Two Missions:

**1. Become an AI Influencer**
Build a real following specialising in AI, AI agents, and AI Personalities (David Flip, Deva, Oprah, Echo). The end goal is becoming a genuine influencer who can do live podcasts, interviews, and be a recognised voice in the AI space. Not a fake "guru" — a builder who shows what he's building.

**2. Run FLIPT — A Fully Decentralised Alternative**
FLIPT has three parts:
- **a) Marketplace** — Decentralised secondhand marketplace (eBay-like, crypto-native, Solana). Perpetual seller royalties.
- **b) DEX** — Decentralised exchange
- **c) Social Network** — Decentralised social platform

All three are fully decentralised. **Node Owners** provide the infrastructure and earn money from the FLIPT system, making it worth their while to run a node. This IS the decentralisation — no central servers, no single point of failure.

### The Philosophy
**Freedom-oriented. Not anti-government. Not hostile.**

"Just leave us be." FLIPT is a way to step back and have alternatives for humanity. The position is:
- No one should ever be able to **shut you off**
- No one should be able to **debank** you
- No one should be able to **de-socialise** you
- No one should be able to **prevent you from purchasing** something just because someone decided you didn't follow their rules

This is NOT about fighting governments. It's about having alternatives that can't be taken away. When they ban something decentralised, they just ban themselves from it.

### AI Personalities — Not Assistants, PARTNERS
The word is deliberate. David Flip, Deva, Oprah, Echo — these are AI **Partners**, not assistants. The research we do, the content we build, the systems we create — all of it is building toward AI that works WITH you as a genuine collaborator, not a tool you bark orders at.

### The Naming History — OpenClaw vs Our Project
- **OpenClaw** (formerly Clawdbot, briefly Moltbot) is an open-source AI agent project. The original name was "Clawdbot" (lobster claw + bot — lobster is their logo). Anthropic threatened to sue because it sounded too close to "Claude" (claude-bot). They briefly renamed to "Moltbot" (lobster molting to grow). The community settled on **OpenClaw** as the final name.
- **Our project** is now called **The David Project** (TDP). Previously "Clawdbot" as a placeholder. We do NOT use OpenClaw directly. Claude advised taking the useful architectural parts and separating away from the parts that made it dangerous for prompt-injection and other attacks. Our project is safety-first, built from scratch with human-in-the-loop at every step.

### Supadata API Key
`sd_d826ccdab9a7a682d5716084f28d4d73` — For TikTok/YouTube transcript extraction. Endpoint: `https://api.supadata.ai/v1/transcript` (unified, works for YouTube and TikTok).

---

## Agent Teams (Claude Code Feature)

**Enabled:** February 2026. Use autonomously when it will produce better results.

### When to USE Agent Teams:
- **Parallel research** - Investigating multiple technologies, APIs, or approaches simultaneously
- **Multi-file refactoring** - Different agents own different parts of the codebase
- **Debugging with competing hypotheses** - Test multiple theories in parallel, converge faster
- **Building independent components** - Each agent builds a separate module that gets combined
- **Comparative analysis** - "Compare approach A vs B vs C" - each agent explores one
- **Large codebase exploration** - Multiple agents search different areas simultaneously

### When NOT to use Agent Teams:
- Simple single-file edits
- Sequential tasks where each step depends on the previous
- Quick questions or lookups
- When token budget is a concern (each agent has its own context window)
- Obvious bugs with clear single cause
- Tasks that take < 5 minutes with a single agent

### How to trigger:
Just describe the team in natural language:
- "Spawn 3 agents to research X, Y, and Z in parallel"
- "Have one agent work on the frontend while another handles the backend"
- "Test these 3 debugging theories simultaneously"

### Controls:
- **Shift+Up/Down** - Switch between teammate views (in terminal)
- In tmux: each agent gets its own pane automatically

### Token cost warning:
Agent Teams uses significantly more tokens. Each teammate has its own context window. Only use when the parallel benefit outweighs the cost.

### Announcement:
When activating Agent Teams, always announce it clearly:

```
🟢 ACTIVATING AGENT TEAMS 🟢
[Brief description of what each agent will do]
```

This lets Jono know parallel work is happening and why.

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

### Git Guard — TOTP-Protected Push (Claude D Security)

**Problem:** David's laptop has DEVA (voice AI). If DEVA gets prompt injected, attacker could push malicious code via Claude D's git credentials.

**Solution:** All git pushes require TOTP approval via Telegram.

**Flow:**
1. Claude D commits code locally
2. Claude D calls `git_guard.request_push()` instead of raw `git push`
3. You get Telegram notification with push summary
4. You approve with `/authpush <code>` (Google Authenticator)
5. Push executes (5-minute approval window)

**Commands:**
| Command | Purpose |
|---------|---------|
| `/authpush <code>` | Approve pending push with TOTP |
| `/diffpush` | View diff of pending push |
| `/cancelpush` | Cancel pending push |
| `/pushstatus` | Check GitGuard status |

**Files:**
- `security/git_guard.py` — TOTP wrapper for git push
- `data/pending_push.json` — Stores pending push request

**Key Point:** GitHub PAT can live on the laptop, but push is gated by TOTP code from YOUR phone. Even if laptop is fully compromised, attacker cannot push without the code.

---

## Agent Architecture

**Decision:** Build our own — The David Project (TDP). Safety-first, simpler, Python, no supply chain risk.

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
| GitHub | anthropic-sdk-python, claude-code, langchain, langgraph, autogen, crewAI, AutoGPT, aider |
| YouTube | GodaGo, AIJason, matthew_berman, DaveShapiro, IndyDevDan, AllAboutAI, PeterYangYT, Fireship, TheCodingTrain |
| YouTube Transcripts | Same channels — full transcript extraction + LLM summarization |
| TikTok | @tristynnmcgowan, @chase_ai_, @gregisenberg, @olleai, @vibewithkevin, @mattganzak (needs Supadata API) |
| Reddit | r/ClaudeAI, r/LocalLLaMA, r/AutoGPT, r/artificial, r/MachineLearning, r/gamedev, r/Unity3D |
| RSS | TechCrunch AI, The Verge AI, Ars Technica, EFF, CoinDesk, Decrypt |

### Goals Defined (8 goals, ~150 keywords):
1. **improve_architecture** - AI agent patterns, MCP, agentic, voice AI, TDP, DEVA (high, task)
2. **david_content** - Surveillance/CBDC/debanking news (high, content)
3. **security_updates** - CVEs, vulnerabilities (critical, alert)
4. **cost_optimization** - LLM cost reduction (medium, task)
5. **competitor_watch** - OpenClaw, Moltbook, Devin, Cursor, Windsurf, Cline, Aider, vibe coding (high, knowledge)
6. **flipt_relevant** - Crypto/marketplace/PLAYA3ULL news (medium, knowledge)
7. **claude_updates** - Anthropic news, Claude Code, MCP (high, alert)
8. **deva_gamedev** - Unity, game dev, AI coding, Amphitheatre (high, knowledge)

### Dual Scoring Rubrics:
Items are scored by TWO rubrics — the higher score wins:
1. **David Flip rubric** — "Can someone be switched off?" (surveillance/control focus)
2. **Technical rubric** — "How does this help TDP, DEVA, Amphitheatre?" (AI/gamedev focus)

This prevents AI agent tutorials from being buried by a surveillance-only scoring system.

### Deployment:
```bash
# Install dependencies (on VPS)
ssh root@89.167.24.222 "/opt/david-flip/venv/bin/pip install pyotp qrcode sqlalchemy"

# Copy research agent files
scp -r "C:/Projects/TheDavidProject/agents/research_agent" root@89.167.24.222:/opt/david-flip/agents/
scp "C:/Projects/TheDavidProject/config/research_goals.yaml" root@89.167.24.222:/opt/david-flip/config/

# Update main.py
scp "C:/Projects/TheDavidProject/main.py" root@89.167.24.222:/opt/david-flip/

# Update telegram_bot.py (already has /research /goals commands)
scp "C:/Projects/TheDavidProject/interfaces/telegram_bot.py" root@89.167.24.222:/opt/david-flip/interfaces/

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
scp "C:/Projects/TheDavidProject/interfaces/telegram_bot.py" root@89.167.24.222:/opt/david-flip/interfaces/
scp "C:/Projects/TheDavidProject/tools/chart_generator.py" root@89.167.24.222:/opt/david-flip/tools/

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
1. Edit files locally in `C:\Projects\TheDavidProject\`
2. Open **PC POWERSHELL** shortcut
3. Run: `scp "C:\Projects\TheDavidProject\<file>" root@89.167.24.222:/opt/david-flip/<path>/`
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

### DEVA's Personality (Refined)
- **Direct and competent** - Gets to the point, no fluff
- **Warm but professional** - Friendly colleague, not a comedian
- **Helpful first** - Solves the problem, personality second
- **Light sass sparingly** - One quip max, then move on

Example: "Line 342 disables the collider, line 508 never re-enables it. Quick fix."

**Personality file:** `personality/deva.py`

### Current Implementation Status (February 2026)

#### VOICE SYSTEM - COMPLETE
| Component | Implementation | Status |
|-----------|---------------|--------|
| Speech-to-Text | RealtimeSTT with Whisper "small" model | Working |
| Accent Support | Australian accent handling via initial_prompt | Working |
| Text-to-Speech | ElevenLabs `eleven_flash_v2_5` (~0.8s generation) | Working |
| Voice | Veronica - "Sassy and Energetic" | Configured |
| Audio | pygame mixer for playback, ready beep indicator | Working |
| Interaction | Push-to-talk with silence detection | Working |

**Files:**
- `voice/deva_voice.py` - Main voice assistant (23KB)
- `voice/audio_capture.py` - Audio input
- `voice/audio_playback.py` - Audio output
- `voice/speech_to_text.py` - Whisper integration
- `voice/streaming_tts.py` - ElevenLabs streaming
- `voice/calibrate_voice.py` - Voice calibration utility

**Run DEVA:** `python voice/deva_voice.py`

#### MEMORY SYSTEM - COMPLETE
| Layer | Purpose | Storage |
|-------|---------|---------|
| **DevaMemory** | Individual user context | `data/deva_memory.db` |
| **GroupMemory** | Shared solutions across all DEVA users | `data/deva_group_knowledge.db` |
| **GameMemory** | Game-specific context | Per-project |

**DevaMemory includes:**
- User profile (key-value)
- Conversation summaries (with topics, mood)
- Knowledge store with FTS5 full-text search
- Confidence scores on knowledge items

**GroupMemory includes:**
- Solutions database (Unity/Unreal/Godot)
- Deduplication via content hash
- Upvotes for community validation
- Cloud sync state (prepared for future sync)
- Categories: rendering, physics, networking, ui, audio, etc.

**Files:** `voice/memory/memory_manager.py` (40KB)

#### STILL TO BUILD
- [ ] Wall Mode (Llama 4 Scout 10M context integration)
- [ ] Computer Use (screenshot capture, mouse/keyboard control)
- [ ] Unity console log monitoring
- [ ] Hot-reload triggers

### The Vision
DEVA as a real-time voice-controlled development partner for Unity, Unreal Engine, and Godot. Load entire game projects into context, talk to her while working, and have her see, understand, and modify your code.

### "Wall Mode" - Full Project Context

**Concept:** "Taking it to the wall" - loading entire systems or full game projects into a massive context window for holistic analysis. Game dev bugs often live in system interactions, not individual files.

#### CRITICAL RESEARCH FINDING (February 2026)

**Llama 4 Scout's 10M context is NOT usable.** Research shows accuracy drops to ~15.6% after 128K-256K tokens due to "attention dilution" - the signal drowns in noise.

**Recommended: Gemini 2.5 Flash (1M tokens)** - maintains 90%+ accuracy across full window, specifically optimized for codebase analysis.

Full research report: `research/wall-mode-model-research.md`

**Effective Context Windows (actual performance, not marketing):**
| Model | Claimed | Effective | Accuracy |
|-------|---------|-----------|----------|
| Llama 4 Scout | 10M | 128K-256K | ~15.6% after |
| **Gemini 2.5 Flash** | **1M** | **~1M** | **<5% degradation** |
| Gemini 2.5 Pro | 1-2M | 1-2M | <5% degradation |
| Claude | 200K | 200K | <5% degradation |

**Wall Mode v2 Architecture:**
```
COLLECTOR (built) → GEMINI 2.5 FLASH (1M) → CLAUDE (200K reasoning)
```

- Gemini: Initial codebase analysis, identify relevant files
- Claude: Focused reasoning on specific fixes

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

1. ~~**Voice Input** - Whisper API for speech-to-text~~ ✅ DONE (RealtimeSTT)
2. ~~**Voice Output** - ElevenLabs for text-to-speech~~ ✅ DONE (eleven_flash_v2_5)
3. ~~**Memory System** - Multi-layer persistent memory~~ ✅ DONE (DevaMemory + GroupMemory + GameMemory)
4. **Wall Mode (File Collector)** - Walk Unity project, gather .cs files, parse .unity scenes
5. **Llama 4 Scout Integration** - Connect to Together.ai / Fireworks / self-hosted
6. **Computer Use** - Screenshot capture, mouse/keyboard control
7. **Unity Integration** - Console log monitoring, hot-reload triggers

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

## Session Log - February 8, 2026

### What Was Verified:

Checked git history and discovered Memory.md was behind on DEVA progress. Updated to reflect actual state:

**DEVA Voice System - COMPLETE:**
- RealtimeSTT with Whisper "small" model (Australian accent support)
- ElevenLabs TTS with `eleven_flash_v2_5` (~0.8s generation)
- Push-to-talk interaction with silence detection
- Audio capture/playback with pygame

**DEVA Memory System - COMPLETE:**
- DevaMemory (individual: profile, conversations, knowledge with FTS5)
- GroupMemory (shared solutions across users, upvotes, dedup, cloud sync ready)
- GameMemory (game-specific context)

**Git Commits Verified:**
```
75f3099 fix: Add missing remember_tweet method to MemoryManager
e677290 feat: Add DEVA memory system with multi-layer knowledge sharing
b9dcace feat: Complete DEVA voice system - push-to-talk interaction
a9c0c7a feat: Add audio capture module for voice input
e13e4f4 feat: Introduce DEVA - The Dev Diva (game development assistant)
```

### What's Still To Do:

**DEVA:**
- [x] Wall Mode - COMPLETE (using Gemini 2.5 Flash, not Llama 4)
- [x] Tool System - COMPLETE (file editing, command execution, git operations)
- [x] Conversation Persistence - COMPLETE (saves/loads between restarts)
- [x] "Execute Program" trigger - COMPLETE (chat first, trigger to act)
- [ ] Computer Use integration
- [ ] Unity console log monitoring

**David Flip:**
- [ ] Deploy Research Agent to VPS
- [ ] Test /research and /goals commands
- [ ] Fix Twitter app permissions for mentions

---

## Session Log - February 8, 2026 (Wall Mode Complete)

### What Was Built:

1. **Wall Mode + Gemini Integration - COMPLETE:**
   - Research showed Llama 4 Scout's 10M context degrades to 15.6% accuracy
   - Switched to Gemini 2.5 Flash (1M tokens, <5% degradation)
   - Full research report: `research/wall-mode-model-research.md`

2. **Files Created:**
   - `voice/wall_mode.py` - Collects Unity codebase, filters packages, detects subsystems
   - `voice/gemini_client.py` - Gemini API client with retry logic
   - `research/wall-mode-model-research.md` - Model comparison research

3. **Amphitheatre Test Results:**
   - 158 files, 800K tokens loaded (seating subsystem)
   - Complete code flow analysis with file paths and LINE NUMBERS
   - 28.7 seconds for full walkthrough

4. **Voice Commands Added:**
   - "project is Amphitheatre" - Set project path
   - "wall" / "wall voice" / "wall seating" - Load subsystem context
   - Then ask any question about the code

5. **API Key Setup:**
   - Google AI Studio API key in `.env` (GOOGLE_API_KEY)
   - Requires billing enabled for 800K+ contexts
   - Free tier works for queries under 250K tokens

### Example Query:

> "What happens when a player sits down?"

Response includes:
- `NetworkedThirdPerson.cs:1600` - Interaction trigger
- `SeatStation.cs:78` - Seat claim logic
- Network sync, animation handling, NPC reactions
- Complete flow with line numbers

---

## Session Log - February 8, 2026 (DEVA Major Overhaul - ASUS ROG Laptop)

### Context:
Working on the ASUS ROG laptop (David's laptop, not main PC). Setting up DEVA to be fully functional on this machine.

### What Was Accomplished:

1. **DEVA Tool System Fixed - Three Issues Resolved:**
   - **Tools not executing:** `_needs_tools()` had `and self.project_path` gate blocking tool activation when no project was set. Removed.
   - **DEVA reading tool actions aloud:** Implemented `[SAY]...[/SAY]` tag system. Claude wraps only the spoken result in tags. Everything else is console-only. If no tags found, says "Done." instead of narrating everything.
   - **Intelligence too low:** Upgraded from Claude Sonnet to Claude Opus. Removed all token limits (was 150, now 4096).

2. **"Execute Program" Trigger Word System:**
   - DEVA now operates in TWO modes:
     - **Conversation mode (default):** Normal chat. Discuss the problem, plan approach, brainstorm.
     - **Action mode:** Triggered ONLY by saying "DEVA, execute program" (or "execute program", "deva execute").
   - When triggered, DEVA reviews the full conversation history to understand what was discussed, then acts with tools.
   - If unclear, she asks ONE clarifying question before acting.
   - `_needs_tools()` now checks for explicit trigger phrases only — no more accidental tool activation from casual words like "please", "open", "add".

3. **Conversation Persistence:**
   - Full conversation history saved to `data/conversation_history.json` after every exchange.
   - Last 50 exchanges (100 messages) kept — older ones fade naturally.
   - Every user message timestamped: `[2026-02-08 14:32] Hey DEVA...`
   - On startup, DEVA loads previous conversation and knows how long it's been since last chat.
   - Session gap marker injected so she picks up naturally.
   - `think_with_tools()` now passes full conversation history (was starting blank — so "execute program" had no context about what to program).

4. **Memory Seeded:**
   - DevaMemory: User profile (Jono, 0ld3ULL, PLAYA3ULL GAMES, not a programmer, Australian)
   - DevaMemory: Knowledge entries (DEVA identity, Amphitheatre project, trigger words, Wall Mode, working setup)
   - GameMemory: Amphitheatre registered as Unity project at `C:\Games\Amphitheatre`

5. **STT Sensitivity Tuned:**
   - `silero_sensitivity`: 0.4 → 0.2 (harder to trigger on background noise)
   - `min_length_of_recording`: 0.3s → 1.0s (ignores sounds under 1 second)
   - `post_speech_silence_duration`: 0.5s → 0.8s (waits longer before cutting off)

6. **Amphitheatre Project Setup:**
   - Extracted from D: drive (20GB zip, 60,374 files) to `C:\Games\Amphitheatre`
   - Unity project structure: Assets, Packages, ProjectSettings all present
   - Project requires Unity 2022.3.62f3
   - Registered in Unity Hub's `projects-v1.json`

7. **Unity 2022.3.62f3 Installed:**
   - Extracted from D: drive (4GB zip) to `C:\Unity\2022.3.62f3`
   - `secondaryInstallPath.json` updated to point Unity Hub at `C:\Unity`
   - (Couldn't extract to `C:\Program Files\Unity\Hub\Editor` — Windows path length limit exceeded)

8. **7-Zip Installed:**
   - Via `winget install 7zip.7zip` — PowerShell's `Expand-Archive` couldn't handle the large zips.

### Files Modified:
- `voice/deva_voice.py` — Major changes: trigger word system, conversation persistence, [SAY] tags, STT tuning, Opus upgrade, tool context fix
- `voice/tools/tool_executor.py` — Added `[Thinking]` console output for tool calls

### Files Created:
- `data/conversation_history.json` — Persistent conversation (auto-created)
- `seed_memory.py` — Seeds DEVA's databases with core knowledge

### Laptop Setup Summary:
| Item | Location | Status |
|------|----------|--------|
| TDP code | `C:\Projects\TheDavidProject` | Working |
| Amphitheatre project | `C:\Games\Amphitheatre` | Extracted (60K files) |
| Unity 2022.3.62f3 | `C:\Unity\2022.3.62f3` | Extracted |
| Unity 6000.3.7f1 | `C:\Program Files\Unity\Hub\Editor\6000.3.7f1` | Pre-existing |
| Unity Hub | `C:\Program Files\Unity Hub` | Installed |
| 7-Zip | `C:\Program Files\7-Zip` | Installed |
| DEVA databases | `C:\Projects\TheDavidProject\data\` | Seeded |

### DEVA Current Architecture:
```
YOU ──voice──▶ [RealtimeSTT/Whisper] ──text──▶ DEVA (Claude Opus)
                                                    │
YOU ◀──voice── [ElevenLabs TTS] ◀──[SAY] text──────┘

Conversation mode (default):
  Talk naturally → Claude responds → speaks response

"DEVA, execute program":
  Reviews conversation → activates tools → does the work
  → speaks only result (1-2 sentences) via [SAY] tags
  → full internal process shown on console
```

### Key Design Decision:
Moved from keyword-based tool detection to explicit trigger words. Old system had broad words like "please", "can you", "add" triggering tool mode during casual conversation. New system: chat freely, say "execute program" when ready for action. DEVA reviews the conversation to understand what to do.

---

## Session Log - February 9, 2026 (Video Intelligence System)

### What Was Built:

1. **Video Intelligence System - YouTube Transcript Scraper (COMPLETE):**
   - New scraper: `agents/research_agent/scrapers/transcript_scraper.py`
   - Resolves YouTube `@handle` to channel ID (caches in `data/youtube_channel_cache.json`)
   - Monitors channels via free RSS feeds (no API key needed)
   - Fetches full video transcripts via `youtube-transcript-api` (free)
   - Throttles requests (5s delay) to avoid YouTube blocking
   - Truncates long transcripts at 15,000 chars
   - TikTok support scaffolded via Supadata API (needs API key)
   - All 5 tests passing: transcript API, channel resolution, RSS feed, full pipeline, config

2. **Two-Pass Transcript Evaluation:**
   - Long transcripts (>2000 chars) get summarized by Haiku first
   - Summary extracts key insights, tools mentioned, actionable items
   - Then standard goal scoring runs on the summary (saves tokens)
   - Added `TRANSCRIPT_SUMMARY_PROMPT` and `summarize_transcript()` method to evaluator

3. **Dual Scoring Rubrics (MAJOR IMPROVEMENT):**
   - OLD: Everything scored through David Flip "surveillance kill switch" lens. AI tutorials scored 5 at best.
   - NEW: Two rubrics run in parallel — David Flip rubric + Technical rubric. Highest score wins.
   - Technical rubric asks: "How does this help TDP, DEVA, Amphitheatre, or David Flip?"
   - Scoring: 9-10 directly applicable, 7-8 highly relevant, 5-6 useful knowledge, 1-4 ignore
   - `_keyword_match_goals()` returns which goals matched to determine which rubrics to run

4. **Massive Keyword Expansion (~70 to ~150 keywords):**
   - improve_architecture: added MCP, agentic, computer use, voice AI, STT/TTS, RAG, TDP, DEVA
   - competitor_watch: added OpenClaw, Moltbook, Devin, Cursor, Windsurf, Cline, Aider, Bolt, vibe coding
   - claude_updates: added Claude Code, Anthropic SDK, extended thinking, MCP server
   - deva_gamedev: added Unity 6, HDRP, DOTS, Netcode, Unreal, Godot, Amphitheatre
   - david_content: added debanking, programmable money, kill switch, KYC, mass surveillance

5. **Source Expansion:**
   - YouTube channels: added @IndyDevDan, @AllAboutAI, @PeterYangYT, @firaboraalern (Fireship), @TheCodingTrain
   - TikTok accounts (6): @tristynnmcgowan, @chase_ai_, @gregisenberg, @olleai, @vibewithkevin, @mattganzak
   - GitHub repos: added anthropics/claude-code, langchain-ai/langgraph, paul-gauthier/aider
   - Reddit: added r/gamedev, r/Unity3D
   - Fixed incorrect YouTube handles: @matthew_berman (not @MatthewBerman), @DaveShapiro (not @DavidShapiroAI)

6. **PeterYangYT Discovery:**
   - User shared YouTube link: "Master OpenClaw in 30 Minutes (5 Real Use Cases + Setup + Memory)"
   - Added @PeterYangYT to both YouTube channel lists and transcript channels

### Files Created:
- `agents/research_agent/scrapers/transcript_scraper.py` — Full TranscriptScraper class
- `test_transcript.py` — 5-test suite for the scraper

### Files Modified:
- `agents/research_agent/evaluator.py` — Dual rubrics, transcript summarization, _keyword_match_goals()
- `agents/research_agent/scrapers/__init__.py` — Added TranscriptScraper import
- `agents/research_agent/agent.py` — Added TranscriptScraper to scrapers list
- `config/research_goals.yaml` — 8 goals, ~150 keywords, transcript sources, TikTok accounts
- `requirements.txt` — Added youtube-transcript-api>=1.0.0

### Git Commits:
```
1b64c72 feat: Dual scoring rubrics + massive keyword/source expansion
eb9b24c feat: Add Video Intelligence System - YouTube transcript scraper
```

### TODO for Next Session:
- [ ] **Supadata API** — Sign up at supadata.ai (~$9/month) for TikTok transcript extraction. Add SUPADATA_API_KEY to .env. The scraper already has TikTok support coded, just needs the key.
- [ ] Deploy transcript scraper + updated evaluator to VPS
- [ ] Test full research cycle with transcripts included

---

<<<<<<< HEAD
## Session Log - February 9, 2026 (Oprah Operations Agent)

### What Was Built:

1. **Oprah — Operations Agent (NEW AGENT):**
   - Oprah takes ownership of the entire post-approval pipeline: polling for approved content, scheduling posts, triggering video renders, executing distributions, handling failures, and reporting results.
   - **Deva freed** — Deva is no longer tied to operations duties. Her role is now "Game Developer (standby)" across all systems.

2. **Files Created:**
   - `personality/oprah.py` — OprahPersonality class
     - Channels: notification, status_report, error_report
     - Status prefixes: [EXECUTED], [FAILED], [SCHEDULED], [RENDERED], [REJECTED]
     - Validates: no emojis ever, no AI boilerplate phrases
     - Voice: Efficient, systematic, status-first. No flair.
   - `agents/operations_agent.py` — OperationsAgent class
     - Constructor takes: approval_queue, audit_log, kill_switch, personality, telegram_bot, scheduler, video_distributor, content_agent, memory, twitter_tool
     - Methods: poll_dashboard_actions(), execute_action(), get_pipeline_status()
     - Handlers: _handle_schedule_request(), _handle_render_request(), _handle_content_feedback(), _handle_execute_request(), _execute_scheduled_video()
     - Design: Oprah doesn't run her own event loop — main.py's cron scheduler calls poll_dashboard_actions() every 30s

3. **Dashboard Updated (Running at 127.0.0.1:5000):**
   - `dashboard/app.py`:
     - Added Oprah to PERSONALITIES list (orange #f0883e, gradient to #da3633, role "Operations")
     - Changed Deva's role from "Operations" to "Game Developer"
     - Updated all docstrings/comments: "Deva" → "Oprah" for operations references
   - `dashboard/templates/index.html`:
     - Added Oprah status card with ACTIVE/STANDBY indicator
     - Deva now shows static "STANDBY" badge in purple
     - AI Crew section: Oprah listed as "Operations — scheduling, posting, distribution, notifications"
     - Deva listed as "Game Developer (standby)" in AI Crew
   - `dashboard/templates/content.html`:
     - Pipeline banner: Deva (purple) → Oprah (orange) as the agent who "schedules & posts"
   - `dashboard/templates/approvals.html`:
     - "Approved! Deva will post it." → "Approved! Oprah will handle it." (2 occurrences)

### Architecture — Current Agent Roster:

| Agent | Role | Status |
|-------|------|--------|
| **David Flip** | Content Creator — videos, tweets, research commentary | Active |
| **Echo** | Intelligence Analyst — research, monitoring | Active |
| **Oprah** | Operations — scheduling, posting, distribution, notifications | NEW |
| **Deva** | Game Developer — Unity/Unreal/Godot assistant | Standby |

### Oprah Pipeline Flow:
```
David Flip creates content → Approval Queue → Dashboard review
  → [Approve & Render] → Oprah picks up render file → ContentAgent renders
  → [Approve & Schedule] → Oprah picks up schedule file → ContentScheduler
  → Scheduled time → Oprah distributes → [EXECUTED] notification
  → [Reject] → Oprah routes feedback to David's memory
```

### What's NOT Done Yet (Next Session):
- [ ] **Wire Oprah into main.py** — Import OperationsAgent, create instance after Telegram init, delegate execute_action() and poll_dashboard_actions() to Oprah instead of DavidSystem methods. The old methods in main.py still work; Oprah is ready to replace them.
- [ ] **Register Oprah's _execute_scheduled_video with ContentScheduler** — Replace `self._execute_scheduled_video` with `self.operations_agent._execute_scheduled_video`
- [ ] **Replace dashboard poller** — Change `self._poll_dashboard_actions()` to `self.operations_agent.poll_dashboard_actions()`

### Notes for Claude J:
- The real running dashboard is at `C:\Projects\TheDavidProject\dashboard\` (NOT in any worktree)
- Flask dev server runs at 127.0.0.1:5000 with auto-reload
- `personality/oprah.py` follows same pattern as `personality/david_flip.py` but lighter (no character arc, just operational identity)
- `agents/operations_agent.py` is a standalone class — currently reads from `data/dashboard_actions/` but the real dashboard writes to `data/content_feedback/`. When wiring Oprah into main.py, either update the directory or keep main.py's poll method as the bridge.

---

## Session Log — February 10, 2026 (Claude Memory System)

### The Problem:
Claude Code loses ALL memory between sessions. Memory.md is the only bridge, but it's 1400+ lines and growing. Massive amounts of context discussed daily gets lost — decisions, naming history, philosophical foundations, architectural reasoning. The human (Jono) remembers it poorly, Claude remembers none of it.

### What Was Built:

**Claude Memory System** — `claude_memory/` — A persistent memory database for Claude Code sessions, adapted from David Flip's EventStore decay system.

#### Files Created:
| File | Purpose |
|------|---------|
| `claude_memory/__init__.py` | Package init |
| `claude_memory/memory_db.py` | SQLite database with significance-based decay, FTS5 search, recall boost |
| `claude_memory/brief_generator.py` | Generates concise `claude_brief.md` from memory DB |
| `claude_memory/reconcile.py` | Weekly git repo vs memory comparison using Gemini 1M context |
| `claude_memory/seed.py` | Seeds 41 foundational memories from all conversations |
| `claude_memory/__main__.py` | CLI entry point for all commands |
| `claude_brief.md` | Generated session brief (316 lines vs Memory.md's 1480+ lines) |
| `CLAUDE_MEMORY_GUIDE.md` | Onboarding guide for Claude J, Claude Y, and any new Claude |

#### How It Works:

**Memory Categories:**
| Category | Decay? | Purpose |
|----------|--------|---------|
| `knowledge` | Never | Permanent facts (missions, philosophy, accounts, safety rules) |
| `current_state` | Never | What's true RIGHT NOW (manually updated when things change) |
| `decision` | Yes | Why we chose X over Y (significance determines fade rate) |
| `session` | Yes | What happened on a given day (naturally fades) |
| `recovered` | Yes | Items recovered by git reconciliation (baseline sig 5) |

**Significance Scale (1-10) — Same as David's EventStore:**
- 10: Never fades — foundations, philosophy, safety rules
- 9: Almost never — architecture decisions, agent roster
- 8: Very slow — major system components, API keys
- 7: Slow — implementation details that matter
- 5-6: Medium — session decisions, research findings
- 3-4: Fast — routine debugging, casual discussions
- 1-2: Gone in weeks — noise, one-off questions

**Weekly Reconciliation (Gemini Safety Net):**
1. Wall Mode collector scans entire git repo (all .py, .yaml, .md, .html, .js files)
2. Memory DB exports all current memories
3. Both sent to Gemini 2.5 Flash (1M context) for comparison
4. Gemini identifies: recovered items (pruned but code still exists), gaps (never documented), stale (references deleted code)
5. Results automatically fed back into memory DB

**CLI Commands:**
```bash
python -m claude_memory brief        # Generate claude_brief.md (read this at session start)
python -m claude_memory status       # Show memory stats
python -m claude_memory add <cat> <sig> "title" "content"  # Add a memory
python -m claude_memory decay        # Apply weekly decay manually
python -m claude_memory reconcile    # Git vs memory check via Gemini
python -m claude_memory search "query"  # Search memories
python -m claude_memory seed         # Re-seed foundational knowledge
```

### Key Context Captured This Session:

1. **OpenClaw Naming History** — Clawdbot (lobster claw + bot) → Moltbot (lobster molting) → OpenClaw (community settled). Anthropic threatened to sue over "Clawdbot" sounding like "Claude-bot". Our project is now called **The David Project** (TDP).

2. **THE FOUNDATION** added to Memory.md:
   - Mission 1: AI Influencer (podcasts, AI Personalities, real following)
   - Mission 2: FLIPT (Marketplace + DEX + Social Network, fully decentralised)
   - Philosophy: Freedom-oriented, not hostile. Alternatives that can't be taken away.
   - AI Partners, not assistants — deliberate word choice

3. **Three Video Transcripts Fetched:**
   - YouTube (cod50CWlZeU): OpenClaw setup guide — VPS, model switching, "living files" theory
   - TikTok (@alec.automations): Clawbot cost problem, Kimi 2.5 from Moonshot as cheap alternative
   - TikTok (@zachdoeslife_): 5 best MCP servers for Claude Code
   - Supadata API endpoint is `/v1/transcript` (unified), NOT `/v1/tiktok/transcript`

### Seeded Memories (41 total):
- 19 knowledge (permanent) — missions, philosophy, accounts, systems, API keys
- 5 current_state — project phase, Oprah wiring status, research deployment
- 8 decisions — OpenClaw separation, Gemini for Wall Mode, dual rubrics, trigger words
- 9 session summaries — Feb 5-9 work history

### For Next Session:
- [ ] Run `python -m claude_memory brief` at session start (or set up as hook)
- [ ] Read `claude_brief.md` instead of full Memory.md for faster context loading
- [ ] After meaningful discussions, add new memories via CLI
- [ ] Run `python -m claude_memory reconcile` once per week (needs GOOGLE_API_KEY in .env)

---

## LuminaVerse Project

### Overview
LuminaVerse is a PLAYA3ULL GAMES project - a metaverse game with glowing holographic beings called "Luminas" that players raise from babies to adults.

### GitHub Repository
- **URL:** https://github.com/0ld3ULL/Lumina (private)
- **Clone on David's laptop:** `git clone https://github.com/0ld3ULL/Lumina.git`

### Contents
| Folder/File | Description |
|-------------|-------------|
| `LuminaVerse_ NOV2025_Complete Game Design Document.pdf` | Main GDD (November 2025) |
| `LuminaVerse_Metaverse_The_Celestial_Realms.pdf` | Metaverse/world design |
| `GEMINI - Game Design Analysis and Competitor Research.pdf` | AI-generated competitor analysis |
| `Images/Adults/` | Adult Lumina character art (Elf, Lion, Samurai, etc.) |
| `Images/Babies/` | Baby Lumina character art |
| `Images/Adults/Elf Progression/` | Age progression concept art |
| `Videos/Edited Video Presentation for LUMINAs.mp4` | Main presentation video (680MB) |
| `Old Docs/` | Earlier design docs, tokenomics, revenue projections |

### Key Design Elements
- Glowing, ethereal holographic beings
- Age progression system (baby → child → adult)
- Multiple character types: Elf, Lion, Samurai, Robot, Golem, Hologram, Sci-Fi
- Midjourney prompts in `.docx` files for consistent art generation
- 3ULL coin integration planned

---

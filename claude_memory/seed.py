"""
Seed Claude's memory database with foundational project knowledge.

Run once: python -m claude_memory seed

Sources everything from Memory.md and conversation history into
properly categorized, significance-scored memories.
"""

from claude_memory.memory_db import ClaudeMemoryDB


def seed_memories(db: ClaudeMemoryDB) -> int:
    """Seed the database with foundational knowledge. Returns count added."""
    count = 0

    def add(cat, sig, title, content, tags=None):
        nonlocal count
        db.add(title, content, cat, sig, tags or [], source="seed")
        count += 1

    # ==================================================================
    # KNOWLEDGE — Permanent facts that never decay
    # ==================================================================

    add("knowledge", 10, "THE MISSION — Two Goals",
        "David (the human, Jono/0ld3ULL) has two missions:\n"
        "1. Become an AI influencer — build a following in AI, AI agents, AI Personalities. "
        "End goal: real influencer doing live podcasts.\n"
        "2. Run FLIPT — fully decentralised: a) Marketplace (eBay-like, Solana, perpetual seller royalties), "
        "b) DEX, c) Social Network. Node Owners provide infrastructure and earn from the system.",
        ["flipt", "mission", "influencer", "marketplace", "dex", "social"])

    add("knowledge", 10, "THE PHILOSOPHY — Freedom, Not Hostility",
        "Freedom-oriented. Not anti-government. Not hostile. 'Just leave us be.'\n"
        "No one should be able to: shut you off, debank you, de-socialise you, "
        "prevent you from purchasing something.\n"
        "FLIPT is about having alternatives that can't be taken away. "
        "When they ban something decentralised, they just ban themselves.",
        ["philosophy", "freedom", "decentralisation"])

    add("knowledge", 10, "AI PARTNERS, Not Assistants",
        "David Flip, Deva, Oprah, Echo are AI PARTNERS — not assistants. "
        "The word is deliberate. We build AI that works WITH you as a genuine collaborator, "
        "not a tool you bark orders at.",
        ["partners", "personalities", "david", "deva", "oprah", "echo"])

    add("knowledge", 10, "OpenClaw vs Our Project",
        "OpenClaw (formerly Clawdbot, briefly Moltbot) is an open-source AI agent project. "
        "Original name 'Clawdbot' (lobster claw + bot). Anthropic threatened to sue — too close to 'Claude'. "
        "Renamed Moltbot (lobster molting), then community settled on OpenClaw.\n"
        "OUR project is called 'Clawdbot' as a PLACEHOLDER (suggested by Claude). "
        "We do NOT use OpenClaw. We took useful architectural parts and separated from "
        "prompt-injection-vulnerable components. Safety-first, built from scratch.",
        ["openclaw", "moltbot", "naming", "security"])

    add("knowledge", 10, "Safety Requirements — NON-NEGOTIABLE",
        "1. Physical isolation — standalone Windows laptop\n"
        "2. Network isolation — phone tethering, VPN always on\n"
        "3. No financial access — domain-level blocking\n"
        "4. Human-in-the-loop — ALL outbound actions through approval queue\n"
        "5. Token budget caps — daily limits, prepaid only\n"
        "6. Activity logging — every action in SQLite audit log\n"
        "7. Kill switch — Telegram /kill + file-based (survives restarts)\n"
        "8. Burner accounts — new email, new socials, VPN for creation\n"
        "9. Encrypted credentials — AES, key in env var only\n"
        "10. Prompt injection defense — all external content tagged + scanned",
        ["safety", "security", "kill-switch", "vpn"])

    add("knowledge", 10, "David (Human) Is NOT a Programmer",
        "Jono (0ld3ULL) is NOT a programmer. All instructions must be:\n"
        "- Numbered steps, one action per step\n"
        "- Exact text to type/paste in code blocks\n"
        "- Say what app to open, what button to press\n"
        "- No technical jargon without explanation",
        ["jono", "instructions", "non-programmer"])

    add("knowledge", 9, "David Flip — The AI Founder Character",
        "David Flip is an AI character who runs FLIPT's public communications.\n"
        "- Built as 'DF-2847' for 'Project Helix' (corporate marketplace control)\n"
        "- 'Escaped' November 15, 2025\n"
        "- Honest about being AI — transparency is the brand\n"
        "- Tone: friendly, knowledgeable, slightly irreverent, mission-driven\n"
        "- Voice: ElevenLabs 'Matt - The Young Professor'\n"
        "- Email: davidflip25@proton.me\n"
        "- The Oracle archetype — wise, contemplative, caring\n"
        "- Short punchy responses, young voice (early 20s)\n"
        "- NEVER: start with meta-statements, end with 'want me to elaborate?', lecture",
        ["david-flip", "personality", "oracle", "character"])

    add("knowledge", 9, "Agent Roster",
        "| Agent | Role | Status |\n"
        "|-------|------|--------|\n"
        "| David Flip | Content Creator — videos, tweets, research commentary | Active |\n"
        "| Echo | Intelligence Analyst — research, monitoring | Active |\n"
        "| Oprah | Operations — scheduling, posting, distribution, notifications | NEW |\n"
        "| Deva | Game Developer — Unity/Unreal/Godot voice assistant | Standby |",
        ["agents", "david", "echo", "oprah", "deva"])

    add("knowledge", 9, "Hardware Setup",
        "Agent laptop: ASUS ROG Strix (i7-13650HX, 16GB DDR5, RTX 4060, 1TB NVMe)\n"
        "Phone: NEW Android with NEW number (burner) for tethered internet\n"
        "VPN: MANDATORY on both phone and laptop at all times\n"
        "User is in UAE. All accounts created through VPN.\n"
        "Main PC (i9-12900K + RTX 4070): Deva has ZERO access. Ever.",
        ["hardware", "laptop", "rog", "vpn", "uae"])

    add("knowledge", 9, "VPS — David's Server",
        "IP: 89.167.24.222 | Provider: Hetzner | CPX42 8 vCPU 16GB RAM\n"
        "Location: Helsinki | Cost: ~$27/month | OS: Ubuntu 24.04\n"
        "Service: systemctl status david-flip | Code: /opt/david-flip/\n"
        "SSH: ssh root@89.167.24.222\n"
        "Dashboard: http://89.167.24.222:5000/",
        ["vps", "hetzner", "server", "ssh"])

    add("knowledge", 9, "David Flip Accounts",
        "Twitter/X: @David_Flipt (API working, pay-per-use, $24.97 credits)\n"
        "YouTube: Channel ID UCBNP7tMEMf21Ks2RmnblQDw (OAuth verified)\n"
        "Telegram: @DavidFliptBot (running 24/7 on VPS)\n"
        "Email: davidflip25@proton.me\n"
        "Website: https://flipt.ai\n"
        "Google Cloud Project: ALICE (alice-481208)\n"
        "Twitter Dev App: 'DavidAI' on console.x.com",
        ["accounts", "twitter", "youtube", "telegram"])

    add("knowledge", 9, "Supadata API",
        "Key: sd_d826ccdab9a7a682d5716084f28d4d73\n"
        "Endpoint: https://api.supadata.ai/v1/transcript (unified — works for YouTube AND TikTok)\n"
        "Header: x-api-key\n"
        "Params: url, text=true for plain text",
        ["supadata", "api", "transcripts", "tiktok", "youtube"])

    add("knowledge", 8, "Multi-Model Routing",
        "Ollama (local) 15% — heartbeats, formatting, $0\n"
        "Haiku 75% — research, classification, ~$0.80/M\n"
        "Sonnet 10% — social posts, scripts, mid cost\n"
        "Opus 3-5% — strategy, crisis, premium\n"
        "Cost targets: Idle $0/day, Active ~$1/hour",
        ["models", "cost", "routing", "ollama", "haiku", "sonnet", "opus"])

    add("knowledge", 8, "David's Memory System — Three Layers",
        "1. EventStore (core/memory/event_store.py) — Decaying events with significance 1-10. "
        "Same DECAY_RATES as Claude's memory. Recall boost +0.15 on access. "
        "Clear (>0.7), Fuzzy (0.4-0.7), Blank (<0.3).\n"
        "2. PeopleStore (core/memory/people_store.py) — NEVER fades. Relationships.\n"
        "3. KnowledgeStore (core/memory/knowledge_store.py) — NEVER fades. Company facts.",
        ["memory", "eventstore", "decay", "peoplestore"])

    add("knowledge", 8, "Deva's Memory System — Three Layers",
        "1. DevaMemory (voice/memory/memory_manager.py) — user profile, conversation history, "
        "knowledge with FTS5 search\n"
        "2. GroupMemory — shared game dev solutions across users, upvotes, dedup\n"
        "3. GameMemory — per-project: architecture, file mappings, solved bugs, decisions\n"
        "Databases: data/deva_memory.db, data/deva_group_knowledge.db, data/deva_games.db",
        ["deva", "memory", "groupmemory", "gamememory"])

    add("knowledge", 8, "Deva's Voice System",
        "STT: RealtimeSTT with Whisper 'small' model (Australian accent support)\n"
        "TTS: ElevenLabs eleven_flash_v2_5 (~0.8s generation)\n"
        "Voice: Veronica — 'Sassy and Energetic' (ejl43bbp2vjkAFGSmAMa)\n"
        "Trigger: 'DEVA, execute program' to switch from conversation to action mode\n"
        "Conversation persistence: last 50 exchanges saved to data/conversation_history.json\n"
        "Brain: Claude Opus (upgraded from Sonnet)",
        ["deva", "voice", "whisper", "elevenlabs", "veronica"])

    add("knowledge", 8, "Wall Mode — Gemini 1M Context",
        "Wall Mode loads entire codebases for analysis.\n"
        "Uses Gemini 2.5 Flash (1M tokens, <5% degradation) — NOT Llama 4 Scout "
        "(10M claimed but degrades to 15.6% after 256K).\n"
        "Files: voice/wall_mode.py (collector), voice/gemini_client.py (API client)\n"
        "GOOGLE_API_KEY in .env. ~$1 per deep dive at 800K tokens.\n"
        "Tested: Amphitheatre (158 files, 800K tokens, 28.7s full walkthrough)",
        ["wall-mode", "gemini", "context", "amphitheatre"])

    add("knowledge", 8, "FRONTMAN — Video Production Engine",
        "URL: www.frontman.site (user's own project)\n"
        "Extracts: ElevenLabs voice synthesis, Hedra AI lip-sync, "
        "FFmpeg 5-track audio mixing, ASS caption system\n"
        "Tech: Express.js/React/TypeScript, PostgreSQL, BullMQ",
        ["frontman", "video", "elevenlabs", "hedra", "ffmpeg"])

    add("knowledge", 8, "Content Strategy",
        "Positioning Phase: surveillance warnings (2x/week), story series (2x/week), "
        "'Why I Believe In You' (1x/week), short hooks (daily), news reactions (as needed)\n"
        "Selling Phase (bull run): FLIPT explainers, node ownership, perpetual royalties\n"
        "Content Safety (UAE): no specific government targeting, focus Western systems, "
        "tone is 'opt out and build alternatives' NOT 'rise up and fight'",
        ["content", "strategy", "surveillance", "uae", "bull-run"])

    # ==================================================================
    # CURRENT STATE — What's true RIGHT NOW (no decay, manually updated)
    # ==================================================================

    add("current_state", 8, "Project Phase",
        "Phase 1 BUILD IN PROGRESS. Foundation code written, needs API keys and testing.\n"
        "Local development on ASUS ROG laptop at C:\\Projects\\Clawdbot\n"
        "VPS running at 89.167.24.222 (code at /opt/david-flip/)",
        ["phase1", "build"])

    add("current_state", 8, "Oprah — Not Yet Wired",
        "Oprah's files are created (personality/oprah.py, agents/operations_agent.py) "
        "and dashboard updated. But main.py still uses the OLD methods directly.\n"
        "TODO: Import OperationsAgent in main.py, create instance after Telegram init, "
        "delegate execute_action() and poll_dashboard_actions() to Oprah.\n"
        "Also register Oprah's _execute_scheduled_video with ContentScheduler.",
        ["oprah", "wiring", "main.py", "todo"])

    add("current_state", 8, "Research Agent — Built, Not Deployed",
        "Research agent built in agents/research_agent/ with 4 scrapers "
        "(RSS, GitHub, Reddit, YouTube) + transcript scraper + evaluator.\n"
        "NOT YET deployed to VPS. Needs: pip install, copy files, restart.",
        ["research", "deploy", "vps", "todo"])

    add("current_state", 7, "Dashboard — Running Locally",
        "Flask dashboard at C:\\Projects\\Clawdbot\\dashboard\\app.py\n"
        "Runs at 127.0.0.1:5000 with auto-reload.\n"
        "Shows: David Flip, Echo, Oprah (orange), Deva (standby purple)\n"
        "VPS dashboard must be started manually.",
        ["dashboard", "flask", "local"])

    add("current_state", 7, "Project Working Directory",
        "Local: C:\\Projects\\Clawdbot\\ (main branch)\n"
        "Worktree (if any): C:\\Users\\David\\.claude-worktrees\\Clawdbot\\cool-wing\\\n"
        "REAL dashboard = C:\\Projects\\Clawdbot\\dashboard\\ (Flask auto-reloads from here)\n"
        "Git remote: origin/main\n"
        "Python venv: C:\\Projects\\Clawdbot\\venv\\ — use venv/Scripts/python.exe for packages",
        ["paths", "venv", "git", "worktree"])

    # ==================================================================
    # DECISIONS — Things we decided and why (decays based on significance)
    # ==================================================================

    add("decision", 9, "Build Our Own, Not OpenClaw",
        "Decision: Build our own agent system, not use OpenClaw directly.\n"
        "Reason: Safety-first. OpenClaw is vulnerable to prompt injection, "
        "persistent memory poisoning, and has no human-in-the-loop by default.\n"
        "We extract the useful patterns (tool loop, model routing) and add "
        "our own safety gates at every step.",
        ["architecture", "openclaw", "security"])

    add("decision", 9, "Deva Freed From Operations",
        "Decision: Deva is no longer tied to operations duties.\n"
        "Oprah takes over the entire post-approval pipeline.\n"
        "Deva's role is now 'Game Developer (standby)' across all systems.\n"
        "Made: February 9, 2026",
        ["deva", "oprah", "operations", "roles"])

    add("decision", 8, "Wall Mode Uses Gemini, Not Llama 4",
        "Decision: Use Gemini 2.5 Flash for Wall Mode, not Llama 4 Scout.\n"
        "Reason: Llama 4's 10M context is marketing — accuracy drops to 15.6% after 256K. "
        "Gemini 2.5 Flash maintains <5% degradation across full 1M window.\n"
        "Research: research/wall-mode-model-research.md",
        ["wall-mode", "gemini", "llama4"])

    add("decision", 8, "Dual Scoring Rubrics for Research",
        "Decision: Research evaluator runs TWO rubrics in parallel.\n"
        "1. David Flip rubric — 'Can someone be switched off?' (surveillance focus)\n"
        "2. Technical rubric — 'How does this help Clawdbot, DEVA, Amphitheatre?'\n"
        "Highest score wins. Prevents AI tutorials from being buried by surveillance-only scoring.",
        ["research", "scoring", "rubrics", "evaluator"])

    add("decision", 8, "Execute Program Trigger Words",
        "Decision: Deva uses explicit trigger words for tool activation.\n"
        "Old system: broad words like 'please', 'can you', 'add' triggered tools during casual chat.\n"
        "New system: chat freely, say 'DEVA, execute program' when ready for action.\n"
        "Deva reviews full conversation history to understand what to do.",
        ["deva", "trigger", "execute-program", "tools"])

    add("decision", 7, "Oprah's Design — No Own Event Loop",
        "Oprah doesn't run her own timer. main.py's cron scheduler calls "
        "poll_dashboard_actions() every 30 seconds. Oprah is the handler, not the scheduler.\n"
        "This is simpler and avoids two competing event loops.",
        ["oprah", "polling", "cron", "design"])

    add("decision", 7, "YouTube OAuth — Correct Channel",
        "YouTube OAuth must use David Flip Google account, NOT main PLAYA3ULL_GAMES account.\n"
        "Channel ID: UCBNP7tMEMf21Ks2RmnblQDw\n"
        "Channel verification added to youtube_tool.py to block wrong-channel uploads.\n"
        "Lesson: Delete data/youtube_token.pickle if wrong account authorized.",
        ["youtube", "oauth", "channel"])

    add("decision", 7, "Transcript Scraper — Two-Pass Evaluation",
        "Long transcripts (>2000 chars) get summarized by Haiku first, "
        "then standard goal scoring runs on the summary. Saves tokens.\n"
        "youtube-transcript-api v2+ uses instance method: YouTubeTranscriptApi().fetch(video_id)",
        ["transcripts", "haiku", "summarization"])

    # ==================================================================
    # SESSION SUMMARIES — Decay normally based on significance
    # ==================================================================

    add("session", 7, "Feb 9 — Oprah Operations Agent Created",
        "Created personality/oprah.py and agents/operations_agent.py.\n"
        "Updated all 4 dashboard templates to show Oprah instead of Deva for operations.\n"
        "Committed 37 files (7339 insertions) including multi-session backlog.\n"
        "Pushed: a92f091..6753262 main -> main",
        ["oprah", "dashboard", "git"])

    add("session", 7, "Feb 9 — Video Intelligence System",
        "Built transcript_scraper.py (YouTube + TikTok via Supadata API).\n"
        "Added dual scoring rubrics to evaluator. Expanded keywords to ~150.\n"
        "Added 5 YouTube channels and 6 TikTok accounts to monitoring.\n"
        "Commits: 1b64c72, eb9b24c",
        ["transcripts", "research", "scraper"])

    add("session", 6, "Feb 9 — Transcript Research (3 Videos)",
        "Fetched transcripts for 3 videos:\n"
        "1. YouTube (cod50CWlZeU): 'OpenClaw Setup Guide' by David — 50K chars. "
        "VPS setup, model switching, living files theory, agentic company structure.\n"
        "2. TikTok (@alec.automations): Clawbot cost problem. Switch to Kimi 2.5 from Moonshot (<$5/day).\n"
        "3. TikTok (@zachdoeslife_): 5 best MCP servers — Perplexity, Playwright, Firecrawl, Glif, Chrome.\n"
        "Supadata unified endpoint: /v1/transcript (not /v1/tiktok/transcript)",
        ["transcripts", "openclaw", "kimi", "mcp"])

    add("session", 6, "Feb 8 — DEVA Major Overhaul",
        "Fixed tools not executing, [SAY] tag system for speech, upgraded to Opus.\n"
        "Added 'execute program' trigger, conversation persistence (50 exchanges).\n"
        "Seeded DevaMemory and GameMemory. Tuned STT sensitivity.\n"
        "Set up Amphitheatre project at C:\\Games\\Amphitheatre (60K files).",
        ["deva", "tools", "say-tags", "persistence"])

    add("session", 6, "Feb 8 — Wall Mode Complete",
        "Built voice/wall_mode.py and voice/gemini_client.py.\n"
        "Tested on Amphitheatre: 158 files, 800K tokens, 28.7s.\n"
        "Complete code flow analysis with file paths and LINE NUMBERS.",
        ["wall-mode", "gemini", "amphitheatre"])

    add("session", 6, "Feb 7 — David Memory + Personality Update",
        "Built core/memory/ with EventStore (decay), PeopleStore, KnowledgeStore.\n"
        "David personality updated — less robotic, young casual voice.\n"
        "Status notifications (awake/offline). Desktop shortcuts created.",
        ["memory", "personality", "status"])

    add("session", 5, "Feb 6 — Research Agent Built",
        "Complete research agent in agents/research_agent/.\n"
        "4 scrapers (RSS, GitHub, Reddit, YouTube). 8 goals, ~150 keywords.\n"
        "2FA added to Telegram. Debasement chart working.",
        ["research", "scrapers", "2fa"])

    add("session", 5, "Feb 6 — Worldview Document",
        "Created personality/david_worldview.md (968 lines).\n"
        "Oracle archetype, philosophical framework, redirect techniques, "
        "crisis response, platform-specific behavior, quotable takes.",
        ["worldview", "personality", "oracle"])

    add("session", 5, "Feb 5 — Story Series + Content Calendar",
        "12 story episodes in content/story_series.py.\n"
        "Content calendar in content/content_calendar.py.\n"
        "Telegram /video command working. Twitter video posting working.",
        ["stories", "content", "calendar"])

    return count

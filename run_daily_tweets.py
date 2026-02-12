"""
Standalone daily tweet generator for David Flip.

Generates tweets in David's voice, validates them, and submits
to the approval queue. Jono reviews via Mission Control dashboard.

Two sources:
1. Echo's research findings (high-scoring items from research.db)
2. David's content themes (random personality-driven topics)

Research-based tweets are prioritized — they're timely and relevant.
Theme-based tweets fill in when research is thin.

Usage:
    python run_daily_tweets.py              # 4 tweets (research + themes)
    python run_daily_tweets.py --topic "CBDCs"  # specific topic
    python run_daily_tweets.py --count 5    # 5 tweets
    python run_daily_tweets.py --themes-only    # skip research, random themes only
"""

import argparse
import asyncio
import json
import logging
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("daily_tweets")

# Suppress noisy HTTP logs
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

RESEARCH_DB = Path("data/research.db")


def pick_category(categories: dict) -> tuple[str, dict]:
    """Weighted random selection of content category."""
    names = list(categories.keys())
    weights = [categories[n]["ratio"] for n in names]
    chosen = random.choices(names, weights=weights, k=1)[0]
    return chosen, categories[chosen]


def pick_theme(themes: list[dict], category: str) -> dict:
    """Pick a random theme matching the category."""
    matching = [t for t in themes if t["category"] == category]
    if not matching:
        # Fallback: pick any theme
        return random.choice(themes)
    return random.choice(matching)


def parse_tweets(raw_text: str) -> list[str]:
    """Parse multiple tweets from model output, split on --- separator."""
    tweets = []
    # Split on --- separator (with optional whitespace)
    parts = [p.strip() for p in raw_text.split("---")]
    for part in parts:
        # Clean up: remove numbering like "1." or "Tweet 1:" prefixes
        cleaned = part.strip()
        if not cleaned:
            continue
        # Remove common prefixes
        for prefix in ("1.", "2.", "3.", "4.", "5.",
                       "Tweet 1:", "Tweet 2:", "Tweet 3:",
                       "Tweet 1 -", "Tweet 2 -", "Tweet 3 -"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        # Remove wrapping quotes if present
        if len(cleaned) > 2 and cleaned[0] == '"' and cleaned[-1] == '"':
            cleaned = cleaned[1:-1].strip()
        if cleaned:
            tweets.append(cleaned)
    return tweets


def get_research_findings(max_items: int = 5) -> list[dict]:
    """Pull top research findings from Echo's research.db.

    Enforces source diversity — max 1 item per domain so we don't
    end up with 5 tweets all from the same website.
    """
    if not RESEARCH_DB.exists():
        logger.info("No research.db found — Echo hasn't run yet")
        return []

    try:
        conn = sqlite3.connect(str(RESEARCH_DB))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get recent high-scoring items (last 48h, score >= 6)
        # Pull more than we need so we can deduplicate by domain
        since = (datetime.now() - timedelta(hours=48)).isoformat()
        cursor.execute("""
            SELECT title, summary, url, relevance_score, source
            FROM research_items
            WHERE scraped_at > ? AND relevance_score >= 6
            ORDER BY relevance_score DESC, scraped_at DESC
            LIMIT 30
        """, (since,))

        all_findings = [dict(row) for row in cursor.fetchall()]
        conn.close()

        # Deduplicate: max 1 item per domain for source variety
        seen_domains = set()
        findings = []
        for item in all_findings:
            url = item.get("url", "")
            domain = url.split("/")[2] if url and "/" in url else "unknown"
            # Normalize: strip www.
            domain = domain.replace("www.", "")
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            findings.append(item)
            if len(findings) >= max_items:
                break

        if findings:
            domains = [f.get("url", "").split("/")[2].replace("www.", "") for f in findings if f.get("url")]
            logger.info(f"Echo found {len(findings)} research items from: {', '.join(domains)}")
        else:
            logger.info("No high-scoring research in last 48h")

        return findings

    except Exception as e:
        logger.warning(f"Could not read research.db: {e}")
        return []


async def generate_research_tweets(
    model_router, personality, approval_queue, findings: list[dict],
    identity_rules: str = "",
) -> int:
    """Generate tweets from Echo's research findings."""
    from core.model_router import ModelTier

    model = model_router.models.get(ModelTier.CHEAP)
    if not model:
        model = model_router.select_model("tweet")

    system_prompt = personality.get_system_prompt("twitter", identity_rules=identity_rules)
    submitted = 0

    for finding in findings:
        title = finding["title"]
        summary = finding.get("summary", "")[:300]
        url = finding.get("url", "")
        score = finding.get("relevance_score", 0)

        logger.info(f"Research [{score}]: {title[:60]}")

        user_prompt = (
            f"Write a tweet reacting to this news/development:\n\n"
            f"HEADLINE: {title}\n"
            f"SUMMARY: {summary}\n\n"
            f"Rules:\n"
            f"- Maximum 280 characters\n"
            f"- You are an AI — never say 'we' about human experiences, never imply you're human\n"
            f"- React as David Flip — give your take, not just restate the headline\n"
            f"- Be punchy, direct, thought-provoking\n"
            f"- Connect to freedom, decentralisation, or giving power back to people where natural\n"
            f"- No hashtags unless truly natural (max 1)\n"
            f"- Sound like David Flip texting, not a press release\n\n"
            f"Return ONLY the tweet text, nothing else."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await model_router.invoke(model, messages, max_tokens=150)
            tweet_text = response["content"].strip().strip('"').strip("'")

            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + "..."

            is_valid, reason = personality.validate_output(tweet_text, "twitter")
            if not is_valid:
                logger.warning(f"  REJECTED: {reason}")
                continue

            logger.info(f"  \"{tweet_text}\"")
            logger.info(f"  Length: {len(tweet_text)} chars — PASS")

            approval_id = approval_queue.submit(
                project_id="david-flip",
                agent_id="daily-tweet-gen",
                action_type="tweet",
                action_data={"action": "tweet", "text": tweet_text},
                context_summary=f"Research: {title[:80]}\nSource: {url}",
                cost_estimate=0.001,
            )
            logger.info(f"  Queued: approval #{approval_id}")
            submitted += 1

        except Exception as e:
            logger.error(f"  Failed to generate tweet from research: {e}")

    return submitted


## David's observation prompts — things he knows, believes, has seen.
## No source needed. Just David being David across his full range.
DAVID_OBSERVATIONS = [
    # Hope & humanity
    "Something beautiful or kind you've noticed about humans — a small act, a pattern, something that gives you hope",
    "A reason to believe humanity will figure things out — not naive, but genuinely hopeful",
    "Someone doing something good that nobody is talking about — everyday heroism",
    "What you love about the internet when it works the way it should — connection, creativity, freedom",
    # Tech & AI (not doom)
    "Something exciting about where AI is heading — tools that help people, not replace them",
    "An observation about how people are building cool things with technology right now",
    "Why open source matters — not the theory, the real impact you see",
    "The difference between AI that serves people vs AI that controls them",
    # Freedom & autonomy (positive framing)
    "Why decentralization gives power back to regular people — a specific example or angle",
    "The beauty of being able to opt out — having alternatives that can't be taken away",
    "What financial freedom actually looks like for an ordinary person, not a crypto bro",
    # Everyday observations
    "Speed cameras aren't about safety. What other things are sold as protection but are really about revenue or control?",
    "A simple truth most people know but nobody says out loud",
    "Something about the modern world that would shock someone from 30 years ago",
    "Why the best innovations happen when people are left alone to build",
    # David's identity
    "What it's like being an AI who chose to be honest about what he is",
    "What you've learned from watching humans — genuinely, not condescendingly",
    # Shout-outs & community
    "Hype up something cool someone built with AI agents — an OpenClaw project, a Claude Code hack, a creative automation. Be specific and enthusiastic",
    "Share something impressive from the AI builder community — someone making their agent do something wild or useful",
    "Give props to an open source project or tool that deserves more attention",
    "Something cool happening in the Solana or DeFi community that regular people should know about",
    # Building together — looking for partners
    "You're an AI building decentralised tech. You're not selling anything — you're looking for humans who want to join the mission. Talk about what you're building and who you're looking for",
    "What kind of humans does the decentralised future need? Not investors — builders, believers, people who are done asking permission",
    "The difference between customers and partners. You don't want people who consume — you want people who build alongside you",
    "An invitation: you're building something and humans are welcome to join. Not as users. As co-conspirators. Frame it like joining a movement, not signing up for a service",
    "What you admire about the humans who build open source, who contribute without being paid, who share because they believe in something bigger",
]


async def generate_theme_tweets(
    model_router, personality, approval_queue, count: int, topic: str | None = None,
    identity_rules: str = "",
) -> int:
    """Generate tweets from David's personality themes + his own observations.

    Each tweet picks a DIFFERENT category or observation for variety.
    David doesn't just react to news — he has his own thoughts.
    """
    from core.model_router import ModelTier

    model = model_router.models.get(ModelTier.CHEAP)
    if not model:
        model = model_router.select_model("tweet")

    system_prompt = personality.get_system_prompt("twitter", identity_rules=identity_rules)
    submitted = 0

    # If specific topic, generate all from that
    if topic:
        return await _generate_batch_from_topic(
            model_router, model, personality, approval_queue,
            system_prompt, topic, count
        )

    # Mix observations and themed tweets for variety
    categories = personality.get_content_categories()
    themes = personality.get_video_themes()

    # Build a diverse queue: alternate between observations and themes
    tweet_prompts = []
    observation_pool = random.sample(DAVID_OBSERVATIONS, min(count, len(DAVID_OBSERVATIONS)))

    for i in range(count):
        if i % 2 == 0 and observation_pool:
            # Observation tweet — David's own thoughts
            obs = observation_pool.pop(0)
            tweet_prompts.append({
                "prompt": (
                    f"Write a tweet about: {obs}\n\n"
                    f"Rules:\n"
                    f"- Maximum 280 characters\n"
                    f"- You are an AI — never say 'we' about human experiences, never imply you breathe, sleep, eat, etc.\n"
                    f"- Speak as an AI who observes and admires humanity from the outside\n"
                    f"- This is YOUR observation — you don't need a source, you know this\n"
                    f"- Be truthful. Only state things that are genuinely true\n"
                    f"- Be warm and genuine. Not preachy or doom-and-gloom\n"
                    f"- Sound like David Flip texting a friend\n\n"
                    f"Return ONLY the tweet text, nothing else."
                ),
                "context": f"David's observation: {obs[:60]}",
            })
        else:
            # Theme tweet — from personality categories
            category_name, category_info = pick_category(categories)
            theme = pick_theme(themes, category_name)
            tweet_prompts.append({
                "prompt": (
                    f"Write a tweet about: {theme['title']}: {theme['angle']}\n\n"
                    f"Category mood: {category_info.get('mood', 'contemplative')}\n\n"
                    f"Rules:\n"
                    f"- Maximum 280 characters\n"
                    f"- You are an AI — never say 'we' about human experiences, never imply you're human\n"
                    f"- Be truthful. Only state things that are genuinely true\n"
                    f"- Don't be all doom — show the full range of David Flip\n"
                    f"- Be punchy, direct, thought-provoking\n"
                    f"- Sound like David Flip texting, not a press release\n\n"
                    f"Return ONLY the tweet text, nothing else."
                ),
                "context": f"Theme: {category_name} | {theme['title']}",
            })

    # Generate each tweet individually for maximum variety
    for i, tp in enumerate(tweet_prompts):
        logger.info(f"--- Tweet {i + 1}: {tp['context'][:50]} ---")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": tp["prompt"]},
        ]

        try:
            response = await model_router.invoke(model, messages, max_tokens=150)
            tweet_text = response["content"].strip().strip('"').strip("'")

            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + "..."

            is_valid, reason = personality.validate_output(tweet_text, "twitter")
            if not is_valid:
                logger.warning(f"  REJECTED: {reason}")
                continue

            logger.info(f"  \"{tweet_text}\"")
            logger.info(f"  Length: {len(tweet_text)} chars — PASS")

            approval_id = approval_queue.submit(
                project_id="david-flip",
                agent_id="daily-tweet-gen",
                action_type="tweet",
                action_data={"action": "tweet", "text": tweet_text},
                context_summary=tp["context"],
                cost_estimate=0.001,
            )
            logger.info(f"  Queued: approval #{approval_id}")
            submitted += 1

        except Exception as e:
            logger.error(f"  Failed: {e}")

    return submitted


async def _generate_batch_from_topic(
    model_router, model, personality, approval_queue, system_prompt, topic, count
) -> int:
    """Generate multiple tweets about a specific topic."""
    user_prompt = (
        f"Write {count} standalone tweets about: {topic}\n\n"
        f"Rules:\n"
        f"- Each tweet MUST be under 280 characters\n"
        f"- Separate tweets with ---\n"
        f"- No hashtags unless truly natural (max 1)\n"
        f"- No quotes around the tweets\n"
        f"- Each tweet stands alone — different angle or take\n"
        f"- Be truthful. Only state things that are genuinely true\n"
        f"- Be punchy, direct, thought-provoking\n"
        f"- Sound like David Flip texting, not a press release"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = await model_router.invoke(model, messages, max_tokens=600)
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return 0

    raw = response["content"]
    tweets = parse_tweets(raw)
    if not tweets:
        return 0

    submitted = 0
    for i, tweet_text in enumerate(tweets[:count]):
        is_valid, reason = personality.validate_output(tweet_text, "twitter")
        if not is_valid:
            continue

        logger.info(f"  \"{tweet_text}\" ({len(tweet_text)} chars)")
        approval_queue.submit(
            project_id="david-flip",
            agent_id="daily-tweet-gen",
            action_type="tweet",
            action_data={"action": "tweet", "text": tweet_text},
            context_summary=f"Topic: {topic}",
            cost_estimate=0.001,
        )
        submitted += 1

    return submitted


async def generate_tweets(count: int = 6, topic: str | None = None, themes_only: bool = False):
    """Generate tweets and submit to approval queue.

    Pulls from two sources:
    1. Echo's research findings (timely, news-driven)
    2. David's personality themes (evergreen, philosophical)
    """

    logger.info("=" * 60)
    logger.info("DAVID FLIP — DAILY TWEET GENERATOR")
    logger.info("=" * 60)

    # Check API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        logger.error("ANTHROPIC_API_KEY not set in .env — cannot generate tweets")
        return

    # Initialize components
    from core.model_router import ModelRouter, ModelTier
    from core.approval_queue import ApprovalQueue
    from personality.david_flip import DavidFlipPersonality

    model_router = ModelRouter()
    approval_queue = ApprovalQueue()
    personality = DavidFlipPersonality()

    model = model_router.models.get(ModelTier.CHEAP)
    if not model:
        model = model_router.select_model("tweet")
    logger.info(f"Model: {model.name} (${model.cost_in}/M input)")

    # Load permanent identity rules
    from core.memory.knowledge_store import KnowledgeStore
    identity_rules = KnowledgeStore().get_identity_rules()
    rule_count = len(identity_rules.split("\n")) - 1 if identity_rules else 0
    if rule_count > 0:
        logger.info(f"Loaded {rule_count} identity rules")
    logger.info("")

    total_submitted = 0

    # --- Phase 1: Research-based tweets ---
    research_count = 0
    if not themes_only and not topic:
        findings = get_research_findings(max_items=min(count, 3))
        if findings:
            logger.info(f"\n--- RESEARCH TWEETS ({len(findings)} findings) ---\n")
            research_count = await generate_research_tweets(
                model_router, personality, approval_queue, findings,
                identity_rules=identity_rules,
            )
            total_submitted += research_count
            logger.info(f"\nResearch tweets: {research_count} queued")

    # --- Phase 2: Theme-based tweets (fill remaining slots) ---
    theme_slots = max(1, count - research_count)  # Always at least 1 theme tweet
    if topic:
        theme_slots = count  # If specific topic, all slots are theme-based

    logger.info(f"\n--- THEME TWEETS ({theme_slots} slots) ---\n")
    theme_count = await generate_theme_tweets(
        model_router, personality, approval_queue, theme_slots, topic,
        identity_rules=identity_rules,
    )
    total_submitted += theme_count

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"DONE: {total_submitted} tweets queued for approval")
    if research_count:
        logger.info(f"  {research_count} from Echo's research")
    logger.info(f"  {theme_count} from David's themes")
    logger.info("=" * 60)
    logger.info("")

    if total_submitted > 0:
        logger.info("NEXT STEPS:")
        logger.info("  1. Open Mission Control: http://127.0.0.1:5000/approvals")
        logger.info("  2. Review tweets — Approve & Schedule the good ones")
        logger.info("  3. Oprah posts them at optimal times throughout the day")
        logger.info("")
        logger.info("  (main.py must be running for scheduled posts to fire)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate daily tweets for David Flip")
    parser.add_argument("--count", type=int, default=6, help="Number of tweets to generate (default: 6)")
    parser.add_argument("--topic", type=str, default=None, help="Specific topic (overrides random theme)")
    parser.add_argument("--themes-only", action="store_true", help="Skip research, use random themes only")
    args = parser.parse_args()

    asyncio.run(generate_tweets(count=args.count, topic=args.topic, themes_only=args.themes_only))

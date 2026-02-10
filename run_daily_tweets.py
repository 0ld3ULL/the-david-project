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
    model_router, personality, approval_queue, findings: list[dict]
) -> int:
    """Generate tweets from Echo's research findings."""
    from core.model_router import ModelTier

    model = model_router.models.get(ModelTier.CHEAP)
    if not model:
        model = model_router.select_model("tweet")

    system_prompt = personality.get_system_prompt("twitter")
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


async def generate_theme_tweets(
    model_router, personality, approval_queue, count: int, topic: str | None = None
) -> int:
    """Generate tweets from David's personality themes (original logic)."""
    from core.model_router import ModelTier

    model = model_router.models.get(ModelTier.CHEAP)
    if not model:
        model = model_router.select_model("tweet")

    categories = personality.get_content_categories()
    themes = personality.get_video_themes()

    category_name, category_info = pick_category(categories)
    theme = pick_theme(themes, category_name)

    logger.info(f"Theme: {category_name} — {theme['title']}")

    system_prompt = personality.get_system_prompt("twitter")

    if topic:
        user_content = topic
    else:
        user_content = f"{theme['title']}: {theme['angle']}"

    user_prompt = (
        f"Write {count} standalone tweets about: {user_content}\n\n"
        f"Category mood: {category_info.get('mood', 'contemplative')}\n\n"
        f"Rules:\n"
        f"- Each tweet MUST be under 280 characters\n"
        f"- Separate tweets with ---\n"
        f"- No hashtags unless truly natural (max 1)\n"
        f"- No quotes around the tweets\n"
        f"- Each tweet stands alone — different angle or take\n"
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
        logger.warning("No tweets parsed from model output.")
        return 0

    submitted = 0
    for i, tweet_text in enumerate(tweets[:count]):
        logger.info(f"--- Theme Tweet {i + 1} ---")
        logger.info(f"  \"{tweet_text}\"")
        logger.info(f"  Length: {len(tweet_text)} chars")

        is_valid, reason = personality.validate_output(tweet_text, "twitter")
        if not is_valid:
            logger.warning(f"  REJECTED: {reason}")
            continue

        logger.info(f"  Validation: PASS")

        approval_id = approval_queue.submit(
            project_id="david-flip",
            agent_id="daily-tweet-gen",
            action_type="tweet",
            action_data={"action": "tweet", "text": tweet_text},
            context_summary=f"Daily tweet | {category_name} | {theme['title']}",
            cost_estimate=0.001,
        )
        logger.info(f"  Queued: approval #{approval_id}")
        submitted += 1

    return submitted


async def generate_tweets(count: int = 4, topic: str | None = None, themes_only: bool = False):
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
    logger.info("")

    total_submitted = 0

    # --- Phase 1: Research-based tweets ---
    research_count = 0
    if not themes_only and not topic:
        findings = get_research_findings(max_items=min(count, 3))
        if findings:
            logger.info(f"\n--- RESEARCH TWEETS ({len(findings)} findings) ---\n")
            research_count = await generate_research_tweets(
                model_router, personality, approval_queue, findings
            )
            total_submitted += research_count
            logger.info(f"\nResearch tweets: {research_count} queued")

    # --- Phase 2: Theme-based tweets (fill remaining slots) ---
    theme_slots = max(1, count - research_count)  # Always at least 1 theme tweet
    if topic:
        theme_slots = count  # If specific topic, all slots are theme-based

    logger.info(f"\n--- THEME TWEETS ({theme_slots} slots) ---\n")
    theme_count = await generate_theme_tweets(
        model_router, personality, approval_queue, theme_slots, topic
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
    parser.add_argument("--count", type=int, default=4, help="Number of tweets to generate (default: 4)")
    parser.add_argument("--topic", type=str, default=None, help="Specific topic (overrides random theme)")
    parser.add_argument("--themes-only", action="store_true", help="Skip research, use random themes only")
    args = parser.parse_args()

    asyncio.run(generate_tweets(count=args.count, topic=args.topic, themes_only=args.themes_only))

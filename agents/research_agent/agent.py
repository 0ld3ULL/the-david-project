"""
Echo - Intelligence Analyst for the David Flip network.

Autonomous research agent that:
1. Scrapes multiple sources on tiered frequencies (hot/warm/daily)
2. Evaluates findings against goals using dual rubrics + LLM fallback
3. Detects cross-source trends
4. Routes to appropriate actions
5. Generates daily podcast/newsletter
6. Sends daily digest to operator
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

import yaml

from .knowledge_store import KnowledgeStore, ResearchItem
from .evaluator import GoalEvaluator
from .action_router import ActionRouter
from .trend_detector import TrendDetector
from .podcast_digest import PodcastDigestGenerator
from .scrapers import (
    RSSScraper, GitHubScraper, RedditScraper, YouTubeScraper,
    TranscriptScraper, HackerNewsScraper, TwitterScraper,
    GitHubTrendingScraper, ArXivScraper, PerplexityScraper,
    FirecrawlScraper,
)

if TYPE_CHECKING:
    from core.model_router import ModelRouter
    from core.approval_queue import ApprovalQueue

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/research_goals.yaml"


class ResearchAgent:
    """
    Echo — Autonomous intelligence analyst.

    Scrapes, evaluates, and acts on information across the AI/tech landscape.

    Supports three frequency tiers:
    - HOT: Every 2-4 hours (Twitter, HN) - breaking news
    - WARM: Every 8-12 hours (RSS, Reddit, GitHub) - daily coverage
    - DAILY: Once per day (transcripts, ArXiv) - deep content

    Full daily cycle:
    1. Run all scrapers (or tier-specific subset)
    2. Deduplicate against seen items
    3. Evaluate each item against goals (using LLM)
    4. Detect cross-source trends
    5. Route relevant items to actions
    6. Store all items in database
    7. Generate podcast/newsletter (daily only)
    8. Send digest
    """

    def __init__(self, model_router: "ModelRouter",
                 approval_queue: "ApprovalQueue",
                 telegram_bot=None,
                 memory_manager=None):
        self.router = model_router
        self.queue = approval_queue
        self.telegram = telegram_bot
        self.memory = memory_manager

        # Load Echo personality
        self.personality = self._load_personality()

        # Load config
        self.config = self._load_config()

        # Initialize components
        self.store = KnowledgeStore()
        self.evaluator = GoalEvaluator(model_router)
        self.action_router = ActionRouter(
            approval_queue, model_router, telegram_bot, memory_manager
        )
        self.trend_detector = TrendDetector()
        self.podcast_generator = PodcastDigestGenerator(model_router, personality=self.personality)

        # Initialize ALL scrapers
        self.all_scrapers = [
            RSSScraper(),
            GitHubScraper(),
            RedditScraper(),
            YouTubeScraper(),
            TranscriptScraper(),
            HackerNewsScraper(),
            TwitterScraper(),
            GitHubTrendingScraper(),
            ArXivScraper(),
            PerplexityScraper(),
            FirecrawlScraper(),
        ]

        # Group scrapers by frequency tier
        self.tier_scrapers = self._group_by_tier()

        # Store last podcast for retrieval
        self.last_podcast = None

        logger.info(
            f"Echo initialized with {len(self.all_scrapers)} scrapers "
            f"(hot: {len(self.tier_scrapers.get('hot', []))}, "
            f"warm: {len(self.tier_scrapers.get('warm', []))}, "
            f"daily: {len(self.tier_scrapers.get('daily', []))})"
        )

    def _load_personality(self):
        """Load Echo personality configuration."""
        try:
            from personality.echo import EchoPersonality
            return EchoPersonality()
        except ImportError:
            logger.warning("Could not load EchoPersonality, using defaults")
            return None

    def _load_config(self) -> dict:
        """Load full config."""
        try:
            with open(CONFIG_PATH, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {}

    def _group_by_tier(self) -> dict:
        """Group scrapers into frequency tiers based on config."""
        tiers = self.config.get("frequency_tiers", {})

        hot_sources = set(tiers.get("hot", {}).get("sources", []))
        warm_sources = set(tiers.get("warm", {}).get("sources", []))
        daily_sources = set(tiers.get("daily", {}).get("sources", []))

        grouped = {"hot": [], "warm": [], "daily": []}

        for scraper in self.all_scrapers:
            freq = getattr(scraper, "frequency", None)
            name = scraper.name

            if freq == "hot" or name in hot_sources:
                grouped["hot"].append(scraper)
            elif freq == "warm" or name in warm_sources:
                grouped["warm"].append(scraper)
            elif freq == "daily" or name in daily_sources:
                grouped["daily"].append(scraper)
            else:
                # Default to warm
                grouped["warm"].append(scraper)

        return grouped

    async def run_tier(self, tier: str) -> dict:
        """
        Run scrapers for a specific frequency tier.
        Use this for hot/warm checks between full daily runs.

        Returns stats dict.
        """
        scrapers = self.tier_scrapers.get(tier, [])
        if not scrapers:
            logger.warning(f"No scrapers configured for tier: {tier}")
            return {"scraped": 0, "new": 0, "relevant": 0, "tier": tier}

        logger.info(f"Running {tier} tier research ({len(scrapers)} scrapers)...")
        return await self._run_scrapers(scrapers, send_digest=False, generate_podcast=False)

    async def run_daily_research(self) -> dict:
        """
        Main entry point - run full research cycle (ALL scrapers).
        Includes trend detection, podcast generation, and full digest.
        """
        logger.info("Starting FULL daily research cycle (all scrapers)...")
        return await self._run_scrapers(
            self.all_scrapers,
            send_digest=True,
            generate_podcast=True
        )

    async def _run_scrapers(self, scrapers: list,
                            send_digest: bool = True,
                            generate_podcast: bool = False) -> dict:
        """Core scraping pipeline shared by tier runs and full daily runs."""
        start_time = datetime.now()

        stats = {
            "scraped": 0,
            "new": 0,
            "relevant": 0,
            "alerts": 0,
            "tasks": 0,
            "content": 0,
            "knowledge": 0,
            "watch": 0,
            "trends": 0,
            "errors": [],
        }

        # 1. Scrape all sources in this set
        all_items = []
        for scraper in scrapers:
            try:
                items = await scraper.scrape()
                all_items.extend(items)
                logger.info(f"{scraper.name}: Found {len(items)} items")
            except Exception as e:
                error_msg = f"{scraper.name} failed: {e}"
                logger.error(error_msg)
                stats["errors"].append(error_msg)

        stats["scraped"] = len(all_items)

        # 2. Deduplicate against seen items
        new_items = self.store.filter_new(all_items)
        stats["new"] = len(new_items)
        logger.info(f"After dedup: {len(new_items)} new items")

        if not new_items:
            logger.info("No new items to process")
            if send_digest:
                await self._send_digest(stats, start_time)
            return stats

        # 3. Evaluate each item against goals
        evaluated = await self.evaluator.evaluate_batch(new_items)

        # 4. Detect cross-source trends
        trends = self.trend_detector.detect_trends(evaluated)
        stats["trends"] = len(trends)

        # 5. Boost scores for trending items
        if trends:
            evaluated = self.trend_detector.boost_scores(evaluated, trends)
            logger.info(f"Detected {len(trends)} trends, boosted scores")

        # 6. Filter relevant items and route actions
        relevant_items = [i for i in evaluated if i.relevance_score > 3]
        stats["relevant"] = len(relevant_items)

        if relevant_items:
            routing_stats = await self.action_router.route_batch(relevant_items)
            stats["alerts"] = routing_stats.get("alert_sent", 0)
            stats["tasks"] = routing_stats.get("task_created", 0)
            stats["content"] = routing_stats.get("content_queued", 0)
            stats["knowledge"] = routing_stats.get("knowledge_added", 0)
            stats["watch"] = routing_stats.get("watch_added", 0)

        # 7. Store all evaluated items
        self.store.save_batch(evaluated)

        # 8. Record digest stats
        self.store.record_digest({
            "items_scraped": stats["scraped"],
            "items_relevant": stats["relevant"],
            "alerts_sent": stats["alerts"],
            "tasks_created": stats["tasks"],
            "content_drafted": stats["content"],
        })

        # 9. Generate podcast/newsletter (daily only)
        if generate_podcast and relevant_items:
            try:
                self.last_podcast = await self.podcast_generator.generate(
                    relevant_items, trends
                )
                logger.info("Podcast/newsletter generated")

                # Send podcast summary to Telegram
                if self.telegram and self.last_podcast:
                    summary = self.podcast_generator.format_for_telegram(self.last_podcast)
                    await self.telegram.send_digest(summary)

            except Exception as e:
                logger.error(f"Podcast generation failed: {e}")
                stats["errors"].append(f"Podcast failed: {e}")

        # 10. Send digest
        if send_digest:
            await self._send_digest(stats, start_time, trends)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Research cycle complete in {duration:.1f}s: {stats}")

        return stats

    async def _send_digest(self, stats: dict, start_time: datetime,
                           trends: list = None):
        """Send daily digest to operator via Telegram in Echo's voice."""
        duration = (datetime.now() - start_time).total_seconds()

        # Use Echo's header if personality loaded
        header = "ECHO INTELLIGENCE BRIEF" if self.personality else "DAILY RESEARCH DIGEST"

        digest = (
            f"{header}\n"
            f"{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Scanned: {stats['scraped']} items across all sources\n"
            f"New: {stats['new']} | Relevant: {stats['relevant']} | "
            f"Trends: {stats.get('trends', 0)}\n\n"
            f"Actions routed:\n"
            f"  Alerts: {stats['alerts']}\n"
            f"  Tasks: {stats['tasks']}\n"
            f"  Content: {stats['content']}\n"
            f"  Knowledge: {stats['knowledge']}\n"
            f"  Watch: {stats.get('watch', 0)}\n\n"
            f"Cycle time: {duration:.1f}s"
        )

        if stats["errors"]:
            digest += f"\n\nErrors ({len(stats['errors'])}):\n"
            for err in stats["errors"][:5]:
                digest += f"  - {err[:80]}\n"

        # Add trend report
        if trends:
            trend_report = self.trend_detector.format_trend_report(trends[:5])
            digest += f"\n\n{trend_report}"

        if self.telegram:
            try:
                await self.telegram.send_digest(digest)
                logger.info("Digest sent to operator")
            except Exception as e:
                logger.error(f"Failed to send digest: {e}")
        else:
            logger.info(f"Digest (no Telegram):\n{digest}")

    async def get_recent_findings(self, hours: int = 24,
                                  min_relevance: float = 5) -> list[ResearchItem]:
        """Get recent relevant findings for display."""
        return self.store.get_recent(hours=hours, min_relevance=min_relevance)

    async def get_pending_alerts(self) -> list[ResearchItem]:
        """Get high-priority items that might need attention."""
        return self.store.get_by_priority("critical") + self.store.get_by_priority("high")

    def get_goals(self) -> list[dict]:
        """Get current research goals."""
        return self.evaluator.goals

    def get_digest_history(self, days: int = 7) -> list[dict]:
        """Get digest stats for the last N days."""
        return self.store.get_digest_stats(days=days)

    def get_last_podcast(self) -> Optional[dict]:
        """Get the most recently generated podcast."""
        return self.last_podcast

    async def close(self):
        """Clean up resources."""
        for scraper in self.all_scrapers:
            try:
                await scraper.close()
            except Exception as e:
                logger.warning(f"Error closing {scraper.name}: {e}")
        logger.info("Echo signing off")

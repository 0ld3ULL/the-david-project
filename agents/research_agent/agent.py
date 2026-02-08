"""
Research Agent - David's Intelligence Network.

Autonomous research agent that:
1. Scrapes multiple sources daily
2. Evaluates findings against goals
3. Routes to appropriate actions
4. Sends daily digest to operator
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from .knowledge_store import KnowledgeStore, ResearchItem
from .evaluator import GoalEvaluator
from .action_router import ActionRouter
from .scrapers import RSSScraper, GitHubScraper, RedditScraper, YouTubeScraper, TranscriptScraper

if TYPE_CHECKING:
    from core.model_router import ModelRouter
    from core.approval_queue import ApprovalQueue

logger = logging.getLogger(__name__)


class ResearchAgent:
    """
    Autonomous research agent that scrapes, evaluates, and acts on information.

    Daily workflow:
    1. Scrape all configured sources
    2. Deduplicate against seen items
    3. Evaluate each item against goals (using LLM)
    4. Route relevant items to actions (alert, task, content, knowledge)
    5. Store all items in database
    6. Generate and send daily digest
    """

    def __init__(self, model_router: "ModelRouter",
                 approval_queue: "ApprovalQueue",
                 telegram_bot=None,
                 memory_manager=None):
        self.router = model_router
        self.queue = approval_queue
        self.telegram = telegram_bot
        self.memory = memory_manager

        # Initialize components
        self.store = KnowledgeStore()
        self.evaluator = GoalEvaluator(model_router)
        self.action_router = ActionRouter(
            approval_queue, model_router, telegram_bot, memory_manager
        )

        # Initialize scrapers
        self.scrapers = [
            RSSScraper(),
            GitHubScraper(),
            RedditScraper(),
            YouTubeScraper(),
            TranscriptScraper(),
        ]

        logger.info("Research Agent initialized with %d scrapers", len(self.scrapers))

    async def run_daily_research(self) -> dict:
        """
        Main entry point - run full research cycle.

        Returns dict with stats:
        - scraped: Total items found
        - new: Items not seen before
        - relevant: Items matching goals
        - alerts: Alerts sent
        - tasks: Tasks created
        - content: Content drafted
        """
        start_time = datetime.now()
        logger.info("Starting daily research cycle...")

        stats = {
            "scraped": 0,
            "new": 0,
            "relevant": 0,
            "alerts": 0,
            "tasks": 0,
            "content": 0,
            "knowledge": 0,
            "errors": [],
        }

        # 1. Scrape all sources
        all_items = []
        for scraper in self.scrapers:
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
            await self._send_digest(stats, start_time)
            return stats

        # 3. Evaluate each item against goals
        evaluated = await self.evaluator.evaluate_batch(new_items)

        # 4. Filter relevant items and route actions
        relevant_items = [i for i in evaluated if i.relevance_score > 3]
        stats["relevant"] = len(relevant_items)

        if relevant_items:
            routing_stats = await self.action_router.route_batch(relevant_items)
            stats["alerts"] = routing_stats.get("alert_sent", 0)
            stats["tasks"] = routing_stats.get("task_created", 0)
            stats["content"] = routing_stats.get("content_queued", 0)
            stats["knowledge"] = routing_stats.get("knowledge_added", 0)

        # 5. Store all evaluated items
        self.store.save_batch(evaluated)

        # 6. Record digest stats
        self.store.record_digest({
            "items_scraped": stats["scraped"],
            "items_relevant": stats["relevant"],
            "alerts_sent": stats["alerts"],
            "tasks_created": stats["tasks"],
            "content_drafted": stats["content"],
        })

        # 7. Send daily digest
        await self._send_digest(stats, start_time)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Research cycle complete in {duration:.1f}s: {stats}")

        return stats

    async def _send_digest(self, stats: dict, start_time: datetime):
        """Send daily digest to operator via Telegram."""
        duration = (datetime.now() - start_time).total_seconds()

        digest = (
            f"DAILY RESEARCH DIGEST\n"
            f"{datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            f"Scraped: {stats['scraped']} items\n"
            f"New: {stats['new']} items\n"
            f"Relevant: {stats['relevant']} items\n\n"
            f"Actions taken:\n"
            f"  Alerts: {stats['alerts']}\n"
            f"  Tasks: {stats['tasks']}\n"
            f"  Content: {stats['content']}\n"
            f"  Knowledge: {stats['knowledge']}\n\n"
            f"Duration: {duration:.1f}s"
        )

        if stats["errors"]:
            digest += f"\n\nErrors ({len(stats['errors'])}):\n"
            for err in stats["errors"][:3]:  # Limit to 3 errors
                digest += f"  - {err[:50]}\n"

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

    async def close(self):
        """Clean up resources."""
        for scraper in self.scrapers:
            try:
                await scraper.close()
            except Exception as e:
                logger.warning(f"Error closing {scraper.name}: {e}")
        logger.info("Research Agent closed")

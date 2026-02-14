"""
The David Project - Agent System Entry Point

Starts all services:
1. Telegram bot (command interface + approval UI)
2. Core agent engine (tool loop)
3. Token budget initialization
4. Audit logging

Usage:
    python main.py

Requires .env file with API credentials (see .env.example).
"""

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from core.approval_queue import ApprovalQueue
from core.audit_log import AuditLog
from core.engine import AgentContext, AgentEngine
from core.kill_switch import KillSwitch
from core.model_router import ModelRouter
from core.scheduler import ContentScheduler, set_active_scheduler
from core.token_budget import TokenBudgetManager
from interfaces.telegram_bot import TelegramBot
from personality.david_flip import DavidFlipPersonality
from tools.twitter_tool import TwitterTool
from tools.tiktok_tool import TikTokTool
from tools.tool_registry import build_registry, get_project_allowed_tools
from tools.video_distributor import VideoDistributor
from agents.content_agent import ContentAgent
from agents.interview_agent import InterviewAgent
from agents.operations_agent import OperationsAgent
from agents.growth_agent import GrowthAgent
from agents.research_agent import ResearchAgent
from core.memory import MemoryManager
from personality.momentum import MomentumPersonality
from personality.oprah import OprahPersonality

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("david")


class DavidSystem:
    """Main system orchestrator. Wires all components together."""

    def __init__(self):
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)

        # Core components
        self.kill_switch = KillSwitch()
        self.approval_queue = ApprovalQueue()
        self.audit_log = AuditLog()
        self.token_budget = TokenBudgetManager()
        self.model_router = ModelRouter()
        self.personality = DavidFlipPersonality()

        # Memory system
        self.memory = MemoryManager(model_router=self.model_router)

        # Tools
        self.twitter = TwitterTool()
        self.tiktok = TikTokTool()
        self.tool_registry = build_registry(
            twitter_tool=self.twitter,
            tiktok_tool=self.tiktok,
        )

        # Agent engine
        self.engine = AgentEngine(
            model_router=self.model_router,
            tool_registry=self.tool_registry,
            approval_queue=self.approval_queue,
            token_budget=self.token_budget,
            audit_log=self.audit_log,
            kill_switch=self.kill_switch,
            allowed_tools=get_project_allowed_tools("david-flip"),
        )

        # Scheduler for recurring tasks
        self.scheduler = ContentScheduler()
        set_active_scheduler(self.scheduler)

        # Content Agent
        self.content_agent = ContentAgent(
            approval_queue=self.approval_queue,
            scheduler=self.scheduler,
            personality=self.personality,
        )

        # Video Distributor
        self.video_distributor = VideoDistributor(
            twitter_tool=self.twitter,
            tiktok_tool=self.tiktok,
        )

        # Interview Agent
        self.interview_agent = InterviewAgent(
            approval_queue=self.approval_queue,
            personality=self.personality,
            model_router=self.model_router,
        )

        # Research Agent (initialized after Telegram bot)
        self.research_agent = None

        # Telegram bot (needs research_agent, set after)
        self.telegram = TelegramBot(
            approval_queue=self.approval_queue,
            kill_switch=self.kill_switch,
            token_budget=self.token_budget,
            audit_log=self.audit_log,
            on_command=self.handle_command,
            memory_manager=self.memory,
            content_agent=self.content_agent,
            interview_agent=self.interview_agent,
            scheduler=self.scheduler,
        )

        # Wire video distributor's telegram reference (for TikTok manual mode)
        self.video_distributor._telegram = self.telegram

        # Operations Agent (Oprah) — handles post-approval pipeline
        self.oprah_personality = OprahPersonality()
        self.oprah = OperationsAgent(
            approval_queue=self.approval_queue,
            audit_log=self.audit_log,
            kill_switch=self.kill_switch,
            personality=self.oprah_personality,
            telegram_bot=self.telegram,
            scheduler=self.scheduler,
            video_distributor=self.video_distributor,
            content_agent=self.content_agent,
            memory=self.memory,
            twitter_tool=self.twitter,
            model_router=self.model_router,
            david_personality=self.personality,
        )

        # Growth Agent (Momentum) — reply targeting + analytics
        self.momentum_personality = MomentumPersonality()
        self.growth_agent = GrowthAgent(
            twitter_tool=self.twitter,
            approval_queue=self.approval_queue,
            audit_log=self.audit_log,
            personality=self.momentum_personality,
            telegram_bot=self.telegram,
            model_router=self.model_router,
            david_personality=self.personality,
            kill_switch=self.kill_switch,
        )

        # Wire alert callback (uses _loop ref set in start() for thread safety)
        self.audit_log.set_alert_callback(self._send_audit_alert)

        # Set default budgets
        self.token_budget.set_budget("master", daily=2.00, monthly=60.00)
        self.token_budget.set_budget("david-flip", daily=10.00, monthly=200.00)

    def _send_audit_alert(self, msg: str):
        """Thread-safe audit alert sender."""
        if hasattr(self, '_loop') and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self.telegram.send_alert(msg), self._loop)
        else:
            logger.warning(f"Audit alert (no event loop): {msg[:100]}")

    async def handle_command(self, command: str, args: str) -> str:
        """
        Handle commands from Telegram.
        Routes to appropriate handler or agent engine.
        """
        # Direct execution of approved actions
        if command.startswith("execute_"):
            action_type = command.replace("execute_", "")
            action_data = json.loads(args)
            return await self._execute_action(action_type, action_data)

        # Generate tweet with David's personality
        if command == "generate_tweet":
            return await self._generate_david_tweet(args)

        # Agent-generated response (user message)
        if command == "message":
            return await self._agent_respond(args)

        return f"Unknown command: {command}"

    async def _generate_david_tweet(self, topic: str) -> str:
        """Generate a tweet using David's personality."""
        context = AgentContext(
            project_id="david-flip",
            session_id="tweet-generation",
            agent_id="david-flip-twitter",
            task_type="content_generation",
        )

        # Load permanent identity rules
        from core.memory.knowledge_store import KnowledgeStore
        identity_rules = KnowledgeStore().get_identity_rules()

        system_prompt = self.personality.get_system_prompt("twitter", identity_rules=identity_rules)

        # Check if this is already a formatted prompt (from news/debasement)
        if "Write a tweet" in topic or "HEADLINE:" in topic or "DATA:" in topic:
            # Already formatted, use directly
            task = topic + "\n\nReturn ONLY the tweet text, nothing else."
        else:
            # Simple topic, add standard formatting
            task = (
                f"Write a single tweet about: {topic}\n\n"
                "Rules:\n"
                "- Maximum 280 characters\n"
                "- Stay in character as David Flip\n"
                "- Be concise, slightly aloof (Musk-style)\n"
                "- Don't use hashtags excessively (1-2 max if any)\n"
                "- Don't start with 'I' too often\n"
                "- Focus on the message, not engagement-baiting\n"
                "- Connect to giving power back to regular people\n\n"
                "Return ONLY the tweet text, nothing else."
            )

        response = await self.engine.run(
            context=context,
            task=task,
            system_prompt=system_prompt,
        )

        # Clean up any quotes or extra formatting
        tweet = response.strip().strip('"').strip("'")

        # Validate character count
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."

        return tweet

    async def _agent_respond(self, user_message: str) -> str:
        """Generate a David Flip response via the agent engine."""
        context = AgentContext(
            project_id="david-flip",
            session_id="telegram-direct",
            agent_id="david-flip-core",
            task_type="simple_qa",
        )

        # Load permanent identity rules
        from core.memory.knowledge_store import KnowledgeStore
        identity_rules = KnowledgeStore().get_identity_rules()

        system_prompt = self.personality.get_system_prompt("general", identity_rules=identity_rules)

        # Get memory context for the topic
        memory_context = self.memory.get_context(topic=user_message)
        if memory_context:
            enhanced_task = f"{user_message}\n\n[Memory Context]\n{memory_context}"
        else:
            enhanced_task = user_message

        response = await self.engine.run(
            context=context,
            task=enhanced_task,
            system_prompt=system_prompt,
        )

        # Validate personality consistency
        is_valid, reason = self.personality.validate_output(response)
        if not is_valid:
            logger.warning(f"Personality validation failed: {reason}")
            # Re-run with stronger personality enforcement
            response = await self.engine.run(
                context=context,
                task=(
                    f"Your previous response was rejected because: {reason}. "
                    f"Please respond again to: {user_message}"
                ),
                system_prompt=system_prompt,
            )

        # Remember the interaction
        self.memory.remember_interaction(user_message, response, channel="telegram")

        # Detect goals/facts in background
        asyncio.create_task(self._detect_goals(user_message))

        return response

    async def _detect_goals(self, message: str):
        """Background task to detect and store goals from conversation."""
        try:
            result = await self.memory.detect_and_store_goal(message)
            if result:
                logger.info(f"Detected {result['type']}: {result.get('title', '')}")
        except Exception as e:
            logger.debug(f"Goal detection error: {e}")

    async def _execute_action(self, action_type: str, action_data: dict) -> str:
        """Execute an approved action — delegates to Oprah."""
        return await self.oprah.execute_action(action_type, action_data)

    async def start(self):
        """Start the system."""
        logger.info("=" * 60)
        logger.info("THE DAVID PROJECT — STARTING")
        logger.info("=" * 60)

        # Check kill switch
        if self.kill_switch.is_active:
            reason = self.kill_switch.get_reason()
            logger.warning(f"Kill switch is active: {reason}")
            logger.warning("Use /revive in Telegram to restart")

        # Log startup
        self.audit_log.log(
            "master", "info", "system", "System starting",
            details=f"Kill switch: {'ACTIVE' if self.kill_switch.is_active else 'inactive'}"
        )

        # Start memory session
        self.memory.start_session()
        logger.info(f"Memory system online: {self.memory.get_summary()}")

        # Start Telegram bot
        await self.telegram.start()

        # Initialize Research Agent (needs telegram bot for alerts)
        self.research_agent = ResearchAgent(
            model_router=self.model_router,
            approval_queue=self.approval_queue,
            telegram_bot=self.telegram,
            memory_manager=self.memory,
        )
        self.telegram.research_agent = self.research_agent
        logger.info("Research Agent initialized")

        # Start content scheduler
        await self.scheduler.start()
        self.scheduler.register_executor("daily_research", self._run_daily_research)

        # Create separate in-memory scheduler for cron jobs (can't pickle methods to SQLite)
        # APScheduler runs jobs in a thread pool, so we need the loop reference
        # to schedule coroutines safely from threads.
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.date import DateTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        self._loop = asyncio.get_running_loop()
        self.cron_scheduler = AsyncIOScheduler()

        # DAILY: Full research cycle at 2am UTC (6am UAE)
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._run_daily_research(), self._loop),
            trigger=CronTrigger(hour=2, minute=0),
            id="daily_research",
        )

        # HOT tier: Every 3 hours (Twitter, HN) - breaking news
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._run_tier("hot"), self._loop),
            trigger=IntervalTrigger(hours=3),
            id="hot_research",
        )

        # WARM tier: Every 10 hours (RSS, Reddit, GitHub)
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._run_tier("warm"), self._loop),
            trigger=IntervalTrigger(hours=10),
            id="warm_research",
        )

        # DAILY TWEET PLANNER: Momo plans the day's schedule at 6:00 UTC
        # Replaces the old 6-fixed-slot system with 4-8 organically spaced tweets
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._plan_and_schedule_tweets(), self._loop),
            trigger=CronTrigger(hour=6, minute=0),
            id="daily_tweet_planner",
        )

        # Also run 30s after boot (catches restarts, first-time runs)
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._plan_and_schedule_tweets(), self._loop),
            trigger=DateTrigger(run_date=datetime.now() + timedelta(seconds=30)),
            id="tweet_planner_startup",
        )

        # DAILY VIDEO: Disabled until operator is confident in quality
        # Uncomment to enable automated daily video generation:
        # self.cron_scheduler.add_job(
        #     lambda: asyncio.run_coroutine_threadsafe(self._run_daily_video(), self._loop),
        #     trigger=CronTrigger(hour=8, minute=0),
        #     id="daily_video",
        # )

        # DASHBOARD POLLER: Check for approved content from dashboard + process feedback
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self.oprah.poll_dashboard_actions(), self._loop),
            trigger=IntervalTrigger(seconds=30),
            id="dashboard_poller",
        )

        # MOMENTUM: Mention monitor every 15 minutes
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self.growth_agent.check_mentions(), self._loop),
            trigger=IntervalTrigger(minutes=15),
            id="momentum_mentions",
        )

        # MOMENTUM: Reply target finder every 6 hours
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self.growth_agent.find_reply_targets(), self._loop),
            trigger=IntervalTrigger(hours=6),
            id="momentum_reply_targets",
        )

        # MOMENTUM: Performance tracking every 4 hours
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self.growth_agent.track_performance(), self._loop),
            trigger=IntervalTrigger(hours=4),
            id="momentum_performance",
        )

        # MOMENTUM: Daily analytics report at 7:00 UTC (11am UAE)
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self.growth_agent.generate_daily_report(), self._loop),
            trigger=CronTrigger(hour=7, minute=0),
            id="momentum_daily_report",
        )

        # Register video_distribute executor on scheduler (Oprah handles all post-approval execution)
        self.scheduler.register_executor("video_distribute", self.oprah._execute_scheduled_video)

        # Register tweet/thread/reply executors for scheduled posting
        self.scheduler.register_executor("tweet", self.oprah._execute_scheduled_tweet)
        self.scheduler.register_executor("thread", self.oprah._execute_scheduled_tweet)
        self.scheduler.register_executor("reply", self.oprah._execute_scheduled_tweet)

        # --- DAVID SCALE: Weekly scoring pipeline (Sundays) ---
        # Sunday 06:00 UTC — Run sentiment pipeline
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._run_david_scale_sentiment(), self._loop),
            trigger=CronTrigger(day_of_week="sun", hour=6, minute=0),
            id="david_scale_sentiment",
        )
        # Sunday 07:00 UTC — Calculate scores + detect ranking changes
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._run_david_scale_scoring(), self._loop),
            trigger=CronTrigger(day_of_week="sun", hour=7, minute=0),
            id="david_scale_scoring",
        )
        # Sunday 08:00 UTC — Generate auto-tweets for ranking changes
        self.cron_scheduler.add_job(
            lambda: asyncio.run_coroutine_threadsafe(self._run_david_scale_tweets(), self._loop),
            trigger=CronTrigger(day_of_week="sun", hour=8, minute=0),
            id="david_scale_tweets",
        )

        self.cron_scheduler.start()
        logger.info("Cron: Research 2:00 UTC | Tweet planner 6:00 UTC (Momo 4-8/day organic) | Hot every 3h | Warm every 10h")
        logger.info("Cron: Momentum — Mentions every 15m | Reply targets every 6h | Performance every 4h | Report 7:00 UTC")
        logger.info("Cron: David Scale — Sentiment Sun 06:00 | Scoring Sun 07:00 | Tweets Sun 08:00")

        logger.info("System online. Waiting for commands via Telegram.")
        logger.info(f"Operator chat ID: {os.environ.get('TELEGRAM_OPERATOR_CHAT_ID', 'NOT SET')}")

        # Tell systemd we're ready (for Type=notify services) + first watchdog ping
        self._notify_systemd("READY=1")
        self._notify_systemd("WATCHDOG=1")

        # Send startup notification to Telegram
        await self._send_status_notification(online=True)

        # Oprah checks: has David been silent too long? Generate content if needed.
        await self.oprah.check_content_gaps()

        # Keep running with heartbeat (updates status file every 60s for watchdog)
        try:
            heartbeat_counter = 0
            while True:
                await asyncio.sleep(1)
                heartbeat_counter += 1
                if heartbeat_counter >= 60:
                    heartbeat_counter = 0
                    await self._heartbeat()
        except asyncio.CancelledError:
            pass

    # --- David Scale methods ---

    async def _run_david_scale_sentiment(self):
        """Run the David Scale sentiment pipeline (Sunday 06:00 UTC)."""
        if self.kill_switch.is_active:
            logger.warning("Skipping David Scale sentiment - kill switch active")
            return

        try:
            from david_scale.sentiment import SentimentPipeline
            pipeline = SentimentPipeline(
                model_router=self.model_router,
                research_db_path="data/research.db",
            )
            stats = await pipeline.run(days=7)
            logger.info(f"David Scale sentiment complete: {stats}")
            self.audit_log.log(
                "david-scale", "info", "sentiment",
                f"Sentiment: {stats.get('customer_mentions', 0)} customer, "
                f"{stats.get('influencer_reviews', 0)} influencer"
            )
        except Exception as e:
            logger.error(f"David Scale sentiment failed: {e}")

    async def _run_david_scale_scoring(self):
        """Run the David Scale scoring engine (Sunday 07:00 UTC)."""
        if self.kill_switch.is_active:
            return

        try:
            from david_scale.scorer import DavidScaleScorer
            from david_scale.models import DavidScaleDB
            db = DavidScaleDB()
            scorer = DavidScaleScorer(db=db)
            results = scorer.score_all()
            self._david_scale_results = results  # Store for tweet step
            changes = scorer.detect_ranking_changes(results)
            self._david_scale_changes = changes
            logger.info(f"David Scale scoring: {len(results)} tools, {len(changes)} changes")
            self.audit_log.log(
                "david-scale", "info", "scoring",
                f"Scored {len(results)} tools, {len(changes)} ranking changes"
            )
        except Exception as e:
            logger.error(f"David Scale scoring failed: {e}")

    async def _run_david_scale_tweets(self):
        """Generate auto-tweets for David Scale ranking changes (Sunday 08:00 UTC)."""
        if self.kill_switch.is_active:
            return

        changes = getattr(self, "_david_scale_changes", [])
        if not changes:
            logger.info("David Scale: no ranking changes to tweet")
            return

        try:
            from david_scale.tweets import DavidScaleTweeter
            tweeter = DavidScaleTweeter(
                model_router=self.model_router,
                approval_queue=self.approval_queue,
            )
            tweets = await tweeter.generate_tweets(changes)
            logger.info(f"David Scale: {len(tweets)} tweets queued for approval")
            self.audit_log.log(
                "david-scale", "info", "tweets",
                f"Queued {len(tweets)} auto-tweets for ranking changes"
            )
        except Exception as e:
            logger.error(f"David Scale tweet generation failed: {e}")

    async def _run_daily_research(self, data: dict = None) -> dict:
        """Run the daily research cycle."""
        if self.kill_switch.is_active:
            logger.warning("Skipping daily research - kill switch active")
            return {"skipped": True, "reason": "kill_switch_active"}

        try:
            logger.info("Running daily research cycle...")
            result = await self.research_agent.run_daily_research()
            self.audit_log.log(
                "david-flip", "info", "research",
                f"Daily research complete: {result['new']} new, {result['relevant']} relevant"
            )
            return result
        except Exception as e:
            logger.error(f"Daily research failed: {e}")
            self.audit_log.log(
                "david-flip", "reject", "research",
                f"Daily research failed: {e}",
                success=False
            )
            return {"error": str(e)}

    async def _plan_and_schedule_tweets(self):
        """Have Momo plan today's tweet schedule, then schedule generation jobs.

        Called daily at 6:00 UTC and 30s after boot.
        For each planned slot, schedules a DateTrigger job 30 minutes before
        to generate a tweet for Jono to review.
        """
        if self.kill_switch.is_active:
            logger.info("Skipping tweet planning - kill switch active")
            return

        try:
            plan = self.growth_agent.plan_daily_schedule()
            slot_times = plan.get("slot_times", [])
            count = plan.get("planned_count", 0)

            if not slot_times:
                logger.warning("Momo returned empty schedule — no tweets planned")
                return

            # Schedule a generation job 30min before each slot
            from apscheduler.triggers.date import DateTrigger
            now = datetime.now()
            scheduled_count = 0

            for i, slot_str in enumerate(slot_times):
                slot_dt = datetime.fromisoformat(slot_str)
                # Make naive for APScheduler comparison (APScheduler uses local time)
                if slot_dt.tzinfo is not None:
                    slot_dt = slot_dt.replace(tzinfo=None)

                gen_time = slot_dt - timedelta(minutes=30)

                # Skip slots that are already past
                if gen_time < now:
                    logger.info(f"  Slot {i+1} ({slot_str}) — gen time already passed, skipping")
                    continue

                slot_label = slot_dt.strftime("%H:%M UTC")
                job_id = f"tweet_gen_{plan['schedule_date']}_{i}"

                # Remove old job if exists (idempotent re-planning)
                try:
                    self.cron_scheduler.remove_job(job_id)
                except Exception:
                    pass

                self.cron_scheduler.add_job(
                    lambda lbl=slot_label: asyncio.run_coroutine_threadsafe(
                        self._run_single_tweet(slot_label=lbl), self._loop
                    ),
                    trigger=DateTrigger(run_date=gen_time),
                    id=job_id,
                )
                scheduled_count += 1
                logger.info(f"  Slot {i+1}: generate at {gen_time.strftime('%H:%M')} → post at {slot_label}")

            logger.info(f"Momo planned {count} tweets, {scheduled_count} generation jobs scheduled")

            # Send summary to Jono via Telegram
            if self.telegram and self.telegram.app:
                try:
                    slot_list = "\n".join(
                        f"  {i+1}. {datetime.fromisoformat(s).strftime('%H:%M UTC')}"
                        for i, s in enumerate(slot_times)
                    )
                    await self.telegram.app.bot.send_message(
                        chat_id=self.telegram.operator_id,
                        text=(
                            f"MOMO'S PLAN — {count} tweets today\n\n"
                            f"{slot_list}\n\n"
                            f"Tweets will be generated 30min before each slot "
                            f"for your review."
                        ),
                    )
                except Exception:
                    pass

            self.audit_log.log(
                "david-flip", "info", "tweet_plan",
                f"Momo planned {count} tweets: {', '.join(datetime.fromisoformat(s).strftime('%H:%M') for s in slot_times)}",
            )

        except Exception as e:
            logger.error(f"Tweet planning failed: {e}")
            self.audit_log.log(
                "david-flip", "reject", "tweet_plan",
                f"Planning failed: {e}",
                success=False,
            )

    async def _run_single_tweet(self, target_hour: int = None, slot_label: str = None):
        """Generate 1 tweet for a planned slot.

        Called 30min before each of Momo's planned slots.
        Generates tweet -> sends to Jono via Telegram with Approve/Reject buttons.
        """
        if self.kill_switch.is_active:
            logger.info("Skipping tweet generation - kill switch active")
            return

        try:
            from run_daily_tweets import generate_tweets
            if not slot_label:
                slot_label = f"{target_hour}:00 UTC" if target_hour else "next slot"
            logger.info(f"Generating tweet for {slot_label}...")
            await generate_tweets(count=1)

            # Find the just-generated tweet so we can show its text in the notification
            pending = self.approval_queue.get_pending()
            tweet_text = ""
            for item in reversed(pending):
                if item["action_type"] == "tweet" and item["status"] == "pending":
                    action_data = json.loads(item["action_data"]) if isinstance(item["action_data"], str) else item["action_data"]
                    tweet_text = action_data.get("text", "")
                    break

            self.audit_log.log(
                "david-flip", "info", "tweets",
                f"Tweet generated for {slot_label} — waiting for review"
            )

            # Notify Jono via Telegram with tweet preview
            if self.telegram and self.telegram.app:
                try:
                    preview = tweet_text[:280] if tweet_text else "(no text)"
                    await self.telegram.app.bot.send_message(
                        chat_id=self.telegram.operator_id,
                        text=(
                            f"TWEET for {slot_label}:\n\n"
                            f"{preview}\n\n"
                            f"Approve: http://89.167.24.222:5000/approvals"
                        ),
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Tweet generation failed for {slot_label}: {e}")
            self.audit_log.log(
                "david-flip", "reject", "tweets",
                f"Tweet generation failed: {e}",
                success=False,
            )

    async def _run_tier(self, tier: str):
        """Run a specific research frequency tier (hot/warm)."""
        if self.kill_switch.is_active:
            logger.info(f"Skipping {tier} research - kill switch active")
            return

        if not self.research_agent:
            logger.warning(f"Skipping {tier} research - research agent not initialized")
            return

        try:
            logger.info(f"Running {tier} tier research...")
            result = await self.research_agent.run_tier(tier)
            if result.get("relevant", 0) > 0:
                self.audit_log.log(
                    "david-flip", "info", "research",
                    f"{tier.upper()} research: {result['new']} new, {result['relevant']} relevant"
                )
            logger.info(f"{tier.upper()} tier complete: {result}")
        except Exception as e:
            logger.error(f"{tier} tier research failed: {e}")

    def _run_daily_research_wrapper(self):
        """Wrapper for cron job (sync entry point)."""
        asyncio.run_coroutine_threadsafe(self._run_daily_research(), self._loop)

    async def _run_daily_video(self):
        """Generate a daily video and submit to approval queue."""
        if self.kill_switch.is_active:
            logger.info("Skipping daily video - kill switch active")
            return

        try:
            logger.info("Running daily video generation...")
            result = await self.content_agent.create_video_for_approval()
            self.audit_log.log(
                "david-flip", "info", "video",
                f"Daily video generated: {result.get('theme_title', 'unknown')} "
                f"(Pillar {result.get('pillar', '?')})"
            )
            # Notify operator
            if self.telegram and self.telegram.app:
                await self.telegram.app.bot.send_message(
                    chat_id=self.telegram.operator_id,
                    text=(
                        f"Daily video generated!\n\n"
                        f"Pillar {result.get('pillar', '?')}: {result.get('theme_title', '')}\n"
                        f"Check /queue to review."
                    ),
                )
        except Exception as e:
            logger.error(f"Daily video generation failed: {e}")

    def _run_daily_video_wrapper(self):
        """Wrapper for daily video cron job (sync entry point)."""
        asyncio.run_coroutine_threadsafe(self._run_daily_video(), self._loop)

    async def _send_status_notification(self, online: bool):
        """Send David's status to Telegram only on state CHANGES, not every restart.

        Reads the previous state from the status file. Only sends a Telegram
        message if the state actually changed (offline→online or online→offline),
        or if David has been offline for more than 5 minutes before coming back.
        This prevents notification spam when the service crash-loops.
        """
        from datetime import timezone, timedelta
        import json

        # Dubai is UTC+4
        dubai_tz = timezone(timedelta(hours=4))
        dubai_time = datetime.now(dubai_tz)
        dubai_time_str = dubai_time.strftime("%I:%M %p - %d %b %Y")

        # Read previous state to detect changes
        status_file = Path("data/david_status.json")
        previous_online = None
        previous_timestamp = None
        try:
            if status_file.exists():
                with open(status_file, "r") as f:
                    prev = json.load(f)
                previous_online = prev.get("online")
                previous_timestamp = prev.get("timestamp_utc")
        except Exception:
            pass

        # Update status file for dashboard (always update)
        status_data = {
            "online": online,
            "timestamp_utc": datetime.utcnow().isoformat(),
            "timestamp_dubai": dubai_time_str,
            "status": "awake" if online else "offline"
        }
        try:
            with open(status_file, "w") as f:
                json.dump(status_data, f)
        except Exception as e:
            logger.warning(f"Could not write status file: {e}")

        # Decide whether to send Telegram notification
        should_notify = False
        if previous_online is None:
            # First ever boot — always notify
            should_notify = True
        elif online and not previous_online:
            # Was offline, now online — notify (recovery)
            should_notify = True
        elif not online:
            # Going offline — always notify
            should_notify = True
        elif online and previous_online and previous_timestamp:
            # Was online, still online (restart). Only notify if gap > 5 minutes
            try:
                prev_time = datetime.fromisoformat(previous_timestamp)
                gap = (datetime.utcnow() - prev_time).total_seconds()
                if gap > 300:
                    should_notify = True
                else:
                    logger.info(f"Suppressing AWAKE notification (restart within {gap:.0f}s)")
            except Exception:
                should_notify = True

        if not should_notify:
            return

        if online:
            message = f"🟢 DAVID IS AWAKE\n\n{dubai_time_str} (Dubai)"
        else:
            message = f"🔴 DAVID IS OFFLINE\n\n{dubai_time_str} (Dubai)"

        try:
            if self.telegram and self.telegram.app:
                await self.telegram.app.bot.send_message(
                    chat_id=self.telegram.operator_id,
                    text=message
                )
        except Exception as e:
            logger.warning(f"Could not send status notification: {e}")

    async def _heartbeat(self):
        """Update status file every 60s and notify systemd watchdog."""
        from datetime import timezone, timedelta as td
        status_file = Path("data/david_status.json")
        dubai_tz = timezone(td(hours=4))
        dubai_time = datetime.now(dubai_tz)
        status_data = {
            "online": True,
            "timestamp_utc": datetime.utcnow().isoformat(),
            "timestamp_dubai": dubai_time.strftime("%I:%M %p - %d %b %Y"),
            "status": "awake",
        }
        try:
            with open(status_file, "w") as f:
                json.dump(status_data, f)
        except Exception:
            pass

        # Notify systemd watchdog (prevents WatchdogSec from killing us)
        self._notify_systemd("WATCHDOG=1")

    @staticmethod
    def _notify_systemd(message: str):
        """Send a notification to systemd via NOTIFY_SOCKET (no extra packages needed)."""
        import socket
        notify_socket = os.environ.get("NOTIFY_SOCKET")
        if not notify_socket:
            return
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            if notify_socket.startswith("@"):
                notify_socket = "\0" + notify_socket[1:]
            sock.connect(notify_socket)
            sock.sendall(message.encode())
            sock.close()
        except Exception:
            pass

    async def stop(self):
        """Graceful shutdown."""
        logger.info("System shutting down...")
        self.audit_log.log("master", "info", "system", "System shutdown")

        # Send shutdown notification to Telegram (before stopping telegram)
        await self._send_status_notification(online=False)

        # Stop research agent
        if self.research_agent:
            await self.research_agent.close()

        # Stop cron scheduler
        if hasattr(self, 'cron_scheduler'):
            self.cron_scheduler.shutdown(wait=False)

        # Stop content scheduler
        await self.scheduler.stop()

        # Stop telegram
        await self.telegram.stop()
        logger.info("System stopped.")


async def main():
    system = DavidSystem()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def signal_handler():
        logger.info("Shutdown signal received")
        asyncio.create_task(system.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    try:
        await system.start()
    except KeyboardInterrupt:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())

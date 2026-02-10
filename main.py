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
from core.scheduler import ContentScheduler
from core.token_budget import TokenBudgetManager
from interfaces.telegram_bot import TelegramBot
from personality.david_flip import DavidFlipPersonality
from tools.twitter_tool import TwitterTool
from tools.tiktok_tool import TikTokTool
from tools.tool_registry import build_registry, get_project_allowed_tools
from tools.video_distributor import VideoDistributor
from agents.content_agent import ContentAgent
from agents.interview_agent import InterviewAgent
from agents.research_agent import ResearchAgent
from core.memory import MemoryManager

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

        # Wire alert callback
        self.audit_log.set_alert_callback(
            lambda msg: asyncio.create_task(self.telegram.send_alert(msg))
        )

        # Set default budgets
        self.token_budget.set_budget("master", daily=2.00, monthly=60.00)
        self.token_budget.set_budget("david-flip", daily=10.00, monthly=200.00)

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

        system_prompt = self.personality.get_system_prompt("twitter")

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

        system_prompt = self.personality.get_system_prompt("general")

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
        """Execute an approved action through the appropriate tool."""
        try:
            if action_type in ("tweet", "thread", "reply"):
                # Ensure action type is in the data for the Twitter tool
                action_data["action"] = action_type
                result = await self.twitter.execute(action_data)
                if "error" in result:
                    return f"Twitter error: {result['error']}"
                url = result.get("url", "")

                # Remember the tweet
                tweet_text = action_data.get("text", "")
                self.memory.remember_tweet(tweet_text, context=url, posted=True)

                return f"Posted: {url}"

            elif action_type == "video_distribute":
                # Multi-platform video distribution
                platforms = action_data.get("platforms", ["twitter", "youtube", "tiktok"])
                result = await self.video_distributor.distribute(
                    video_path=action_data.get("video_path", ""),
                    script=action_data.get("script", ""),
                    platforms=platforms,
                    title=action_data.get("theme_title", "David Flip"),
                    description="flipt.ai",
                    theme_title=action_data.get("theme_title", ""),
                )

                distributed = result.get("distributed", [])
                failed = result.get("failed", [])
                parts = []
                if distributed:
                    parts.append(f"Posted to: {', '.join(distributed)}")
                    for p, r in result.get("results", {}).items():
                        url = r.get("url", "")
                        if url:
                            parts.append(f"  {p}: {url}")
                if failed:
                    parts.append(f"Failed: {', '.join(failed)}")
                    for p, e in result.get("errors", {}).items():
                        parts.append(f"  {p}: {e}")

                return "\n".join(parts) if parts else "Distribution complete"

            else:
                return f"No executor for action type: {action_type}"
        except Exception as e:
            self.audit_log.log(
                "david-flip", "reject", "execution",
                f"Failed: {action_type}", details=str(e), success=False
            )
            return f"Execution failed: {e}"

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
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        self.cron_scheduler = AsyncIOScheduler()

        # DAILY: Full research cycle at 2am UTC (6am UAE)
        self.cron_scheduler.add_job(
            self._run_daily_research_wrapper,
            trigger=CronTrigger(hour=2, minute=0),
            id="daily_research",
        )

        # HOT tier: Every 3 hours (Twitter, HN) - breaking news
        self.cron_scheduler.add_job(
            lambda: asyncio.create_task(self._run_tier("hot")),
            trigger=IntervalTrigger(hours=3),
            id="hot_research",
        )

        # WARM tier: Every 10 hours (RSS, Reddit, GitHub)
        self.cron_scheduler.add_job(
            lambda: asyncio.create_task(self._run_tier("warm")),
            trigger=IntervalTrigger(hours=10),
            id="warm_research",
        )

        # DAILY VIDEO: Disabled until operator is confident in quality
        # Uncomment to enable automated daily video generation:
        # self.cron_scheduler.add_job(
        #     self._run_daily_video_wrapper,
        #     trigger=CronTrigger(hour=8, minute=0),
        #     id="daily_video",
        # )

        # DASHBOARD POLLER: Check for approved content from dashboard + process feedback
        self.cron_scheduler.add_job(
            lambda: asyncio.create_task(self._poll_dashboard_actions()),
            trigger=IntervalTrigger(seconds=30),
            id="dashboard_poller",
        )

        # Register video_distribute executor on scheduler
        self.scheduler.register_executor("video_distribute", self._execute_scheduled_video)

        self.cron_scheduler.start()
        logger.info("Research scheduled: Daily 2:00 UTC | Hot every 3h | Warm every 10h")

        logger.info("System online. Waiting for commands via Telegram.")
        logger.info(f"Operator chat ID: {os.environ.get('TELEGRAM_OPERATOR_CHAT_ID', 'NOT SET')}")

        # Send startup notification to Telegram
        await self._send_status_notification(online=True)

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

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
        asyncio.create_task(self._run_daily_research())

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
        asyncio.create_task(self._run_daily_video())

    async def _poll_dashboard_actions(self):
        """
        Poll for actions from the dashboard:
        1. Schedule requests (approved content to be distributed)
        2. Rejection feedback (goes into David's memory)

        This bridges the dashboard UI with the execution pipeline.
        """
        feedback_dir = Path("data/content_feedback")
        if not feedback_dir.exists():
            return

        for file_path in sorted(feedback_dir.glob("*.json")):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)

                if file_path.name.startswith("schedule_"):
                    await self._handle_schedule_request(data)
                elif file_path.name.startswith("render_"):
                    await self._handle_render_request(data)
                elif file_path.name.startswith("feedback_"):
                    await self._handle_content_feedback(data)
                elif file_path.name.startswith("execute_"):
                    await self._handle_execute_request(data)

                # Remove processed file
                file_path.unlink()

            except Exception as e:
                logger.error(f"Failed to process dashboard action {file_path.name}: {e}")

    async def _handle_schedule_request(self, data: dict):
        """Schedule approved content for distribution at optimal time."""
        from datetime import datetime as dt

        approval_id = data.get("approval_id")
        action_data = data.get("action_data", {})
        platforms = data.get("platforms", ["twitter", "youtube", "tiktok"])
        scheduled_time_str = data.get("scheduled_time", "")

        if not scheduled_time_str:
            logger.error(f"No scheduled_time in schedule request for #{approval_id}")
            return

        scheduled_time = dt.fromisoformat(scheduled_time_str)
        action_data["platforms"] = platforms

        # Schedule via ContentScheduler
        job_id = self.scheduler.schedule(
            content_type="video_distribute",
            content_data=action_data,
            scheduled_time=scheduled_time,
        )

        # Mark as executed in approval queue (it's now scheduled)
        self.approval_queue.mark_executed(approval_id)

        logger.info(
            f"Dashboard: Scheduled #{approval_id} for {scheduled_time.strftime('%I:%M %p')} "
            f"to {', '.join(platforms)} (job: {job_id})"
        )

        # Notify operator via Telegram
        if self.telegram and self.telegram.app:
            try:
                theme = action_data.get("theme_title", "")
                await self.telegram.app.bot.send_message(
                    chat_id=self.telegram.operator_id,
                    text=(
                        f"Content #{approval_id} approved via dashboard\n"
                        f"{'Theme: ' + theme + chr(10) if theme else ''}"
                        f"Scheduled: {scheduled_time.strftime('%b %d, %I:%M %p')}\n"
                        f"Platforms: {', '.join(platforms)}"
                    ),
                )
            except Exception:
                pass

    async def _handle_render_request(self, data: dict):
        """Render video for an approved script (Stage 1 -> Stage 2 transition)."""
        approval_id = data.get("approval_id")
        script = data.get("script", "")
        pillar = data.get("pillar", 1)
        theme_title = data.get("theme_title", "")
        category = data.get("category", "")

        if not script:
            logger.error(f"No script in render request for #{approval_id}")
            return

        logger.info(f"Rendering video for approved script #{approval_id}...")

        # Notify operator that rendering has started
        if self.telegram and self.telegram.app:
            try:
                await self.telegram.app.bot.send_message(
                    chat_id=self.telegram.operator_id,
                    text=(
                        f"Rendering video for script #{approval_id}...\n"
                        f"{'Theme: ' + theme_title + chr(10) if theme_title else ''}"
                        f"This takes ~2 minutes."
                    ),
                )
            except Exception:
                pass

        try:
            # Render video and submit as Stage 2 (video_distribute) approval
            result = await self.content_agent.create_video_for_approval(
                script=script,
                pillar=pillar,
                mood=data.get("mood"),
                theme_title=data.get("theme_title"),
                category=data.get("category"),
            )

            logger.info(
                f"Video rendered for script #{approval_id}: "
                f"{result.get('video_path', 'unknown')} "
                f"(new approval #{result.get('approval_id', '?')})"
            )

            # Notify operator that video is ready for review
            if self.telegram and self.telegram.app:
                try:
                    await self.telegram.app.bot.send_message(
                        chat_id=self.telegram.operator_id,
                        text=(
                            f"Video rendered! Check dashboard to review.\n\n"
                            f"{'Theme: ' + theme_title + chr(10) if theme_title else ''}"
                            f"Approval #{result.get('approval_id', '?')}"
                        ),
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Video render failed for script #{approval_id}: {e}")
            self.audit_log.log(
                "david-flip", "reject", "video_render",
                f"Render failed for script #{approval_id}: {e}",
                success=False,
            )
            # Notify operator of failure
            if self.telegram and self.telegram.app:
                try:
                    await self.telegram.app.bot.send_message(
                        chat_id=self.telegram.operator_id,
                        text=f"Video render FAILED for script #{approval_id}: {e}",
                    )
                except Exception:
                    pass

    async def _handle_content_feedback(self, data: dict):
        """Save content rejection feedback into David's memory."""
        reason = data.get("reason", "")
        context = data.get("content_context", {})
        approval_id = data.get("approval_id", "")

        if not reason:
            return

        # Save to David's memory as a significant event
        summary = (
            f"Content rejected by operator. "
            f"Theme: {context.get('theme_title', 'unknown')}. "
            f"Category: {context.get('category', 'unknown')}. "
            f"Feedback: {reason}"
        )

        self.memory.remember_event(
            title=f"Content feedback: {context.get('theme_title', 'rejected')}",
            summary=summary,
            significance=7,  # High significance — operator feedback matters
            category="content_feedback",
        )

        logger.info(f"Saved content feedback for #{approval_id}: {reason[:100]}")

        # Also log to audit
        self.audit_log.log(
            "david-flip", "info", "content_feedback",
            f"Rejection feedback #{approval_id}: {reason[:200]}",
        )

    async def _handle_execute_request(self, data: dict):
        """Execute an approved action from the dashboard (tweets, threads, replies, etc.)."""
        approval_id = data.get("approval_id")
        action_type = data.get("action_type", "")
        action_data = data.get("action_data", {})

        try:
            result = await self._execute_action(action_type, action_data)

            # Mark as executed in approval queue
            self.approval_queue.mark_executed(approval_id)

            logger.info(f"Dashboard: Executed {action_type} #{approval_id}: {result[:200]}")

            # Notify operator via Telegram
            if self.telegram and self.telegram.app:
                try:
                    await self.telegram.app.bot.send_message(
                        chat_id=self.telegram.operator_id,
                        text=f"Dashboard approved {action_type} #{approval_id}\n{result}",
                    )
                except Exception:
                    pass

        except Exception as e:
            logger.error(f"Dashboard execute failed for #{approval_id}: {e}")
            self.audit_log.log(
                "david-flip", "reject", "dashboard_execute",
                f"Failed {action_type} #{approval_id}: {e}",
                success=False,
            )

    async def _execute_scheduled_video(self, content_data: dict) -> dict:
        """Execute a scheduled video distribution (called by ContentScheduler)."""
        platforms = content_data.get("platforms", ["twitter", "youtube", "tiktok"])

        result = await self.video_distributor.distribute(
            video_path=content_data.get("video_path", ""),
            script=content_data.get("script", ""),
            platforms=platforms,
            title=content_data.get("theme_title", "David Flip"),
            description="flipt.ai",
            theme_title=content_data.get("theme_title", ""),
        )

        # Notify operator of result
        if self.telegram and self.telegram.app:
            distributed = result.get("distributed", [])
            failed = result.get("failed", [])
            parts = []
            if distributed:
                parts.append(f"Posted to: {', '.join(distributed)}")
                for p, r in result.get("results", {}).items():
                    url = r.get("url", "")
                    if url:
                        parts.append(f"  {p}: {url}")
            if failed:
                parts.append(f"Failed: {', '.join(failed)}")

            try:
                await self.telegram.app.bot.send_message(
                    chat_id=self.telegram.operator_id,
                    text="Scheduled post complete!\n\n" + "\n".join(parts),
                )
            except Exception:
                pass

        return result

    async def _send_status_notification(self, online: bool):
        """Send David's status to Telegram with Dubai time and update status file."""
        from datetime import timezone, timedelta
        import json

        # Dubai is UTC+4
        dubai_tz = timezone(timedelta(hours=4))
        dubai_time = datetime.now(dubai_tz)
        dubai_time_str = dubai_time.strftime("%I:%M %p - %d %b %Y")

        # Update status file for dashboard
        status_file = Path("data/david_status.json")
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

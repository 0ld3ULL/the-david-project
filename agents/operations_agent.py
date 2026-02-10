"""
Operations Agent (Oprah) — Post-approval pipeline handler.

Owns the entire post-approval pipeline:
- Polling for approved content (dashboard action files)
- Scheduling posts via ContentScheduler
- Triggering video renders via ContentAgent
- Executing distributions via VideoDistributor
- Handling failures and routing feedback
- Reporting results via Telegram notifications

Design: Oprah doesn't run her own event loop. main.py's cron scheduler
calls poll_dashboard_actions() every 30 seconds. Oprah is the handler,
not the scheduler.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from agents.checkin_log import CheckinLog

logger = logging.getLogger(__name__)

# Directory where dashboard writes action files for polling
DASHBOARD_ACTIONS_DIR = Path("data/content_feedback")


class OperationsAgent:
    """
    Operations agent that handles the post-approval pipeline.
    Invoked by main.py's cron scheduler — does not run its own timer.
    """

    def __init__(
        self,
        approval_queue,       # ApprovalQueue — poll for approved items
        audit_log,            # AuditLog — log every action
        kill_switch,          # KillSwitch — safety gate
        personality,          # OprahPersonality — voice for notifications
        telegram_bot,         # TelegramBot — send notifications
        scheduler=None,       # ContentScheduler — schedule timed posts
        video_distributor=None,  # VideoDistributor — multi-platform distribution
        content_agent=None,   # ContentAgent — for render requests
        memory=None,          # MemoryManager — store rejection feedback
        twitter_tool=None,    # TwitterTool — for tweet execution
    ):
        self.approval_queue = approval_queue
        self.audit_log = audit_log
        self.kill_switch = kill_switch
        self.personality = personality
        self.telegram = telegram_bot
        self.scheduler = scheduler
        self.video_distributor = video_distributor
        self.content_agent = content_agent
        self.memory = memory
        self.twitter = twitter_tool

        # Ensure action directory exists
        DASHBOARD_ACTIONS_DIR.mkdir(parents=True, exist_ok=True)

        # Anti-repetition log — prevents duplicate notifications
        self.checkin_log = CheckinLog()

        logger.info(
            f"{self.personality.name} ({self.personality.role}) initialized"
        )

    def start(self):
        """No-op — main.py's cron scheduler drives polling."""
        pass

    async def stop(self):
        """Cleanup on shutdown."""
        logger.info(f"{self.personality.name} stopping")

    # ------------------------------------------------------------------
    # Pipeline polling — called by main.py cron every 30s
    # ------------------------------------------------------------------

    async def poll_dashboard_actions(self):
        """
        Poll for dashboard action files (schedule, render, execute, feedback).
        Routes by filename prefix to match what the dashboard writes:
          schedule_{id}_{ts}.json  -> _handle_schedule_request()
          render_{id}_{ts}.json    -> _handle_render_request()
          feedback_{id}_{ts}.json  -> _handle_content_feedback()
          execute_{id}_{ts}.json   -> _handle_execute_request()
        """
        if self.kill_switch.is_active:
            return

        action_dir = DASHBOARD_ACTIONS_DIR
        if not action_dir.exists():
            return

        for action_file in sorted(action_dir.glob("*.json")):
            try:
                data = json.loads(action_file.read_text(encoding="utf-8"))

                if action_file.name.startswith("schedule_"):
                    await self._handle_schedule_request(data)
                elif action_file.name.startswith("render_"):
                    await self._handle_render_request(data)
                elif action_file.name.startswith("feedback_"):
                    await self._handle_content_feedback(data)
                elif action_file.name.startswith("execute_"):
                    await self._handle_execute_request(data)
                else:
                    logger.warning(f"Unknown action file: {action_file.name}")

                # Remove processed file
                action_file.unlink()

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {action_file.name}: {e}")
                action_file.unlink()
            except Exception as e:
                logger.error(f"Error processing {action_file.name}: {e}")
                self.audit_log.log(
                    "operations", "reject", "poll",
                    f"Failed to process {action_file.name}",
                    details=str(e), success=False,
                )

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------

    async def _handle_schedule_request(self, data: dict):
        """Schedule approved content for distribution at optimal time."""
        approval_id = data.get("approval_id")
        action_data = data.get("action_data", {})
        platforms = data.get("platforms", ["twitter", "youtube", "tiktok"])
        scheduled_time_str = data.get("scheduled_time", "")

        if not scheduled_time_str:
            logger.error(f"No scheduled_time in schedule request for #{approval_id}")
            return

        scheduled_time = datetime.fromisoformat(scheduled_time_str)
        action_data["platforms"] = platforms

        # Determine content_type from the data (tweets, threads, replies, or video)
        content_type = data.get("content_type", data.get("action_type", "video_distribute"))

        # Ensure tweet executor knows the action type
        if content_type in ("tweet", "thread", "reply"):
            action_data["action"] = content_type
            action_data["approval_id"] = approval_id

        # Schedule via ContentScheduler
        job_id = self.scheduler.schedule(
            content_type=content_type,
            content_data=action_data,
            scheduled_time=scheduled_time,
        )

        # Mark as executed in approval queue (it's now scheduled)
        self.approval_queue.mark_executed(approval_id)

        logger.info(
            f"Dashboard: Scheduled {content_type} #{approval_id} for "
            f"{scheduled_time.strftime('%I:%M %p')} (job: {job_id})"
        )

        text_preview = action_data.get("text", action_data.get("theme_title", ""))[:100]
        await self._notify(
            f"{content_type.title()} #{approval_id} scheduled via dashboard\n"
            f"{text_preview}\n"
            f"Posting at: {scheduled_time.strftime('%b %d, %I:%M %p UTC')}",
            topic="schedule",
            action_type="scheduled",
            result=f"Scheduled {content_type} #{approval_id}",
        )

        self.audit_log.log(
            "operations", "info", "schedule",
            f"Scheduled {content_type} #{approval_id}",
            details=f"time={scheduled_time_str}, platforms={platforms}",
        )

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

        await self._notify(
            f"Rendering video for script #{approval_id}...\n"
            f"{'Theme: ' + theme_title + chr(10) if theme_title else ''}"
            f"This takes ~2 minutes.",
            topic="render",
            action_type="render",
            result="Rendering started",
        )

        try:
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

            await self._notify(
                f"Video rendered! Check dashboard to review.\n\n"
                f"{'Theme: ' + theme_title + chr(10) if theme_title else ''}"
                f"Approval #{result.get('approval_id', '?')}",
                topic="render",
                action_type="rendered",
                result=f"Video rendered #{approval_id}",
            )

            self.audit_log.log(
                "operations", "info", "render",
                f"Render complete #{approval_id}",
                details=json.dumps(result) if isinstance(result, dict) else str(result),
            )

        except Exception as e:
            logger.error(f"Video render failed for script #{approval_id}: {e}")
            await self._notify(
                f"Video render FAILED for script #{approval_id}: {e}",
                topic="render",
                action_type="failed",
                result=str(e),
            )
            self.audit_log.log(
                "operations", "reject", "video_render",
                f"Render failed for script #{approval_id}: {e}",
                success=False,
            )

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

        if self.memory:
            try:
                self.memory.remember_event(
                    title=f"Content feedback: {context.get('theme_title', 'rejected')}",
                    summary=summary,
                    significance=7,  # High significance — operator feedback matters
                    category="content_feedback",
                )
            except Exception as e:
                logger.error(f"Failed to store feedback: {e}")

        logger.info(f"Saved content feedback for #{approval_id}: {reason[:100]}")

        await self._notify(
            f"Feedback recorded for #{approval_id}: {reason[:100]}",
            topic="feedback",
            action_type="rejected",
            result=f"Feedback #{approval_id}",
        )

        self.audit_log.log(
            "operations", "info", "content_feedback",
            f"Rejection feedback #{approval_id}: {reason[:200]}",
        )

    async def _handle_execute_request(self, data: dict):
        """Execute an approved action from the dashboard (tweets, threads, replies, etc.)."""
        approval_id = data.get("approval_id")
        action_type = data.get("action_type", "")
        action_data = data.get("action_data", {})

        try:
            result = await self.execute_action(action_type, action_data)

            # Mark as executed in approval queue
            self.approval_queue.mark_executed(approval_id)

            logger.info(f"Dashboard: Executed {action_type} #{approval_id}: {result[:200]}")

            await self._notify(
                f"Dashboard approved {action_type} #{approval_id}\n{result}",
                topic="execute",
                action_type="executed",
                result=result,
            )

        except Exception as e:
            logger.error(f"Dashboard execute failed for #{approval_id}: {e}")
            await self._notify(
                f"Execute FAILED for {action_type} #{approval_id}: {e}",
                topic="execute",
                action_type="failed",
                result=str(e),
            )
            self.audit_log.log(
                "operations", "reject", "dashboard_execute",
                f"Failed {action_type} #{approval_id}: {e}",
                success=False,
            )

    # ------------------------------------------------------------------
    # Scheduled execution (registered with ContentScheduler)
    # ------------------------------------------------------------------

    async def _execute_scheduled_video(self, content_data: dict) -> dict:
        """Execute a scheduled video distribution (called by ContentScheduler)."""
        platforms = content_data.get("platforms", ["twitter", "youtube", "tiktok"])

        try:
            result = await self.video_distributor.distribute(
                video_path=content_data.get("video_path", ""),
                script=content_data.get("script", ""),
                platforms=platforms,
                title=content_data.get("theme_title", "David Flip"),
                description="flipt.ai",
                theme_title=content_data.get("theme_title", ""),
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

            result_text = "\n".join(parts) if parts else "Distribution complete"

            await self._notify(
                f"Scheduled post complete!\n\n{result_text}",
                topic="distribute",
                action_type="executed",
                result=result_text,
            )

            self.audit_log.log(
                "operations", "info", "distribute",
                f"Video distributed",
                details=result_text,
            )

            return result

        except Exception as e:
            await self._notify(
                f"Scheduled video distribution FAILED: {e}",
                topic="distribute",
                action_type="failed",
                result=str(e),
            )
            self.audit_log.log(
                "operations", "reject", "distribute",
                f"Distribution failed",
                details=str(e), success=False,
            )
            return {"error": str(e)}

    async def _execute_scheduled_tweet(self, content_data: dict) -> dict:
        """Execute a scheduled tweet (called by ContentScheduler at the scheduled time)."""
        action_type = content_data.get("action", "tweet")
        content_data["action"] = action_type

        result = await self.twitter.execute(content_data)

        if "error" in result:
            logger.error(f"Scheduled tweet failed: {result['error']}")
            await self._notify(
                f"Scheduled tweet FAILED: {result['error']}\n"
                f"Text: {content_data.get('text', '')[:100]}",
                topic="tweet",
                action_type="failed",
                result=result["error"],
            )
            return result

        url = result.get("url", "")

        # Remember the tweet in David's memory
        if self.memory:
            self.memory.remember_tweet(
                content_data.get("text", ""), context=url, posted=True
            )

        # Mark as executed in approval queue
        approval_id = content_data.get("approval_id")
        if approval_id:
            self.approval_queue.mark_executed(approval_id)

        await self._notify(
            f"Scheduled tweet posted!\n"
            f"{content_data.get('text', '')[:200]}\n{url}",
            topic="tweet",
            action_type="executed",
            result=url,
        )

        logger.info(f"Scheduled tweet posted: {url}")
        return result

    # ------------------------------------------------------------------
    # Direct action execution (called from _handle_execute_request)
    # ------------------------------------------------------------------

    async def execute_action(self, action_type: str, action_data: dict) -> str:
        """Execute an approved action through the appropriate tool."""
        try:
            if action_type in ("tweet", "thread", "reply"):
                if not self.twitter:
                    return "Twitter tool not configured"
                action_data["action"] = action_type
                result = await self.twitter.execute(action_data)
                if "error" in result:
                    return f"Twitter error: {result['error']}"
                url = result.get("url", "")

                # Remember the tweet
                if self.memory:
                    tweet_text = action_data.get("text", "")
                    self.memory.remember_tweet(tweet_text, context=url, posted=True)

                return f"Posted: {url}"

            elif action_type == "video_distribute":
                if not self.video_distributor:
                    return "Video distributor not configured"
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

                return "\n".join(parts) if parts else "Distribution complete"

            else:
                return f"No executor for action type: {action_type}"

        except Exception as e:
            self.audit_log.log(
                "operations", "reject", "execution",
                f"Failed: {action_type}",
                details=str(e), success=False,
            )
            return f"Execution failed: {e}"

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    def get_pipeline_status(self) -> dict:
        """
        Return pipeline status for /status command.
        Counts pending, scheduled, and upcoming items.
        """
        pending = self.approval_queue.get_pending()
        approved_unexecuted = self.approval_queue.get_approved_unexecuted()

        status = {
            "pending_approvals": len(pending),
            "approved_awaiting_execution": len(approved_unexecuted),
            "scheduled_jobs": 0,
        }

        if self.scheduler:
            try:
                scheduled = self.scheduler.get_upcoming()
                status["scheduled_jobs"] = len(scheduled) if scheduled else 0
            except Exception:
                pass

        return status

    # ------------------------------------------------------------------
    # Content gap management — Oprah keeps David posting
    # ------------------------------------------------------------------

    # Max hours of silence before Oprah triggers content generation
    TWEET_GAP_HOURS = 12
    # How many filler tweets to generate when filling a gap
    FILLER_COUNT = 5

    async def check_content_gaps(self):
        """
        Check when David last posted. If it's been too long, generate
        content and ping Jono to approve.

        Called on startup and can be called periodically.
        """
        if self.kill_switch.is_active:
            return

        # Check last executed tweet
        last_tweet = self.approval_queue.get_last_executed("tweet")
        hours_since_tweet = self._hours_since(last_tweet)

        # Check if there are already pending tweets waiting for approval
        pending = self.approval_queue.get_pending()
        pending_tweets = [p for p in pending if p["action_type"] == "tweet"]

        if pending_tweets:
            logger.info(
                f"Content check: {len(pending_tweets)} tweets already pending approval"
            )
            # Ping Jono to review if they've been sitting there
            await self._notify(
                f"{len(pending_tweets)} tweets waiting for your review!\n\n"
                f"Open Mission Control to approve:\n"
                f"http://89.167.24.222:5000/approvals",
                topic="content_gap",
                action_type="reminder",
                result="pending_tweets",
            )
            return

        if hours_since_tweet is not None and hours_since_tweet < self.TWEET_GAP_HOURS:
            logger.info(
                f"Content check: Last tweet {hours_since_tweet:.1f}h ago — OK"
            )
            return

        # Gap detected — generate content
        gap_msg = (
            f"No tweets posted in {hours_since_tweet:.0f}h"
            if hours_since_tweet is not None
            else "No tweets posted yet"
        )
        logger.info(f"Content gap detected: {gap_msg}. Generating {self.FILLER_COUNT} tweets...")

        try:
            from run_daily_tweets import generate_tweets
            await generate_tweets(count=self.FILLER_COUNT)

            await self._notify(
                f"{gap_msg}.\n\n"
                f"Generated {self.FILLER_COUNT} tweets for review.\n"
                f"Open Mission Control to approve:\n"
                f"http://89.167.24.222:5000/approvals",
                topic="content_gap",
                action_type="content_generated",
                result=f"Generated {self.FILLER_COUNT} tweets",
            )

            self.audit_log.log(
                "operations", "info", "content_gap",
                f"{gap_msg} — generated {self.FILLER_COUNT} tweets",
            )

        except Exception as e:
            logger.error(f"Failed to generate gap-fill tweets: {e}")
            await self._notify(
                f"Tried to generate tweets but failed: {e}",
                topic="content_gap",
                action_type="failed",
                result=str(e),
            )

    def _hours_since(self, approval_record: dict | None) -> float | None:
        """Calculate hours since an approval record's executed_at time."""
        if not approval_record or not approval_record.get("executed_at"):
            return None
        try:
            executed_at = datetime.fromisoformat(approval_record["executed_at"])
            delta = datetime.now() - executed_at
            return delta.total_seconds() / 3600
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _notify(
        self,
        message: str,
        topic: str = "general",
        action_type: str = "",
        result: str = "",
    ):
        """
        Send a notification via Telegram with dedup and urgency filtering.

        1. Skip if this exact message was sent recently (checkin log).
        2. Classify urgency — skip silent progress messages.
        3. Add urgent prefix when warranted.
        4. Send via Telegram and record in checkin log.
        """
        # --- Dedup check (Feature 1) ---
        if self.checkin_log.has_recently_sent_message(message):
            logger.debug(f"Skipping duplicate notification: {message[:80]}")
            return

        # --- Urgency classification (Feature 2) ---
        urgency = self.personality.classify_urgency(action_type, result or message)
        if urgency == "skip":
            logger.debug(f"Skipping low-urgency notification: {message[:80]}")
            return

        if urgency == "urgent":
            message = self.personality.format_urgent(message)

        # --- Send ---
        if self.telegram:
            try:
                await self.telegram.send_report(message)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
                return  # don't log if send failed

        # --- Record in checkin log ---
        self.checkin_log.log_notification(
            topic=topic,
            message_summary=message,
            action_type=action_type,
        )

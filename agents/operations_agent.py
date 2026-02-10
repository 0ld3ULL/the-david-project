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
from datetime import datetime
from pathlib import Path

from agents.checkin_log import CheckinLog

logger = logging.getLogger(__name__)

# Directory where dashboard writes action files for polling
DASHBOARD_ACTIONS_DIR = Path("data/dashboard_actions")


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
        Each action type is a JSON file written by the dashboard when the
        operator clicks approve/schedule/render.
        """
        if self.kill_switch.is_active:
            return

        action_dir = DASHBOARD_ACTIONS_DIR
        if not action_dir.exists():
            return

        for action_file in sorted(action_dir.glob("*.json")):
            try:
                data = json.loads(action_file.read_text(encoding="utf-8"))
                action_type = data.get("action_type", "")

                if action_type == "schedule":
                    await self._handle_schedule_request(data)
                elif action_type == "render":
                    await self._handle_render_request(data)
                elif action_type == "execute":
                    await self._handle_execute_request(data)
                elif action_type == "feedback":
                    await self._handle_content_feedback(data)
                else:
                    logger.warning(f"Unknown action type: {action_type} in {action_file.name}")

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
        """Handle a schedule request from the dashboard."""
        approval_id = data.get("approval_id", "?")
        content_type = data.get("content_type", "content")
        scheduled_time = data.get("scheduled_time", "")
        platforms = data.get("platforms", [])
        job_data = data.get("job_data", {})

        try:
            if self.scheduler:
                job_id = self.scheduler.schedule(
                    action_type="video_distribute",
                    scheduled_time=scheduled_time,
                    data=job_data,
                )
            else:
                job_id = f"pending_{approval_id}"
                logger.warning("No scheduler configured — schedule request logged only")

            notification = self.personality.format_schedule_notification(
                content_type=content_type,
                job_id=str(job_id),
                scheduled_time=scheduled_time,
            )
            if platforms:
                notification += f" -> {', '.join(platforms)}"

            await self._notify(
                notification,
                topic="schedule",
                action_type="scheduled",
                result=notification,
            )

            self.audit_log.log(
                "operations", "info", "schedule",
                f"Scheduled #{approval_id}",
                details=f"time={scheduled_time}, platforms={platforms}",
            )

        except Exception as e:
            error_msg = self.personality.format_notification(
                "failed", f"Schedule failed: {e}", approval_id
            )
            await self._notify(
                error_msg,
                topic="schedule",
                action_type="failed",
                result=str(e),
            )
            self.audit_log.log(
                "operations", "reject", "schedule",
                f"Schedule failed #{approval_id}",
                details=str(e), success=False,
            )

    async def _handle_render_request(self, data: dict):
        """Handle a render request — triggers video creation via ContentAgent."""
        approval_id = data.get("approval_id", "?")
        script = data.get("script", "")
        theme = data.get("theme", "")
        metadata = data.get("metadata", {})

        try:
            await self._notify(
                self.personality.format_notification(
                    "render", "Rendering video...", approval_id
                ),
                topic="render",
                action_type="render",
                result="Rendering video...",
            )

            if self.content_agent:
                result = await self.content_agent.create_video_for_approval(
                    script=script,
                    theme=theme,
                    metadata=metadata,
                )
                notification = self.personality.format_notification(
                    "rendered", "Video ready for review", approval_id
                )
            else:
                result = {"status": "no_content_agent"}
                notification = self.personality.format_notification(
                    "rendered",
                    "Render requested (no content agent configured)",
                    approval_id,
                )

            await self._notify(
                notification,
                topic="render",
                action_type="rendered",
                result=notification,
            )

            self.audit_log.log(
                "operations", "info", "render",
                f"Render complete #{approval_id}",
                details=json.dumps(result) if isinstance(result, dict) else str(result),
            )

        except Exception as e:
            error_msg = self.personality.format_notification(
                "failed", f"Render failed: {e}", approval_id
            )
            await self._notify(
                error_msg,
                topic="render",
                action_type="failed",
                result=str(e),
            )
            self.audit_log.log(
                "operations", "reject", "render",
                f"Render failed #{approval_id}",
                details=str(e), success=False,
            )

    async def _handle_content_feedback(self, data: dict):
        """Handle rejection feedback — routes to memory for future learning."""
        approval_id = data.get("approval_id", "?")
        feedback = data.get("feedback", "")
        content_type = data.get("content_type", "unknown")

        if self.memory and feedback:
            try:
                self.memory.store(
                    category="content_feedback",
                    key=f"rejection_{approval_id}",
                    value={
                        "approval_id": approval_id,
                        "content_type": content_type,
                        "feedback": feedback,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
            except Exception as e:
                logger.error(f"Failed to store feedback: {e}")

        notification = self.personality.format_notification(
            "rejected", f"Feedback recorded: {feedback[:100]}", approval_id
        )
        await self._notify(
            notification,
            topic="feedback",
            action_type="rejected",
            result=notification,
        )

        self.audit_log.log(
            "operations", "info", "feedback",
            f"Feedback received #{approval_id}",
            details=feedback[:500],
        )

    async def _handle_execute_request(self, data: dict):
        """Handle an immediate execution request from the dashboard."""
        approval_id = data.get("approval_id", "?")
        action_type = data.get("execute_type", "")
        action_data = data.get("execute_data", {})

        result = await self.execute_action(action_type, action_data)

        if "failed" in result.lower() or "error" in result.lower():
            notify_action = "failed"
            notification = self.personality.format_notification(
                "failed", result, approval_id
            )
        else:
            notify_action = "executed"
            notification = self.personality.format_notification(
                "executed", result, approval_id
            )
            self.approval_queue.mark_executed(int(approval_id))

        await self._notify(
            notification,
            topic="execute",
            action_type=notify_action,
            result=result,
        )

    # ------------------------------------------------------------------
    # Scheduled video execution (registered with ContentScheduler)
    # ------------------------------------------------------------------

    async def _execute_scheduled_video(self, job_data: dict):
        """
        Execute a scheduled video distribution.
        Called by ContentScheduler when a scheduled time arrives.
        """
        approval_id = job_data.get("approval_id", "?")
        platforms = job_data.get("platforms", [])
        video_path = job_data.get("video_path", "")

        try:
            if self.video_distributor:
                result = await self.video_distributor.distribute(
                    video_path=video_path,
                    platforms=platforms,
                    metadata=job_data.get("metadata", {}),
                )

                # Build platform result summary
                successes = []
                failures = []
                for platform, status in result.items():
                    if isinstance(status, dict) and status.get("success"):
                        url = status.get("url", "")
                        successes.append(f"{platform}" + (f" ({url})" if url else ""))
                    else:
                        error = status.get("error", "unknown") if isinstance(status, dict) else str(status)
                        failures.append(f"{platform}: {error}")

                parts = []
                if successes:
                    parts.append(f"Posted to {', '.join(successes)}")
                if failures:
                    parts.append(f"Failed: {'; '.join(failures)}")

                result_text = ". ".join(parts) if parts else "Distribution complete"
            else:
                result_text = f"Distributed to {', '.join(platforms)}" if platforms else "No distributor configured"

            notification = self.personality.format_notification(
                "executed", result_text, approval_id
            )
            await self._notify(
                notification,
                topic="distribute",
                action_type="executed",
                result=result_text,
            )

            self.audit_log.log(
                "operations", "info", "distribute",
                f"Video distributed #{approval_id}",
                details=result_text,
            )

        except Exception as e:
            error_msg = self.personality.format_notification(
                "failed", f"Distribution failed: {e}", approval_id
            )
            await self._notify(
                error_msg,
                topic="distribute",
                action_type="failed",
                result=str(e),
            )
            self.audit_log.log(
                "operations", "reject", "distribute",
                f"Distribution failed #{approval_id}",
                details=str(e), success=False,
            )

    # ------------------------------------------------------------------
    # Direct action execution (called from handle_command)
    # ------------------------------------------------------------------

    async def execute_action(self, action_type: str, action_data: dict) -> str:
        """Execute an approved action through the appropriate tool."""
        try:
            if action_type in ("tweet", "thread", "reply"):
                if not self.twitter:
                    return "Twitter tool not configured"
                result = await self.twitter.execute(action_data)
                if "error" in result:
                    return f"Twitter error: {result['error']}"
                url = result.get("url", "")
                return f"Posted: {url}"

            elif action_type == "video_distribute":
                if not self.video_distributor:
                    return "Video distributor not configured"
                platforms = action_data.get("platforms", [])
                result = await self.video_distributor.distribute(
                    video_path=action_data.get("video_path", ""),
                    platforms=platforms,
                    metadata=action_data.get("metadata", {}),
                )
                return f"Distributed to {len(platforms)} platform(s)"

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

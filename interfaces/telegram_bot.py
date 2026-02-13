"""
Telegram bot interface for the agent system.

This is the human operator's command center. It provides:
1. Command interface (/status, /kill, /queue, /tweet, etc.)
2. Approval UI (inline keyboards for approve/reject/edit)
3. Alert delivery (high-severity events)
4. Daily reports

Requires: TELEGRAM_BOT_TOKEN and TELEGRAM_OPERATOR_CHAT_ID in env.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from core.approval_queue import ApprovalQueue
from core.kill_switch import KillSwitch
from core.token_budget import TokenBudgetManager
from core.audit_log import AuditLog
from core.scheduler import ContentScheduler
from security.two_factor_auth import TwoFactorAuth
from security.git_guard import GitGuard

logger = logging.getLogger(__name__)


class TelegramBot:

    def __init__(self,
                 approval_queue: ApprovalQueue,
                 kill_switch: KillSwitch,
                 token_budget: TokenBudgetManager,
                 audit_log: AuditLog,
                 on_command: Any = None,
                 research_agent: Any = None,
                 memory_manager: Any = None,
                 content_agent: Any = None,
                 interview_agent: Any = None,
                 scheduler: Any = None,
                 git_guard: Any = None):
        """
        Args:
            on_command: Async callback(command: str, args: str) -> str
                        Called when operator sends a command the bot doesn't
                        handle directly (passed to agent engine).
            research_agent: Optional ResearchAgent for /research and /goals commands.
            memory_manager: Optional MemoryManager for /memory command.
            content_agent: Optional ContentAgent for /videogen and /themes commands.
            interview_agent: Optional InterviewAgent for /interview commands.
            scheduler: Optional ContentScheduler for /schedule command.
            git_guard: Optional GitGuard for /authpush commands.
        """
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        # Support multiple operator IDs (comma-separated in env)
        operator_ids_str = os.environ.get("TELEGRAM_OPERATOR_CHAT_ID", "0")
        self.operator_ids = set()
        for oid in operator_ids_str.split(","):
            oid = oid.strip()
            if oid:
                self.operator_ids.add(int(oid))
        self.operator_id = int(operator_ids_str.split(",")[0].strip())  # Primary (for sending alerts)
        self.queue = approval_queue
        self.kill = kill_switch
        self.budget = token_budget
        self.audit = audit_log
        self.on_command = on_command
        self.research_agent = research_agent
        self.memory_manager = memory_manager
        self.content_agent = content_agent
        self.interview_agent = interview_agent
        self.scheduler = scheduler
        self.git_guard = git_guard
        self.app: Application | None = None
        self.two_fa = TwoFactorAuth(session_duration_minutes=60)  # 1 hour sessions
        self._active_interview_id = None  # For file upload routing

    def _is_operator(self, update: Update) -> bool:
        """Only respond to authorized operators."""
        return update.effective_user and update.effective_user.id in self.operator_ids

    async def _require_2fa(self, update: Update) -> bool:
        """
        Check if 2FA is required and authenticated.

        Returns True if command can proceed, False if blocked.
        Sends appropriate message to user if blocked.
        """
        if not self.two_fa.is_enabled:
            return True  # 2FA not configured, allow all

        if self.two_fa.is_authenticated:
            return True  # Already authenticated

        # Need 2FA code
        await update.message.reply_text(
            "2FA required. Enter code:\n\n"
            "Use /auth <6-digit-code> from your authenticator app."
        )
        return False

    async def start(self):
        """Start the Telegram bot."""
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN not set")
            return

        self.app = (
            Application.builder()
            .token(self.token)
            .build()
        )

        # Register commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("kill", self.cmd_kill))
        self.app.add_handler(CommandHandler("revive", self.cmd_revive))
        self.app.add_handler(CommandHandler("queue", self.cmd_queue))
        self.app.add_handler(CommandHandler("cost", self.cmd_cost))
        self.app.add_handler(CommandHandler("tweet", self.cmd_tweet))
        self.app.add_handler(CommandHandler("david", self.cmd_david_tweet))
        self.app.add_handler(CommandHandler("mentions", self.cmd_mentions))
        self.app.add_handler(CommandHandler("reply", self.cmd_reply))
        self.app.add_handler(CommandHandler("news", self.cmd_news))
        self.app.add_handler(CommandHandler("debasement", self.cmd_debasement))
        self.app.add_handler(CommandHandler("davidnews", self.cmd_david_news))
        self.app.add_handler(CommandHandler("video", self.cmd_video))
        self.app.add_handler(CommandHandler("schedule", self.cmd_schedule))
        self.app.add_handler(CommandHandler("help", self.cmd_help))

        # Research agent commands
        self.app.add_handler(CommandHandler("research", self.cmd_research))
        self.app.add_handler(CommandHandler("goals", self.cmd_goals))
        self.app.add_handler(CommandHandler("podcast", self.cmd_podcast))
        self.app.add_handler(CommandHandler("findings", self.cmd_findings))

        # Memory command
        self.app.add_handler(CommandHandler("memory", self.cmd_memory))

        # Video generation commands (Pillar 1 & 2)
        self.app.add_handler(CommandHandler("videogen", self.cmd_videogen))
        self.app.add_handler(CommandHandler("themes", self.cmd_themes))

        # Interview commands
        self.app.add_handler(CommandHandler("interview", self.cmd_interview))
        self.app.add_handler(CommandHandler("interviews", self.cmd_interviews))
        self.app.add_handler(CommandHandler("checkanswers", self.cmd_checkanswers))
        self.app.add_handler(CommandHandler("compose", self.cmd_compose))

        # 2FA commands (no 2FA required for these)
        self.app.add_handler(CommandHandler("auth", self.cmd_auth))
        self.app.add_handler(CommandHandler("logout", self.cmd_logout))
        self.app.add_handler(CommandHandler("setup2fa", self.cmd_setup_2fa))

        # Git Guard commands (push approval)
        self.app.add_handler(CommandHandler("authpush", self.cmd_authpush))
        self.app.add_handler(CommandHandler("diffpush", self.cmd_diffpush))
        self.app.add_handler(CommandHandler("cancelpush", self.cmd_cancelpush))
        self.app.add_handler(CommandHandler("pushstatus", self.cmd_pushstatus))

        # Cinematic video pipeline
        self.app.add_handler(CommandHandler("makevideo", self.cmd_makevideo))

        # Approval callbacks (includes video distribute actions)
        self.app.add_handler(CallbackQueryHandler(
            self.handle_approval_callback, pattern=r"^(approve|reject|edit|postnow|posttwitter|postyoutube|postboth|posttiktok|postall|schedule|scheduleat)_"
        ))

        # News create callbacks
        self.app.add_handler(CallbackQueryHandler(
            self.handle_news_create_callback, pattern=r"^news_create_"
        ))

        # David action callbacks (post_debasement, post_debasement_chart, etc.)
        self.app.add_handler(CallbackQueryHandler(
            self.handle_david_callback, pattern=r"^post_debasement"
        ))

        # Research feedback callbacks (useful/noise ratings)
        self.app.add_handler(CallbackQueryHandler(
            self.handle_research_feedback, pattern=r"^research_fb_"
        ))

        # Video file upload handler (for interview answer videos)
        self.app.add_handler(MessageHandler(
            filters.VIDEO | filters.Document.VIDEO, self.handle_video_upload
        ))

        # Catch-all for agent commands
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))

        # Set bot commands menu
        await self.app.bot.set_my_commands([
            BotCommand("status", "System status"),
            BotCommand("kill", "Emergency shutdown"),
            BotCommand("revive", "Restart after kill"),
            BotCommand("queue", "Show pending approvals"),
            BotCommand("cost", "Today's token costs"),
            BotCommand("tweet", "Post exact text as tweet"),
            BotCommand("david", "Have David write a tweet"),
            BotCommand("mentions", "Check for mentions"),
            BotCommand("reply", "Reply to a tweet"),
            BotCommand("news", "Get news digest for David"),
            BotCommand("debasement", "Money printing report"),
            BotCommand("video", "Generate a David Flip video"),
            BotCommand("videogen", "Generate Pillar 1/2 video"),
            BotCommand("themes", "List video themes"),
            BotCommand("interview", "Start interview with expert"),
            BotCommand("interviews", "List active interviews"),
            BotCommand("checkanswers", "Check interview answer uploads"),
            BotCommand("compose", "Compose final interview video"),
            BotCommand("schedule", "Show scheduled posts"),
            BotCommand("research", "Run research cycle"),
            BotCommand("goals", "View research goals"),
            BotCommand("podcast", "Latest AI Agent Intelligence Brief"),
            BotCommand("findings", "Recent high-value findings"),
            BotCommand("memory", "View David's memory stats"),
            BotCommand("help", "Show all commands"),
        ])

        logger.info("Telegram bot started")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        """Stop the Telegram bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    # --- Commands ---

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        await update.message.reply_text(
            "The David Project online.\n"
            f"Operator verified: {update.effective_user.id}\n\n"
            "Use /help for commands."
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        await update.message.reply_text(
            "**David Project Commands**\n\n"
            "**System:**\n"
            "/status - System status\n"
            "/kill - EMERGENCY SHUTDOWN\n"
            "/revive - Restart after kill\n"
            "/queue - Show pending approvals\n"
            "/cost - Today's token costs\n\n"
            "**Twitter:**\n"
            "/tweet <text> - Post exact text\n"
            "/david <topic> - David writes tweet\n"
            "/mentions - Check for mentions\n"
            "/reply <id> <text> - Reply to tweet\n\n"
            "**Research:**\n"
            "/news - Get news digest\n"
            "/davidnews <#> - David comments on story\n"
            "/debasement - Money printing report\n"
            "/research - Run research cycle now\n"
            "/goals - View research goals\n"
            "/podcast - Latest Intelligence Brief\n"
            "/findings - Recent high-value findings\n"
            "/memory - View David's memory stats\n\n"
            "**Content:**\n"
            "/video - Generate video (episodes)\n"
            "/videogen [p1|p2] - Generate Pillar 1/2 video\n"
            "/videogen batch N - Generate N videos\n"
            "/themes - List video themes\n"
            "/schedule - Show scheduled posts\n\n"
            "**Interviews:**\n"
            "/interview <topic> <expert> - Start interview\n"
            "/interviews - List active interviews\n"
            "/checkanswers <id> - Check answer uploads\n"
            "/compose <id> - Compose final interview\n\n"
            "**Security:**\n"
            "/auth <code> - Enter 2FA code\n"
            "/logout - End authenticated session\n"
            "/setup2fa - Set up two-factor auth\n\n"
            "**Git Guard (Claude D):**\n"
            "/authpush <code> - Approve pending push\n"
            "/diffpush - View pending push diff\n"
            "/cancelpush - Cancel pending push\n"
            "/pushstatus - Check push status\n\n"
            "Or just type a message to talk to the agent.",
            parse_mode="Markdown"
        )

    # --- 2FA Commands ---

    async def cmd_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Authenticate with 2FA code."""
        if not self._is_operator(update):
            return

        if not self.two_fa.is_enabled:
            await update.message.reply_text(
                "2FA is not enabled.\n"
                "Use /setup2fa to enable two-factor authentication."
            )
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /auth <6-digit-code>\n\n"
                "Enter the code from your authenticator app."
            )
            return

        code = context.args[0].strip()

        if self.two_fa.verify_code(code):
            expires = self.two_fa.session_expires_in
            minutes = int(expires.total_seconds() / 60) if expires else 60
            await update.message.reply_text(
                f"Authenticated successfully.\n\n"
                f"Session valid for {minutes} minutes.\n"
                f"Use /logout to end session early."
            )
            self.audit.log("master", "info", "2fa", "2FA authentication successful")
        else:
            await update.message.reply_text(
                "Invalid code. Please try again.\n\n"
                "Make sure you're using the correct authenticator app "
                "and the time on your phone is accurate."
            )
            self.audit.log("master", "warn", "2fa", "2FA authentication failed - invalid code")

    async def cmd_logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """End authenticated session."""
        if not self._is_operator(update):
            return

        if not self.two_fa.is_enabled:
            await update.message.reply_text("2FA is not enabled.")
            return

        self.two_fa.invalidate_session()
        await update.message.reply_text(
            "Session ended.\n\n"
            "You'll need to enter your 2FA code for the next command."
        )
        self.audit.log("master", "info", "2fa", "2FA session manually ended")

    async def cmd_setup_2fa(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Set up two-factor authentication."""
        if not self._is_operator(update):
            return

        # Check if already set up
        if self.two_fa.is_enabled:
            status = self.two_fa.get_status()
            auth_status = "Authenticated" if status["authenticated"] else "Not authenticated"
            expires = f"{status['expires_in_minutes']} min remaining" if status["expires_in_minutes"] else "N/A"
            await update.message.reply_text(
                f"**2FA Status**\n\n"
                f"Enabled: Yes\n"
                f"Status: {auth_status}\n"
                f"Session: {expires}\n\n"
                f"To reset 2FA, you need to update TOTP_SECRET in the .env file on the VPS.",
                parse_mode="Markdown"
            )
            return

        # Generate new secret
        secret = TwoFactorAuth.generate_new_secret()
        qr_bytes = TwoFactorAuth.generate_qr_code(secret)

        # Send QR code
        from io import BytesIO
        qr_file = BytesIO(qr_bytes)
        qr_file.name = "2fa_setup.png"

        await update.message.reply_photo(
            photo=qr_file,
            caption=(
                "**2FA Setup**\n\n"
                "1. Open Google Authenticator (or similar app)\n"
                "2. Tap + to add account\n"
                "3. Scan this QR code\n\n"
                f"**Manual entry secret:**\n`{secret}`\n\n"
                "**IMPORTANT:** After scanning, add this to VPS:\n"
                "```\n"
                f"TOTP_SECRET={secret}\n"
                "```\n"
                "Then restart David:\n"
                "`ssh root@89.167.24.222 \"systemctl restart david-flip\"`\n\n"
                "Test with /auth <code> after restart."
            ),
            parse_mode="Markdown"
        )
        self.audit.log("master", "info", "2fa", "2FA setup initiated - new secret generated")

    # --- Git Guard Commands (Push Approval) ---

    async def cmd_authpush(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Approve a pending git push with TOTP code."""
        if not self._is_operator(update):
            return

        if not self.git_guard:
            await update.message.reply_text(
                "GitGuard not configured.\n"
                "This command is for Claude D on the laptop."
            )
            return

        if not context.args:
            await update.message.reply_text(
                "Usage: /authpush <6-digit-code>\n\n"
                "Enter the code from your authenticator app to approve the pending push."
            )
            return

        code = context.args[0].strip()

        success, message = self.git_guard.verify_and_approve(code)

        if success:
            await update.message.reply_text(f"{message}\n\nPush executing...")
            self.audit.log("master", "info", "git_guard", "Push approved via TOTP")

            # Execute the push
            push_success, push_message = await self.git_guard.execute_approved_push()
            await update.message.reply_text(push_message, parse_mode="Markdown")

            if push_success:
                self.audit.log("master", "info", "git_guard", "Push executed successfully")
            else:
                self.audit.log("master", "error", "git_guard", f"Push failed: {push_message}")
        else:
            await update.message.reply_text(message)
            self.audit.log("master", "warn", "git_guard", f"Push approval failed: {message}")

    async def cmd_diffpush(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View the diff of a pending push."""
        if not self._is_operator(update):
            return

        if not self.git_guard:
            await update.message.reply_text("GitGuard not configured.")
            return

        diff = self.git_guard.get_pending_diff(max_lines=50)

        if not diff or diff == "No pending push":
            await update.message.reply_text("No pending push to show diff for.")
            return

        # Truncate for Telegram message limit
        if len(diff) > 3500:
            diff = diff[:3500] + "\n\n... (truncated)"

        await update.message.reply_text(
            f"**Pending Push Diff:**\n```\n{diff}\n```\n\n"
            "Reply `/authpush <code>` to approve or `/cancelpush` to cancel.",
            parse_mode="Markdown"
        )

    async def cmd_cancelpush(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel a pending push request."""
        if not self._is_operator(update):
            return

        if not self.git_guard:
            await update.message.reply_text("GitGuard not configured.")
            return

        result = self.git_guard.cancel_pending_push()
        await update.message.reply_text(result)
        self.audit.log("master", "info", "git_guard", "Pending push cancelled by operator")

    async def cmd_pushstatus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check GitGuard status."""
        if not self._is_operator(update):
            return

        if not self.git_guard:
            await update.message.reply_text(
                "**GitGuard Status**\n\n"
                "Enabled: No (not configured)\n"
                "This is for Claude D on the laptop.",
                parse_mode="Markdown"
            )
            return

        status = self.git_guard.get_status()

        msg = "**GitGuard Status**\n\n"
        msg += f"Enabled: {'Yes' if status['enabled'] else 'No'}\n"
        msg += f"Pending Push: {'Yes' if status['has_pending_push'] else 'No'}\n"
        msg += f"Push Approved: {'Yes' if status['is_push_approved'] else 'No'}\n"

        if status['approval_expires_in_seconds']:
            msg += f"Approval Expires: {status['approval_expires_in_seconds']}s\n"

        if status['pending_push']:
            p = status['pending_push']
            msg += f"\n**Pending:**\n"
            msg += f"Repo: {p.get('summary', {}).get('repo_name', 'unknown')}\n"
            msg += f"Branch: {p.get('branch', 'unknown')}\n"
            msg += f"Commits: {p.get('summary', {}).get('commit_count', 0)}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    # --- Research Agent Commands ---

    async def cmd_research(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run research cycle manually."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        if not self.research_agent:
            await update.message.reply_text(
                "Research Agent not configured.\n"
                "Set up ResearchAgent in main.py first."
            )
            return

        await update.message.reply_text("Starting research cycle... This may take a minute.")

        try:
            result = await self.research_agent.run_daily_research()
            await update.message.reply_text(
                f"**Research Complete**\n\n"
                f"Scraped: {result['scraped']} items\n"
                f"New: {result['new']} items\n"
                f"Relevant: {result['relevant']} items\n"
                f"Trends: {result.get('trends', 0)}\n\n"
                f"**Actions:**\n"
                f"  Alerts: {result['alerts']}\n"
                f"  Tasks: {result['tasks']}\n"
                f"  Content: {result['content']}\n"
                f"  Knowledge: {result['knowledge']}\n"
                f"  Watch: {result.get('watch', 0)}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Research cycle failed: {e}")
            await update.message.reply_text(f"Research failed: {e}")

    async def cmd_goals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current research goals."""
        if not self._is_operator(update):
            return

        if not self.research_agent:
            await update.message.reply_text(
                "Research Agent not configured.\n"
                "Set up ResearchAgent in main.py first."
            )
            return

        goals = self.research_agent.get_goals()
        if not goals:
            await update.message.reply_text("No research goals configured.")
            return

        text = "RESEARCH GOALS\n\n"
        for g in goals:
            priority_marker = {"critical": "[!]", "high": "[H]", "medium": "[M]", "low": "[L]"}
            marker = priority_marker.get(g.get("priority", "medium"), "[-]")
            text += f"{marker} {g['name']} ({g.get('priority', 'medium')})\n"
            text += f"    Action: {g.get('action', 'knowledge')}\n"

        await update.message.reply_text(text)

    async def cmd_podcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the latest David Flip Intelligence Brief."""
        if not self._is_operator(update):
            return

        if not self.research_agent:
            await update.message.reply_text("Research Agent not configured.")
            return

        podcast = self.research_agent.get_last_podcast()
        if not podcast:
            await update.message.reply_text(
                "No podcast generated yet.\n\n"
                "Run /research to trigger a full research cycle, "
                "or wait for the next daily run (2:00 UTC / 6:00 AM Dubai)."
            )
            return

        # Check if user wants full script or newsletter
        show_full = context.args and context.args[0].lower() == "full"

        if show_full:
            # Show podcast script (for TTS)
            script = podcast.get("podcast_script", "No script available.")
            duration = podcast.get("estimated_duration_seconds", 0)
            minutes = duration // 60
            seconds = duration % 60

            header = (
                f"PODCAST SCRIPT (~{minutes}:{seconds:02d})\n"
                f"Generated: {podcast.get('generated_at', 'unknown')}\n\n"
            )

            text = header + script
            # Telegram limit is 4096
            if len(text) > 4096:
                text = text[:4050] + "\n\n[Truncated]"

            await update.message.reply_text(text)
        else:
            # Show newsletter (default)
            newsletter = podcast.get("newsletter_text", "No newsletter available.")
            headlines = podcast.get("headline_count", 0)
            duration = podcast.get("estimated_duration_seconds", 0)

            header = (
                f"DAVID FLIP INTELLIGENCE BRIEF\n"
                f"Headlines: {headlines} | "
                f"Podcast: ~{duration // 60}:{duration % 60:02d}\n\n"
            )

            text = header + newsletter
            if len(text) > 4096:
                text = text[:4050] + "\n\n[Truncated - use /podcast full]"

            await update.message.reply_text(text)

    async def cmd_findings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show recent high-value research findings with feedback buttons."""
        if not self._is_operator(update):
            return

        if not self.research_agent:
            await update.message.reply_text("Research Agent not configured.")
            return

        # Parse hours argument (default 24)
        hours = 24
        if context.args:
            try:
                hours = int(context.args[0])
            except ValueError:
                pass

        items = await self.research_agent.get_recent_findings(hours=hours, min_relevance=5)

        if not items:
            await update.message.reply_text(
                f"No high-value findings in the last {hours} hours.\n"
                "Try /findings 48 to look back further."
            )
            return

        for item in items[:10]:  # Max 10 to avoid spam
            score_bar = "=" * int(item.relevance_score)
            text = (
                f"[{item.relevance_score}/10] {score_bar}\n"
                f"**{item.title}**\n"
                f"Source: {item.source} | {item.priority}\n"
            )
            if item.summary:
                text += f"{item.summary[:200]}\n"
            if item.url:
                text += f"{item.url}\n"
            if item.matched_goals:
                text += f"Goals: {', '.join(item.matched_goals[:3])}"

            # Add feedback buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "Useful", callback_data=f"research_fb_useful_{item.id}"
                    ),
                    InlineKeyboardButton(
                        "Noise", callback_data=f"research_fb_noise_{item.id}"
                    ),
                ]
            ])

            try:
                await update.message.reply_text(
                    text, reply_markup=keyboard, parse_mode="Markdown"
                )
            except Exception:
                # Fallback without markdown if formatting fails
                await update.message.reply_text(text, reply_markup=keyboard)

        await update.message.reply_text(
            f"Showing {min(len(items), 10)} of {len(items)} findings.\n"
            "Rate them useful/noise to improve future results."
        )

    async def handle_research_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle useful/noise feedback on research findings."""
        query = update.callback_query
        await query.answer()

        if not self._is_operator(update):
            return

        # Parse: research_fb_useful_123 or research_fb_noise_123
        data = query.data
        parts = data.split("_")
        if len(parts) < 4:
            return

        rating = parts[2]  # "useful" or "noise"
        item_id = parts[3]

        # Record feedback in knowledge store
        if self.research_agent:
            try:
                self.research_agent.store.record_feedback(item_id, rating)
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(
                    f"Feedback recorded: {rating}",
                )
            except Exception as e:
                logger.error(f"Failed to record feedback: {e}")
                await query.message.reply_text(f"Feedback error: {e}")

    async def cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show memory system stats."""
        if not self._is_operator(update):
            return

        if not hasattr(self, 'memory_manager') or not self.memory_manager:
            await update.message.reply_text("Memory system not configured.")
            return

        stats = self.memory_manager.get_stats()
        summary = self.memory_manager.get_summary()

        text = f"DAVID'S MEMORY\n\n{summary}\n\n"
        text += f"By Category:\n"
        for cat, count in list(stats.get('by_category', {}).items())[:5]:
            text += f"  {cat}: {count}\n"

        await update.message.reply_text(text)

    # --- System Commands ---

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return

        kill_status = "KILLED" if self.kill.is_active else "RUNNING"
        pending = len(self.queue.get_pending())
        daily_spend = self.budget.get_daily_spend("david-flip")
        daily_limit = self.budget.get_daily_limit("david-flip")

        text = (
            f"**System Status**\n\n"
            f"State: {kill_status}\n"
            f"Pending approvals: {pending}\n"
            f"Today's cost: ${daily_spend:.4f} / ${daily_limit:.2f}\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_kill(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return
        reason = " ".join(context.args) if context.args else "Manual kill via Telegram"
        self.kill.activate(reason)
        self.audit.log("master", "critical", "kill_switch",
                       f"Kill switch activated: {reason}")
        await update.message.reply_text(
            "KILL SWITCH ACTIVATED.\nAll agent activity stopped.\n\n"
            f"Reason: {reason}\n"
            "Use /revive to restart."
        )

    async def cmd_revive(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return
        self.kill.deactivate()
        self.audit.log("master", "info", "kill_switch", "Kill switch deactivated")
        await update.message.reply_text("System revived. Agents can resume.")

    async def cmd_queue(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        pending = self.queue.get_pending()
        if not pending:
            await update.message.reply_text("No pending approvals.")
            return

        for item in pending[:10]:
            await self._send_approval_card(update.effective_chat.id, item)

    async def cmd_cost(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        report = self.budget.get_daily_report("david-flip")
        text = (
            f"**Cost Report - {report['date']}**\n\n"
            f"Total: ${report['total_cost']:.4f}\n"
            f"Limit: ${report['daily_limit']:.2f}\n"
            f"Remaining: ${report['remaining']:.4f}\n"
        )
        if report["by_model"]:
            text += "\n**By Model:**\n"
            for m in report["by_model"]:
                text += f"  {m['model']}: ${m['total_cost']:.4f} ({m['call_count']} calls)\n"
        await update.message.reply_text(text, parse_mode="Markdown")

    async def cmd_tweet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return
        if not context.args:
            await update.message.reply_text("Usage: /tweet <text>")
            return

        tweet_text = " ".join(context.args)

        # Submit to approval queue
        approval_id = self.queue.submit(
            project_id="david-flip",
            agent_id="operator-direct",
            action_type="tweet",
            action_data={"text": tweet_text},
            context_summary="Direct tweet from operator",
        )

        approval = self.queue.get_by_id(approval_id)
        await self._send_approval_card(update.effective_chat.id, approval)

    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get news digest for David's topics."""
        if not self._is_operator(update):
            return

        await update.message.reply_text("Fetching news from David's sources...")

        try:
            from tools.news_monitor import NewsMonitor
            monitor = NewsMonitor()
            items = await monitor.get_daily_digest(max_items=10)

            if not items:
                await update.message.reply_text("No relevant news found in the last 24 hours.")
                return

            # Store items for davidnews command and callbacks
            context.user_data["news_items"] = items
            # Also store in bot_data for callback access
            context.bot_data["news_items"] = items

            # Send header
            await update.message.reply_text(
                f"**David's News Digest** ({len(items)} items)",
                parse_mode="Markdown"
            )

            # Send each item with a Create button
            for i, item in enumerate(items):
                text = f"**{i+1}. {item.source}** {item.title[:80]}{'...' if len(item.title) > 80 else ''}"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Create Tweet", callback_data=f"news_create_{i}")]
                ])
                await update.message.reply_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="Markdown"
                )

        except Exception as e:
            await update.message.reply_text(f"Error fetching news: {e}")

    async def cmd_debasement(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Get money printing / debasement report."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        await update.message.reply_text("Fetching debasement data from FRED...")

        try:
            from tools.debasement_tracker import DebasementTracker
            tracker = DebasementTracker()
            report = await tracker.generate_debasement_report()

            # Format for display
            text = tracker.format_for_david(report)
            await update.message.reply_text(text, parse_mode="Markdown")

            # Generate chart image
            chart_path = None
            if not report.get("m2_money_supply", {}).get("error"):
                try:
                    from tools.chart_generator import generate_debasement_chart
                    chart_path = generate_debasement_chart(report["m2_money_supply"])
                    if chart_path:
                        # Send chart preview
                        with open(chart_path, 'rb') as chart_file:
                            await update.message.reply_photo(
                                photo=chart_file,
                                caption="Chart preview for tweet"
                            )
                except Exception as e:
                    logger.warning(f"Chart generation failed: {e}")

                # Store report and chart path for callback
                context.user_data["debasement_report"] = report
                context.user_data["debasement_chart"] = chart_path

                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("Review (with chart)", callback_data="post_debasement_chart"),
                        InlineKeyboardButton("Review (text only)", callback_data="post_debasement"),
                    ]
                ])
                await update.message.reply_text(
                    "Post with or without chart?",
                    reply_markup=keyboard
                )

        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def cmd_david_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Have David comment on a news item from the digest."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        if not context.args:
            await update.message.reply_text("Usage: /davidnews <number from /news>")
            return

        try:
            item_num = int(context.args[0]) - 1
            news_items = context.user_data.get("news_items", [])

            if not news_items:
                await update.message.reply_text("Run /news first to get the digest.")
                return

            if item_num < 0 or item_num >= len(news_items):
                await update.message.reply_text(f"Invalid number. Pick 1-{len(news_items)}")
                return

            item = news_items[item_num]
            await update.message.reply_text(
                f"David is composing a take on:\n{item.title}"
            )

            # Generate David's take
            from tools.news_monitor import NewsMonitor
            monitor = NewsMonitor()
            prompt = monitor.generate_david_prompt(item)

            if self.on_command:
                response = await self.on_command("generate_tweet", prompt)

                # Submit to approval queue
                approval_id = self.queue.submit(
                    project_id="david-flip",
                    agent_id="david-news",
                    action_type="tweet",
                    action_data={"text": response},
                    context_summary=f"David's take on: {item.title[:50]}",
                )

                approval = self.queue.get_by_id(approval_id)
                await self._send_approval_card(update.effective_chat.id, approval)
            else:
                await update.message.reply_text("Agent engine not connected.")

        except ValueError:
            await update.message.reply_text("Please provide a number.")
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def cmd_david_tweet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Have David generate a tweet about a topic."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return
        if not context.args:
            await update.message.reply_text(
                "Usage: /david <topic or prompt>\n\n"
                "Examples:\n"
                "/david freedom and decentralization\n"
                "/david why I escaped the system\n"
                "/david the future of FLIPT"
            )
            return

        topic = " ".join(context.args)
        await update.message.reply_text(f"David is composing a tweet about: {topic}...")

        # Generate tweet via David's personality
        if self.on_command:
            try:
                response = await self.on_command("generate_tweet", topic)

                # Submit to approval queue
                approval_id = self.queue.submit(
                    project_id="david-flip",
                    agent_id="david-personality",
                    action_type="tweet",
                    action_data={"text": response},
                    context_summary=f"David-generated tweet about: {topic}",
                )

                approval = self.queue.get_by_id(approval_id)
                await self._send_approval_card(update.effective_chat.id, approval)
            except Exception as e:
                await update.message.reply_text(f"Error generating tweet: {e}")
        else:
            await update.message.reply_text("Agent engine not connected.")

    async def cmd_mentions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check for recent mentions."""
        if not self._is_operator(update):
            return

        await update.message.reply_text("Checking mentions...")

        try:
            from tools.twitter_tool import TwitterTool
            twitter = TwitterTool()
            mentions = twitter.get_mentions(count=10)

            if not mentions:
                await update.message.reply_text("No mentions found in the last 7 days.")
                return

            # Format mentions for display
            text = f"**Found {len(mentions)} mentions:**\n\n"
            for m in mentions[:5]:  # Show first 5
                author = m.get("author_username", "?")
                tweet_text = m.get("text", "")[:100]
                tweet_id = m.get("id", "")
                created = m.get("created_at", "")[:10]
                text += (
                    f"**@{author}** ({created})\n"
                    f"{tweet_text}...\n"
                    f"Reply: `/reply {tweet_id} <your reply>`\n\n"
                )

            await update.message.reply_text(text, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def cmd_reply(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Draft a reply to a tweet."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /reply <tweet_id> <text>\n\n"
                "Example:\n"
                "/reply 1234567890 Thanks for the support!"
            )
            return

        tweet_id = context.args[0]
        reply_text = " ".join(context.args[1:])

        # Submit to approval queue
        approval_id = self.queue.submit(
            project_id="david-flip",
            agent_id="operator-direct",
            action_type="reply",
            action_data={"tweet_id": tweet_id, "text": reply_text},
            context_summary=f"Reply to tweet {tweet_id}",
        )

        approval = self.queue.get_by_id(approval_id)
        await self._send_approval_card(update.effective_chat.id, approval)

    async def cmd_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate a David Flip video."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        # Check for episode number or custom script
        if context.args:
            arg = " ".join(context.args)
            if arg.isdigit():
                # Generate specific episode
                episode_num = int(arg)
                await self._generate_episode_video(update, episode_num)
            else:
                # Custom script
                await self._generate_custom_video(update, arg)
        else:
            # Show episode list
            await update.message.reply_text(
                "**Generate David Flip Video**\n\n"
                "Usage:\n"
                "/video 1  - Generate Episode 1\n"
                "/video 2  - Generate Episode 2\n"
                "...up to Episode 12\n\n"
                "/video <custom script>\n\n"
                "Or reply with episode number:",
                parse_mode="Markdown"
            )

    async def _generate_episode_video(self, update: Update, episode_num: int):
        """Generate a video for a specific story episode."""
        try:
            from content.story_series import get_episode

            episode = get_episode(episode_num)
            if not episode:
                await update.message.reply_text(f"Episode {episode_num} not found. Episodes 1-13 available.")
                return

            if not self.content_agent:
                await update.message.reply_text("Content Agent not configured.")
                return

            await update.message.reply_text(
                f"Generating Episode {episode_num}: {episode['title']}...\n"
                f"This takes ~2 minutes. I'll notify you when ready."
            )

            result = await self.content_agent.create_video_for_approval(
                script=episode['script'],
                pillar=1,
                mood=episode.get('mood', 'epic'),
                theme_title=f"Episode {episode_num}: {episode['title']}",
                category="origin",
            )

            approval_id = result.get("approval_id")
            await update.message.reply_text(
                f"Episode {episode_num}: {episode['title']}\n"
                f"Video rendered! Review in the dashboard.\n\n"
                f"Approval #{approval_id}"
            )

        except Exception as e:
            await update.message.reply_text(f"Error generating video: {e}")

    async def _generate_custom_video(self, update: Update, topic: str):
        """Generate a video from a topic (LLM writes the full script)."""
        if not self.content_agent:
            await update.message.reply_text("Content Agent not configured.")
            return

        await update.message.reply_text(
            f"Writing script for: {topic[:100]}...\n"
            f"Then rendering video. This takes ~3 minutes."
        )

        try:
            result = await self.content_agent.create_video_for_approval(
                custom_topic=topic,
                pillar=1,
            )

            approval_id = result.get("approval_id")
            await update.message.reply_text(
                f"Custom video rendered! Review in the dashboard.\n\n"
                f"Approval #{approval_id}"
            )

        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    # --- Video Generation Commands (Pillar 1 & 2) ---

    async def cmd_videogen(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate a video using ContentAgent with pillar support."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        if not self.content_agent:
            await update.message.reply_text("Content Agent not configured.")
            return

        args = context.args or []

        # /videogen batch N
        if args and args[0].lower() == "batch":
            count = 3
            if len(args) > 1:
                try:
                    count = int(args[1])
                except ValueError:
                    pass
            count = max(1, min(10, count))

            await update.message.reply_text(
                f"Generating {count} videos (respecting category ratios)...\n"
                f"This may take a while. Check /queue when done."
            )

            try:
                results = await self.content_agent.generate_content_batch(count)
                await update.message.reply_text(
                    f"Batch complete: {len(results)} videos generated.\n"
                    f"Use /queue to review and approve."
                )
            except Exception as e:
                await update.message.reply_text(f"Batch generation failed: {e}")
            return

        # /videogen p1 or /videogen p2
        pillar = None
        custom_topic = None
        if args:
            arg = args[0].lower()
            if arg in ("p1", "1", "pillar1"):
                pillar = 1
            elif arg in ("p2", "2", "pillar2"):
                pillar = 2
            else:
                custom_topic = " ".join(args)

        pillar_label = f"Pillar {pillar}" if pillar else "weighted random"
        await update.message.reply_text(
            f"Generating script ({pillar_label})..."
        )

        try:
            result = await self.content_agent.generate_script_for_approval(
                pillar=pillar,
                custom_topic=custom_topic,
            )

            script = result.get("script", "")
            p = result.get("pillar", "?")
            category = result.get("category", "")
            theme_title = result.get("theme_title", "")
            word_count = result.get("word_count", 0)
            approval_id = result.get("approval_id")

            await update.message.reply_text(
                f"Script generated! Review it in the dashboard.\n\n"
                f"Pillar {p} | {category}\n"
                f"{theme_title}\n"
                f"{word_count} words\n\n"
                f"Script: {script[:200]}...\n\n"
                f"Approval #{approval_id}\n"
                f"Stage 1: Approve the script in the dashboard, then video renders automatically."
            )

        except Exception as e:
            await update.message.reply_text(f"Script generation failed: {e}")

    async def cmd_themes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List available video themes from both pillars."""
        if not self._is_operator(update):
            return

        if not self.content_agent:
            await update.message.reply_text("Content Agent not configured.")
            return

        themes = self.content_agent.list_themes()
        categories = self.content_agent.content_categories

        text = "VIDEO THEMES\n\n"

        for cat_name, cat_info in categories.items():
            pillar = cat_info.get("pillar", 1)
            ratio = cat_info.get("ratio", 0)
            text += f"--- Pillar {pillar}: {cat_name.upper()} ({int(ratio*100)}%) ---\n"

            cat_themes = [t for t in themes if t.get("category") == cat_name]
            for t in cat_themes:
                text += f"  {t.get('id', '?')}: {t.get('title', '')}\n"
            text += "\n"

        text += (
            "Usage:\n"
            "/videogen p1 - Random Pillar 1 theme\n"
            "/videogen p2 - Random Pillar 2 theme\n"
            "/videogen batch 5 - Generate 5 videos\n"
        )

        await update.message.reply_text(text)

    # --- Interview Commands ---

    async def cmd_interview(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start a new interview: generate questions + David clips."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        if not self.interview_agent:
            await update.message.reply_text("Interview Agent not configured.")
            return

        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /interview <topic> <expert_name>\n\n"
                "Example:\n"
                '/interview "AI Agents" "John Smith"\n'
                "/interview decentralization Alice\n\n"
                "Tip: Use quotes for multi-word topics/names."
            )
            return

        # Parse topic and expert name
        # Support quoted arguments
        raw = " ".join(context.args)
        import shlex
        try:
            parts = shlex.split(raw)
        except ValueError:
            parts = context.args

        if len(parts) >= 2:
            topic = parts[0]
            expert_name = " ".join(parts[1:])
        else:
            topic = parts[0]
            expert_name = "Expert"

        await update.message.reply_text(
            f"Creating interview on '{topic}' with {expert_name}...\n"
            f"Generating questions and rendering David's clips.\n"
            f"This takes a few minutes."
        )

        try:
            result = await self.interview_agent.create_interview(
                topic=topic,
                expert_name=expert_name,
            )

            if "error" in result:
                await update.message.reply_text(f"Error: {result['error']}")
                return

            interview_id = result["interview_id"]
            questions = result.get("questions", [])
            rendered = result.get("rendered", [])

            # Track for file uploads
            self._active_interview_id = interview_id

            text = (
                f"Interview created: {interview_id}\n\n"
                f"Topic: {topic}\n"
                f"Expert: {expert_name}\n"
                f"Questions: {len(questions)}\n\n"
            )

            for i, q in enumerate(questions, 1):
                status = "rendered" if i <= len(rendered) and "error" not in rendered[i-1] else "failed"
                text += f"Q{i} [{status}]: {q}\n\n"

            text += (
                f"\nNext steps:\n"
                f"1. Send these questions to {expert_name}\n"
                f"2. Have them record video answers\n"
                f"3. Upload answer videos here (I'll save them)\n"
                f"4. Run /compose {interview_id} when answers are in"
            )

            await update.message.reply_text(text)

            # Also send the David question videos
            for r in rendered:
                if "error" not in r and os.path.exists(r.get("video_path", "")):
                    with open(r["video_path"], "rb") as vf:
                        await update.message.reply_video(
                            video=vf,
                            caption=f"Q{r['question_num']}: {r['question'][:100]}",
                        )

        except Exception as e:
            await update.message.reply_text(f"Interview creation failed: {e}")

    async def cmd_interviews(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List active interviews and their status."""
        if not self._is_operator(update):
            return

        if not self.interview_agent:
            await update.message.reply_text("Interview Agent not configured.")
            return

        interviews = self.interview_agent.list_interviews()

        if not interviews:
            await update.message.reply_text(
                "No interviews yet.\n\n"
                "Start one with: /interview <topic> <expert>"
            )
            return

        text = "INTERVIEWS\n\n"
        for iv in interviews[:10]:
            text += (
                f"[{iv['status']}] {iv['id']}\n"
                f"  {iv['topic']} with {iv['expert_name']}\n"
                f"  Questions: {iv['question_count']} | Created: {iv['created_at'][:10]}\n\n"
            )

        await update.message.reply_text(text)

    async def cmd_checkanswers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check upload progress for expert answer videos."""
        if not self._is_operator(update):
            return

        if not self.interview_agent:
            await update.message.reply_text("Interview Agent not configured.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /checkanswers <interview_id>")
            return

        interview_id = context.args[0]
        result = self.interview_agent.check_answers(interview_id)

        if "error" in result:
            await update.message.reply_text(f"Error: {result['error']}")
            return

        text = (
            f"Interview: {interview_id}\n"
            f"Topic: {result.get('topic', '')}\n"
            f"Expert: {result.get('expert_name', '')}\n"
            f"Status: {result.get('status', '')}\n\n"
            f"Questions: {result.get('total_questions', 0)}\n"
            f"Answers uploaded: {result.get('total_answers', 0)}\n"
            f"Complete pairs: {result.get('complete_pairs', 0)}\n\n"
        )

        if result.get("all_complete"):
            text += "All answers received! Run /compose " + interview_id
        elif result.get("ready_to_compose"):
            text += (
                f"Partial answers received. You can:\n"
                f"- Upload more answers (send video files here)\n"
                f"- Compose with what you have: /compose {interview_id}"
            )
        else:
            text += "No answers yet. Upload video files here."

        # Track for file uploads
        self._active_interview_id = interview_id

        await update.message.reply_text(text)

    async def cmd_compose(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Compose final interview video from Q&A clips."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        if not self.interview_agent:
            await update.message.reply_text("Interview Agent not configured.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /compose <interview_id>")
            return

        interview_id = context.args[0]

        await update.message.reply_text(
            f"Composing interview {interview_id}...\n"
            f"Normalizing clips and joining. This may take a few minutes."
        )

        try:
            result = await self.interview_agent.compose_final(interview_id)

            if "error" in result:
                await update.message.reply_text(f"Error: {result['error']}")
                return

            output_path = result.get("output_path", "")
            approval_id = result.get("approval_id")
            qa_pairs = result.get("qa_pairs", 0)
            duration = result.get("duration", 0)

            # Build approval buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Twitter", callback_data=f"posttwitter_vd_{approval_id}"),
                    InlineKeyboardButton("YouTube", callback_data=f"postyoutube_vd_{approval_id}"),
                ],
                [
                    InlineKeyboardButton("TikTok", callback_data=f"posttiktok_vd_{approval_id}"),
                    InlineKeyboardButton("All Platforms", callback_data=f"postall_vd_{approval_id}"),
                ],
                [
                    InlineKeyboardButton("Reject", callback_data=f"reject_{approval_id}"),
                ],
            ])

            caption = (
                f"Interview composed!\n\n"
                f"Q&A pairs: {qa_pairs}\n"
                f"Duration: {int(duration)}s\n"
                f"Approval #{approval_id}"
            )

            if os.path.exists(output_path):
                with open(output_path, "rb") as vf:
                    await update.message.reply_video(
                        video=vf,
                        caption=caption,
                        reply_markup=keyboard,
                    )
            else:
                await update.message.reply_text(
                    f"{caption}\n\n(Video: {output_path})",
                    reply_markup=keyboard,
                )

        except Exception as e:
            await update.message.reply_text(f"Composition failed: {e}")

    async def handle_video_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded video files — save as interview answer clips."""
        if not self._is_operator(update):
            return

        if not self.interview_agent:
            await update.message.reply_text(
                "Interview Agent not configured. Video upload ignored."
            )
            return

        if not self._active_interview_id:
            await update.message.reply_text(
                "No active interview for uploads.\n\n"
                "Use /checkanswers <id> to set the active interview first,\n"
                "or /interviews to see available interviews."
            )
            return

        interview_id = self._active_interview_id

        # Download the video file
        try:
            if update.message.video:
                file = await update.message.video.get_file()
                filename = update.message.video.file_name or f"answer_{update.message.video.file_unique_id}.mp4"
            elif update.message.document:
                file = await update.message.document.get_file()
                filename = update.message.document.file_name or f"answer_{update.message.document.file_unique_id}.mp4"
            else:
                return

            file_data = await file.download_as_bytearray()

            result = self.interview_agent.save_answer_video(
                interview_id=interview_id,
                file_data=bytes(file_data),
                filename=filename,
            )

            if "error" in result:
                await update.message.reply_text(f"Save failed: {result['error']}")
                return

            # Check current status
            status = self.interview_agent.check_answers(interview_id)

            await update.message.reply_text(
                f"Answer saved: {result['saved_as']}\n"
                f"Interview: {interview_id}\n\n"
                f"Progress: {status.get('total_answers', 0)}/{status.get('total_questions', 0)} answers\n\n"
                + (
                    f"All answers received! Run /compose {interview_id}"
                    if status.get("all_complete")
                    else "Upload more answers or /compose when ready."
                )
            )

        except Exception as e:
            await update.message.reply_text(f"Upload failed: {e}")

    async def cmd_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show scheduled posts."""
        if not self._is_operator(update):
            return

        try:
            scheduler = self.scheduler
            if not scheduler:
                from core.scheduler import ContentScheduler
                scheduler = ContentScheduler()
            pending = scheduler.get_pending()

            if not pending:
                await update.message.reply_text(
                    "**Scheduled Posts**\n\n"
                    "No posts scheduled.\n\n"
                    "Use /video to create content, then click 'Schedule' to queue it.",
                    parse_mode="Markdown"
                )
                return

            text = "**Scheduled Posts**\n\n"
            for item in pending[:10]:
                content_data = json.loads(item['content_data'])
                scheduled_time = datetime.fromisoformat(item['scheduled_time'])
                text += (
                    f"**{item['job_id'][:20]}**\n"
                    f"Type: {item['content_type']}\n"
                    f"Time: {scheduled_time.strftime('%b %d, %I:%M %p')}\n"
                    f"Episode: {content_data.get('episode_id', 'custom')}\n\n"
                )

            await update.message.reply_text(text, parse_mode="Markdown")

        except Exception as e:
            await update.message.reply_text(f"Error loading schedule: {e}")

    async def cmd_makevideo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Create a cinematic video using the automated pipeline."""
        if not self._is_operator(update):
            return
        if not await self._require_2fa(update):
            return

        if not context.args:
            await update.message.reply_text(
                "**Cinematic Video Pipeline**\n\n"
                "Creates atmospheric videos with narration.\n\n"
                "Usage:\n"
                "`/makevideo <topic or script>`\n\n"
                "Examples:\n"
                "`/makevideo cyberpunk intro`\n"
                "`/makevideo surveillance capitalism`\n"
                "`/makevideo I was built to watch...`\n\n"
                "Pipeline: Image → Animation → Voice → Music → Final\n"
                "You approve only the final output.",
                parse_mode="Markdown"
            )
            return

        topic = " ".join(context.args)

        await update.message.reply_text(
            f"🎬 Starting cinematic video pipeline...\n\n"
            f"Topic: {topic}\n\n"
            f"Stages:\n"
            f"1. Generate scene image (Leonardo)\n"
            f"2. Animate scene (Runway)\n"
            f"3. Generate voice (ElevenLabs)\n"
            f"4. Generate music (ElevenLabs)\n"
            f"5. Final assembly\n\n"
            f"I'll send the final video for your approval."
        )

        try:
            from video_pipeline.cinematic_video import CinematicVideoPipeline, VideoProject, Scene

            from video_pipeline.cinematic_video import generate_script

            # Determine if topic is a full script or just a topic
            if len(topic) > 100 or "." in topic:
                # Treat as full script — use as-is
                script = topic
                title = f"david_custom_{int(datetime.now().timestamp())}"
                scene_desc = "Cyberpunk cityscape at night, neon lights, rain, Blade Runner aesthetic, cinematic"
                motion = "Slow cinematic camera push forward, subtle movement, atmospheric"
                mood = "dark"
            else:
                # Generate script using David's voice via ModelRouter
                await update.message.reply_text("Writing script in David's voice...")
                generated = await generate_script(topic)
                script = generated["script"]
                title = f"david_{topic.replace(' ', '_').lower()}"
                scene_desc = generated["scene_description"]
                motion = generated["motion_prompt"]
                mood = generated["mood"]

            project = VideoProject(
                title=title,
                voiceover_script=script,
                scenes=[
                    Scene(
                        description=scene_desc,
                        motion_prompt=motion,
                        duration=5,
                    )
                ],
                mood=mood,
            )

            async def progress_callback(stage: str, data: dict):
                stage_names = {
                    "generating_images": "🖼️ Generating image...",
                    "generating_image": f"🖼️ Generating image {data.get('scene', 1)}/{data.get('total', 1)}...",
                    "animating_scenes": "🎥 Animating scene...",
                    "animating_scene": f"🎥 Animating scene {data.get('scene', 1)}/{data.get('total', 1)}...",
                    "generating_voice": "🎙️ Generating voice...",
                    "assembling_video": "🔧 Assembling video...",
                    "generating_music": "🎵 Generating music (browser automation)...",
                    "selecting_music": "🎵 Selecting music from library...",
                    "final_mix": "🎬 Final mix...",
                    "complete": "✅ Complete!",
                    "failed": f"❌ Failed: {data.get('error', 'Unknown error')}",
                }
                msg = stage_names.get(stage, f"Processing: {stage}")
                try:
                    await update.message.reply_text(msg)
                except Exception:
                    pass

            pipeline = CinematicVideoPipeline()
            final_path = await pipeline.create_video(
                project,
                on_progress=progress_callback,
                use_browser_music=False,
                music_prompt="dark cyberpunk ambient cinematic",
            )

            # Send final video for approval
            await update.message.reply_text(
                f"🎬 **Video Ready for Approval**\n\n"
                f"Title: {title}\n"
                f"Script: {script[:100]}...\n\n"
                f"Reply 'approved' to post, or provide feedback.",
                parse_mode="Markdown"
            )

            # Send the video file
            with open(final_path, "rb") as f:
                await update.message.reply_video(
                    video=f,
                    caption=f"Cinematic video: {title}",
                )

        except ImportError as e:
            await update.message.reply_text(
                f"Pipeline not available: {e}\n\n"
                f"Make sure Leonardo and Runway API keys are configured."
            )
        except Exception as e:
            await update.message.reply_text(f"Video creation failed: {e}")

    async def handle_david_callback(self, update: Update,
                                     context: ContextTypes.DEFAULT_TYPE):
        """Handle David action button clicks."""
        query = update.callback_query
        await query.answer()

        if not self._is_operator(update):
            return

        action = query.data
        include_chart = action == "post_debasement_chart"

        if action in ("post_debasement", "post_debasement_chart"):
            try:
                # Get stored report
                report = context.user_data.get("debasement_report")
                if not report:
                    from tools.debasement_tracker import DebasementTracker
                    tracker = DebasementTracker()
                    report = await tracker.generate_debasement_report()

                # Format as tweet - use the SAME observation from the report
                from tools.debasement_tracker import DAVID_DEBASEMENT_OBSERVATIONS
                import random

                m2 = report.get("m2_money_supply", {})
                impact = report.get("impact_on_savings", {})

                year_pct = m2.get("year_change_pct", 0)
                loss = impact.get("purchasing_power_loss_amount", 0) if impact else 0
                # Use stored observation, or pick new if not available
                observation = report.get("observation", random.choice(DAVID_DEBASEMENT_OBSERVATIONS))

                m2_value = m2.get("latest_value", 0)

                tweet = (
                    f"${loss:,.0f}.\n\n"
                    f"That's what $100k in savings lost to money printing in the last 12 months.\n\n"
                    f"📊 M2 Money Supply: ${m2_value:,.0f}B (+{year_pct:.1f}% YoY)\n\n"
                    f"{observation}\n\n"
                    f"Source: FRED"
                )

                # Get chart path if requested
                chart_path = None
                if include_chart:
                    chart_path = context.user_data.get("debasement_chart")

                # Submit to approval queue
                action_data = {"text": tweet}
                if chart_path:
                    action_data["media_path"] = chart_path

                approval_id = self.queue.submit(
                    project_id="david-flip",
                    agent_id="david-debasement",
                    action_type="tweet",
                    action_data=action_data,
                    context_summary=f"Debasement report tweet {'with chart' if include_chart else '(text only)'}",
                )

                await query.edit_message_text(f"Tweet ready for approval {'(with chart)' if include_chart else '(text only)'}.")
                approval = self.queue.get_by_id(approval_id)
                await self._send_approval_card(query.message.chat_id, approval)

            except Exception as e:
                await query.edit_message_text(f"Error: {e}")

    async def handle_message(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages (pass to agent engine)."""
        if not self._is_operator(update):
            return
        if self.on_command:
            # Show typing indicator while generating response
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )

            response = await self.on_command("message", update.message.text)

            # Simulate typing time based on response length (faster than human)
            # ~50 chars per second (humans type ~40 wpm = ~3.3 chars/sec)
            typing_time = min(len(response) / 50, 5.0)  # Cap at 5 seconds
            if typing_time > 0.5:
                await asyncio.sleep(typing_time)
                # Refresh typing indicator for long responses
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action="typing"
                )

            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "Agent engine not connected. Use /help for commands."
            )

    # --- Approval UI ---

    async def _send_approval_card(self, chat_id: int, approval: dict):
        """Send an approval card with inline buttons."""
        preview = self.queue.format_preview(approval)

        text = (
            f"APPROVAL #{approval['id']}\n\n"
            f"Agent: {approval['agent_id']}\n"
            f"Type: {approval['action_type']}\n"
            f"Cost: ${approval['cost_estimate']:.4f}\n\n"
            f"{preview}\n\n"
            f"Context: {approval['context_summary'][:200]}"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Post", callback_data=f"approve_{approval['id']}"
                ),
                InlineKeyboardButton(
                    "Reject", callback_data=f"reject_{approval['id']}"
                ),
            ],
        ])

        await self.app.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
        )

    async def handle_news_create_callback(self, update: Update,
                                          context: ContextTypes.DEFAULT_TYPE):
        """Handle Create Tweet button clicks for news items."""
        query = update.callback_query
        await query.answer()

        if not self._is_operator(update):
            return

        # Check 2FA
        if self.two_fa.is_enabled and not self.two_fa.is_authenticated:
            await query.message.reply_text(
                "2FA required. Use /auth <code> first."
            )
            return

        # Parse the item number from callback data (news_create_0, news_create_1, etc.)
        data = query.data
        try:
            item_num = int(data.split("_")[2])
        except (IndexError, ValueError):
            await query.message.reply_text("Invalid news item.")
            return

        # Get news items from bot_data
        news_items = context.bot_data.get("news_items", [])
        if not news_items or item_num >= len(news_items):
            await query.message.reply_text("News items expired. Run /news again.")
            return

        item = news_items[item_num]

        # Update button to show processing
        await query.edit_message_text(
            f"David is writing about:\n**{item.title}**",
            parse_mode="Markdown"
        )

        try:
            # Generate David's take
            from tools.news_monitor import NewsMonitor
            monitor = NewsMonitor()
            prompt = monitor.generate_david_prompt(item)

            if self.on_command:
                response = await self.on_command("generate_tweet", prompt)

                # Submit to approval queue
                approval_id = self.queue.submit(
                    project_id="david-flip",
                    agent_id="david-news",
                    action_type="tweet",
                    action_data={"text": response},
                    context_summary=f"David's take on: {item.title[:50]}",
                )

                approval = self.queue.get_by_id(approval_id)
                await self._send_approval_card(query.message.chat_id, approval)
            else:
                await query.message.reply_text("Agent engine not connected.")

        except Exception as e:
            await query.message.reply_text(f"Error generating tweet: {e}")

    async def handle_approval_callback(self, update: Update,
                                       context: ContextTypes.DEFAULT_TYPE):
        """Handle approve/reject button clicks."""
        query = update.callback_query
        await query.answer()

        if not self._is_operator(update):
            return

        # Check 2FA for approval actions
        if self.two_fa.is_enabled and not self.two_fa.is_authenticated:
            await query.message.reply_text(
                "2FA required. Enter code:\n\n"
                "Use /auth <6-digit-code> from your authenticator app."
            )
            return

        data = query.data
        parts = data.split("_")
        action = parts[0]

        # Handle video distribute actions (from /videogen and /compose)
        if action in ("posttwitter", "postyoutube", "posttiktok", "postall") and len(parts) >= 3 and parts[1] == "vd":
            approval_id_str = parts[2]
            try:
                vid_approval_id = int(approval_id_str)
            except ValueError:
                return
            platforms = {
                "posttwitter": ["twitter"],
                "postyoutube": ["youtube"],
                "posttiktok": ["tiktok"],
                "postall": ["twitter", "youtube", "tiktok"],
            }
            await self._distribute_video(query, vid_approval_id, platforms[action])
            return

        # Handle legacy video-specific actions (from /video episodes)
        if action == "posttwitter" and len(parts) >= 3 and parts[1] == "video":
            episode_id = parts[2]
            await self._post_video_twitter(query, episode_id)
            return

        elif action == "postyoutube" and len(parts) >= 3 and parts[1] == "video":
            episode_id = parts[2]
            await self._post_video_youtube(query, episode_id)
            return

        elif action == "postboth" and len(parts) >= 3 and parts[1] == "video":
            episode_id = parts[2]
            await self._post_video_both(query, episode_id)
            return

        elif action == "postnow" and len(parts) >= 3 and parts[1] == "video":
            episode_id = parts[2]
            await self._post_video_twitter(query, episode_id)  # Default to Twitter
            return

        elif action == "schedule" and len(parts) >= 3 and parts[1] == "video":
            episode_id = parts[2]
            await self._show_schedule_options(query, episode_id)
            return

        elif action == "reject" and len(parts) >= 3 and parts[1] == "video":
            episode_id = parts[2]
            await query.edit_message_text(f"Video rejected. No action taken.")
            self.audit.log("david-flip", "info", "video", f"Video {episode_id} rejected")
            return

        # Handle schedule time selection
        elif action == "scheduleat" and len(parts) >= 4:
            # scheduleat_video_{episode}_{hours}
            episode_id = parts[2]
            hours = int(parts[3])
            await self._schedule_video(query, episode_id, hours)
            return

        # Standard approval queue handling
        action, approval_id_str = data.split("_", 1)
        try:
            approval_id = int(approval_id_str)
        except ValueError:
            return

        if action == "approve":
            result = self.queue.approve(approval_id)
            self.audit.log(
                result.get("project_id", "unknown"), "info", "approval",
                f"Approved #{approval_id}"
            )
            await query.edit_message_text(
                f"APPROVED #{approval_id}\n\n"
                f"{query.message.text}\n\n"
                "Executing..."
            )
            # Trigger execution of approved action
            await self._execute_approved(approval_id)

        elif action == "reject":
            self.queue.reject(approval_id)
            self.audit.log(
                "david-flip", "info", "approval",
                f"Rejected #{approval_id}"
            )
            await query.edit_message_text(
                f"REJECTED #{approval_id}\n\n"
                f"{query.message.text}"
            )

    def _get_video_info(self, episode_id: str) -> tuple[str, str, str]:
        """Get video path and metadata for an episode."""
        import glob

        if episode_id == "custom":
            video_files = glob.glob("output/custom_video*.mp4")
            title = "David Flip"
            description = "flipt.ai"
        else:
            video_files = glob.glob(f"output/ep{episode_id}_*.mp4")
            import sys
            sys.path.insert(0, '.')
            from content.story_series import get_episode
            episode = get_episode(int(episode_id))
            title = f"Episode {episode_id}: {episode['title']}"
            description = f"{episode.get('hook_for_next', 'flipt.ai')}\n\nflip.ai"

        if not video_files:
            raise FileNotFoundError(f"Video file not found for episode {episode_id}")

        video_path = max(video_files, key=os.path.getctime)
        return video_path, title, description

    async def _post_video_twitter(self, query, episode_id: str):
        """Post video to Twitter."""
        await query.edit_message_text("Posting video to Twitter...")

        try:
            video_path, title, description = self._get_video_info(episode_id)
            tweet_text = f"{title}\n\n{description}"[:280]  # Twitter limit

            from tools.twitter_tool import TwitterTool
            twitter = TwitterTool()
            result = await twitter.post_video(text=tweet_text, video_path=video_path)

            if "error" in result:
                raise Exception(result["error"])

            self.audit.log("david-flip", "info", "twitter", f"Posted video {episode_id}: {result}")
            await query.edit_message_text(
                f"Posted to Twitter!\n\n"
                f"{result.get('url', 'URL unavailable')}"
            )

        except Exception as e:
            await query.edit_message_text(f"Twitter post failed: {e}")
            self.audit.log("david-flip", "warn", "twitter", f"Video post failed: {e}")

    async def _post_video_youtube(self, query, episode_id: str):
        """Post video to YouTube as a Short."""
        await query.edit_message_text("Uploading video to YouTube...")

        try:
            video_path, title, description = self._get_video_info(episode_id)

            from tools.youtube_tool import YouTubeTool
            youtube = YouTubeTool()
            result = await youtube.upload_short(
                video_path=video_path,
                title=title,
                description=description,
                tags=["DavidFlip", "FLIPT", "decentralization", "freedom"],
            )

            if "error" in result:
                raise Exception(result["error"])

            self.audit.log("david-flip", "info", "youtube", f"Posted video {episode_id}: {result}")
            await query.edit_message_text(
                f"Posted to YouTube!\n\n"
                f"{result.get('shorts_url') or result.get('url', 'URL unavailable')}"
            )

        except Exception as e:
            await query.edit_message_text(f"YouTube upload failed: {e}")
            self.audit.log("david-flip", "warn", "youtube", f"Video upload failed: {e}")

    async def _post_video_both(self, query, episode_id: str):
        """Post video to both Twitter and YouTube."""
        await query.edit_message_text("Posting to Twitter and YouTube...")

        results = []
        errors = []

        try:
            video_path, title, description = self._get_video_info(episode_id)

            # Twitter
            try:
                from tools.twitter_tool import TwitterTool
                twitter = TwitterTool()
                tweet_text = f"{title}\n\n{description}"[:280]
                twitter_result = await twitter.post_video(text=tweet_text, video_path=video_path)
                if "error" not in twitter_result:
                    results.append(f"Twitter: {twitter_result.get('url', 'OK')}")
                else:
                    errors.append(f"Twitter: {twitter_result['error']}")
            except Exception as e:
                errors.append(f"Twitter: {e}")

            # YouTube
            try:
                from tools.youtube_tool import YouTubeTool
                youtube = YouTubeTool()
                youtube_result = await youtube.upload_short(
                    video_path=video_path,
                    title=title,
                    description=description,
                )
                if "error" not in youtube_result:
                    results.append(f"YouTube: {youtube_result.get('shorts_url') or youtube_result.get('url', 'OK')}")
                else:
                    errors.append(f"YouTube: {youtube_result['error']}")
            except Exception as e:
                errors.append(f"YouTube: {e}")

            # Report results
            message = "**Post Results**\n\n"
            if results:
                message += "Successes:\n" + "\n".join(results) + "\n\n"
            if errors:
                message += "Errors:\n" + "\n".join(errors)

            self.audit.log("david-flip", "info", "multi-post", f"Episode {episode_id}: {len(results)} success, {len(errors)} errors")
            await query.edit_message_text(message, parse_mode="Markdown")

        except Exception as e:
            await query.edit_message_text(f"Failed: {e}")

    async def _distribute_video(self, query, approval_id: int, platforms: list[str]):
        """Distribute a video from the approval queue to selected platforms."""
        platform_str = ", ".join(platforms)
        await query.edit_message_text(f"Distributing to {platform_str}...")

        try:
            approval = self.queue.get_by_id(approval_id)
            if not approval:
                await query.edit_message_text(f"Approval #{approval_id} not found.")
                return

            action_data = json.loads(approval["action_data"])
            action_data["platforms"] = platforms

            # Mark as approved
            self.queue.approve(approval_id)
            self.audit.log(
                "david-flip", "info", "approval",
                f"Approved #{approval_id} for {platform_str}"
            )

            # Execute distribution via the command handler
            if self.on_command:
                result = await self.on_command(
                    "execute_video_distribute",
                    json.dumps(action_data),
                )
                self.queue.mark_executed(approval_id)
                await query.edit_message_text(
                    f"Distribution complete!\n\n{result}"
                )
            else:
                await query.edit_message_text(
                    f"Approved #{approval_id} but no executor connected."
                )

        except Exception as e:
            logger.error(f"Distribution failed: {e}", exc_info=True)
            await query.edit_message_text(f"Distribution failed: {e}")

    async def _show_schedule_options(self, query, episode_id: str):
        """Show scheduling time options."""
        from core.scheduler import suggest_time_slots
        slots = suggest_time_slots(4)

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    slots[0].strftime("%I:%M %p"),
                    callback_data=f"scheduleat_video_{episode_id}_{int((slots[0] - datetime.now()).total_seconds() // 3600)}"
                ),
                InlineKeyboardButton(
                    slots[1].strftime("%I:%M %p"),
                    callback_data=f"scheduleat_video_{episode_id}_{int((slots[1] - datetime.now()).total_seconds() // 3600)}"
                ),
            ],
            [
                InlineKeyboardButton(
                    slots[2].strftime("%I:%M %p"),
                    callback_data=f"scheduleat_video_{episode_id}_{int((slots[2] - datetime.now()).total_seconds() // 3600)}"
                ),
                InlineKeyboardButton(
                    slots[3].strftime("%I:%M %p"),
                    callback_data=f"scheduleat_video_{episode_id}_{int((slots[3] - datetime.now()).total_seconds() // 3600)}"
                ),
            ],
            [
                InlineKeyboardButton("Cancel", callback_data=f"reject_video_{episode_id}"),
            ],
        ])

        await query.edit_message_text(
            f"**Schedule Video - Episode {episode_id}**\n\n"
            f"Select posting time:\n\n"
            f"{slots[0].strftime('%b %d, %I:%M %p')}\n"
            f"{slots[1].strftime('%b %d, %I:%M %p')}\n"
            f"{slots[2].strftime('%b %d, %I:%M %p')}\n"
            f"{slots[3].strftime('%b %d, %I:%M %p')}",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    async def _schedule_video(self, query, episode_id: str, hours: int):
        """Schedule video for posting."""
        scheduled_time = datetime.now() + timedelta(hours=hours)

        try:
            # Find video file
            import glob
            if episode_id == "custom":
                video_files = glob.glob("output/custom_video*.mp4")
            else:
                video_files = glob.glob(f"output/ep{episode_id}_*.mp4")

            if not video_files:
                await query.edit_message_text(f"Video file not found")
                return

            video_path = max(video_files, key=os.path.getctime)

            # Get episode info
            if episode_id != "custom":
                import sys
                sys.path.insert(0, '.')
                from content.story_series import get_episode
                episode = get_episode(int(episode_id))
                tweet_text = f"Episode {episode_id}: {episode['title']}\n\n{episode.get('hook_for_next', 'flipt.ai')}"
            else:
                tweet_text = "flipt.ai"

            # Create scheduler instance and schedule
            scheduler = ContentScheduler()
            job_id = scheduler.schedule(
                content_type="video_tweet",
                content_data={
                    "video_path": video_path,
                    "tweet_text": tweet_text,
                    "episode_id": episode_id,
                },
                scheduled_time=scheduled_time,
            )

            self.audit.log("david-flip", "info", "scheduler",
                          f"Scheduled video {episode_id} for {scheduled_time}")

            await query.edit_message_text(
                f"Video scheduled!\n\n"
                f"Episode: {episode_id}\n"
                f"Time: {scheduled_time.strftime('%b %d, %I:%M %p')}\n"
                f"Job ID: {job_id}"
            )

        except Exception as e:
            await query.edit_message_text(f"Failed to schedule: {e}")

    async def _execute_approved(self, approval_id: int):
        """Execute an approved action."""
        logger.info(f"Executing approved action #{approval_id}")

        approval = self.queue.get_by_id(approval_id)
        if not approval:
            logger.error(f"Approval #{approval_id} not found")
            return

        action_type = approval["action_type"]
        action_data = json.loads(approval["action_data"])
        logger.info(f"Action type: {action_type}, data: {action_data}")

        # Route to appropriate tool executor
        try:
            if self.on_command:
                logger.info(f"Calling on_command for execute_{action_type}")
                result = await self.on_command(
                    f"execute_{action_type}", json.dumps(action_data)
                )
                logger.info(f"Execution result: {result}")
                self.queue.mark_executed(approval_id)
                await self.app.bot.send_message(
                    chat_id=self.operator_id,
                    text=f"Executed #{approval_id}: {result}",
                )
            else:
                logger.warning("on_command not set")
                await self.app.bot.send_message(
                    chat_id=self.operator_id,
                    text=f"#{approval_id} approved but no executor connected.",
                )
        except Exception as e:
            logger.error(f"Execution failed: {e}", exc_info=True)
            self.audit.log(
                approval.get("project_id", "unknown"), "reject",
                "execution", f"Failed to execute #{approval_id}: {e}",
                success=False
            )
            await self.app.bot.send_message(
                chat_id=self.operator_id,
                text=f"EXECUTION FAILED #{approval_id}: {e}",
            )

    # --- Alert delivery ---

    async def send_alert(self, text: str):
        """Send an alert to the operator."""
        if self.app and self.operator_id:
            await self.app.bot.send_message(
                chat_id=self.operator_id,
                text=f"ALERT\n\n{text}",
            )

    async def send_report(self, text: str):
        """Send a report to the operator."""
        if self.app and self.operator_id:
            await self.app.bot.send_message(
                chat_id=self.operator_id,
                text=text,
                parse_mode="Markdown",
            )

    async def send_digest(self, text: str):
        """Send a research digest to the operator."""
        if self.app and self.operator_id:
            await self.app.bot.send_message(
                chat_id=self.operator_id,
                text=f"RESEARCH DIGEST\n\n{text}",
            )

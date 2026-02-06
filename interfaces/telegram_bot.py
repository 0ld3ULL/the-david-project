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

logger = logging.getLogger(__name__)


class TelegramBot:

    def __init__(self,
                 approval_queue: ApprovalQueue,
                 kill_switch: KillSwitch,
                 token_budget: TokenBudgetManager,
                 audit_log: AuditLog,
                 on_command: Any = None):
        """
        Args:
            on_command: Async callback(command: str, args: str) -> str
                        Called when operator sends a command the bot doesn't
                        handle directly (passed to agent engine).
        """
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.operator_id = int(os.environ.get("TELEGRAM_OPERATOR_CHAT_ID", "0"))
        self.queue = approval_queue
        self.kill = kill_switch
        self.budget = token_budget
        self.audit = audit_log
        self.on_command = on_command
        self.app: Application | None = None

    def _is_operator(self, update: Update) -> bool:
        """Only respond to the operator."""
        return update.effective_user and update.effective_user.id == self.operator_id

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
        self.app.add_handler(CommandHandler("video", self.cmd_video))
        self.app.add_handler(CommandHandler("schedule", self.cmd_schedule))
        self.app.add_handler(CommandHandler("help", self.cmd_help))

        # Approval callbacks
        self.app.add_handler(CallbackQueryHandler(
            self.handle_approval_callback, pattern=r"^(approve|reject|edit|postnow|posttwitter|postyoutube|postboth|schedule|scheduleat)_"
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
            BotCommand("video", "Generate a David Flip video"),
            BotCommand("schedule", "Show scheduled posts"),
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
            "Clawdbot Agent System online.\n"
            f"Operator verified: {update.effective_user.id}\n\n"
            "Use /help for commands."
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_operator(update):
            return
        await update.message.reply_text(
            "**Clawdbot Commands**\n\n"
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
            "**Content:**\n"
            "/video - Generate video\n"
            "/schedule - Show scheduled posts\n\n"
            "Or just type a message to talk to the agent.",
            parse_mode="Markdown"
        )

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

    async def cmd_david_tweet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Have David generate a tweet about a topic."""
        if not self._is_operator(update):
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
            import sys
            sys.path.insert(0, '.')
            from content.story_series import get_episode
            
            episode = get_episode(episode_num)
            if not episode:
                await update.message.reply_text(f"Episode {episode_num} not found. Episodes 1-12 available.")
                return
            
            await update.message.reply_text(
                f"Generating Episode {episode_num}: {episode['title']}...\n"
                f"This takes ~2 minutes. I'll send the video when ready."
            )
            
            # Generate video
            from video_pipeline.video_creator import VideoCreator
            from dotenv import load_dotenv
            load_dotenv()
            
            creator = VideoCreator()
            result = await creator.create_video(
                script=episode['script'],
                output_path=f"output/ep{episode_num}_{episode['title'].replace(' ', '_').lower()}.mp4",
                auto_music=True,
            )
            
            # Create approval buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Twitter", callback_data=f"posttwitter_video_{episode_num}"),
                    InlineKeyboardButton("YouTube", callback_data=f"postyoutube_video_{episode_num}"),
                ],
                [
                    InlineKeyboardButton("Both", callback_data=f"postboth_video_{episode_num}"),
                    InlineKeyboardButton("Schedule", callback_data=f"schedule_video_{episode_num}"),
                ],
                [
                    InlineKeyboardButton("Reject", callback_data=f"reject_video_{episode_num}"),
                ],
            ])

            # Send video WITH buttons attached (no separate message)
            with open(result['video_path'], 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"**Episode {episode_num}: {episode['title']}**\n\n"
                            f"Post where?",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            
        except Exception as e:
            await update.message.reply_text(f"Error generating video: {e}")

    async def _generate_custom_video(self, update: Update, script: str):
        """Generate a video with custom script."""
        await update.message.reply_text(
            f"Generating custom video...\n"
            f"Script: {script[:100]}...\n"
            f"This takes ~2 minutes."
        )
        
        try:
            from video_pipeline.video_creator import VideoCreator
            from dotenv import load_dotenv
            load_dotenv()
            
            creator = VideoCreator()
            result = await creator.create_video(
                script=script,
                output_path="output/custom_video.mp4",
                auto_music=True,
            )
            
            # Create approval buttons
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Twitter", callback_data="posttwitter_video_custom"),
                    InlineKeyboardButton("YouTube", callback_data="postyoutube_video_custom"),
                ],
                [
                    InlineKeyboardButton("Both", callback_data="postboth_video_custom"),
                    InlineKeyboardButton("Schedule", callback_data="schedule_video_custom"),
                ],
                [
                    InlineKeyboardButton("Reject", callback_data="reject_video_custom"),
                ],
            ])

            # Send video WITH buttons attached
            with open(result['video_path'], 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="**Custom David Flip Video**\n\nPost where?",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
            
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def cmd_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show scheduled posts."""
        if not self._is_operator(update):
            return

        try:
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

    async def handle_message(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
        """Handle non-command messages (pass to agent engine)."""
        if not self._is_operator(update):
            return
        if self.on_command:
            response = await self.on_command("message", update.message.text)
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
            f"**Approval #{approval['id']}**\n\n"
            f"Agent: {approval['agent_id']}\n"
            f"Type: {approval['action_type']}\n"
            f"Cost: ${approval['cost_estimate']:.4f}\n\n"
            f"{preview}\n\n"
            f"Context: {approval['context_summary'][:200]}"
        )

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Approve", callback_data=f"approve_{approval['id']}"
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
            parse_mode="Markdown",
        )

    async def handle_approval_callback(self, update: Update,
                                       context: ContextTypes.DEFAULT_TYPE):
        """Handle approve/reject button clicks."""
        query = update.callback_query
        await query.answer()

        if not self._is_operator(update):
            return

        data = query.data
        parts = data.split("_")
        action = parts[0]

        # Handle video-specific actions
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
        approval = self.queue.get_by_id(approval_id)
        if not approval:
            return

        action_type = approval["action_type"]
        action_data = json.loads(approval["action_data"])

        # Route to appropriate tool executor
        # (This will be connected to actual tool implementations)
        try:
            if self.on_command:
                result = await self.on_command(
                    f"execute_{action_type}", json.dumps(action_data)
                )
                self.queue.mark_executed(approval_id)
                await self.app.bot.send_message(
                    chat_id=self.operator_id,
                    text=f"Executed #{approval_id}: {result}",
                )
            else:
                await self.app.bot.send_message(
                    chat_id=self.operator_id,
                    text=f"#{approval_id} approved but no executor connected.",
                )
        except Exception as e:
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

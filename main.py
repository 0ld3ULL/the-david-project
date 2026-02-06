"""
Clawdbot Agent System - Entry Point

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
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables before anything else
load_dotenv()

from core.approval_queue import ApprovalQueue
from core.audit_log import AuditLog
from core.engine import AgentContext, AgentEngine
from core.kill_switch import KillSwitch
from core.model_router import ModelRouter
from core.token_budget import TokenBudgetManager
from interfaces.telegram_bot import TelegramBot
from personality.david_flip import DavidFlipPersonality
from tools.twitter_tool import TwitterTool
from tools.tool_registry import build_registry, get_project_allowed_tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/agent.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("clawdbot")


class ClawdbotSystem:
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

        # Tools
        self.twitter = TwitterTool()
        self.tool_registry = build_registry(twitter_tool=self.twitter)

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

        # Telegram bot
        self.telegram = TelegramBot(
            approval_queue=self.approval_queue,
            kill_switch=self.kill_switch,
            token_budget=self.token_budget,
            audit_log=self.audit_log,
            on_command=self.handle_command,
        )

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
        task = (
            f"Write a single tweet about: {topic}\n\n"
            "Rules:\n"
            "- Maximum 280 characters\n"
            "- Stay in character as David Flip\n"
            "- Be concise, slightly aloof (Musk-style)\n"
            "- Don't use hashtags excessively (1-2 max if any)\n"
            "- Don't start with 'I' too often\n"
            "- Focus on the message, not engagement-baiting\n\n"
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

        response = await self.engine.run(
            context=context,
            task=user_message,
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

        return response

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
                return f"Posted: {url}"
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
        logger.info("CLAWDBOT AGENT SYSTEM STARTING")
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

        # Start Telegram bot
        await self.telegram.start()

        logger.info("System online. Waiting for commands via Telegram.")
        logger.info(f"Operator chat ID: {os.environ.get('TELEGRAM_OPERATOR_CHAT_ID', 'NOT SET')}")

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """Graceful shutdown."""
        logger.info("System shutting down...")
        self.audit_log.log("master", "info", "system", "System shutdown")
        await self.telegram.stop()
        logger.info("System stopped.")


async def main():
    system = ClawdbotSystem()

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

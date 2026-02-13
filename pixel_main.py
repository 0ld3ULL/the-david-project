"""
Pixel — Standalone Entry Point

Runs Pixel (autonomous video production agent) independently on the D computer.
Does NOT need the VPS, Telegram bot, or Twitter. Shares safety infrastructure
(KillSwitch, AuditLog, TokenBudget).

Usage:
    python pixel_main.py                    # Headless mode (production)
    python pixel_main.py --visible          # Visible browser (for manual login / debugging)
    python pixel_main.py --explore 60       # Run 60-minute exploration session
    python pixel_main.py --status           # Print status and exit

Environment:
    Requires .env file with:
    - ANTHROPIC_API_KEY (for Browser Use agent)
    - GOOGLE_API_KEY (for Gemini video review)
"""

import argparse
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

from agents.pixel_agent import PixelAgent
from core.audit_log import AuditLog
from core.kill_switch import KillSwitch
from core.token_budget import TokenBudgetManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/pixel.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("pixel")


class PixelSystem:
    """
    Standalone system for Pixel agent.

    Mirrors DavidSystem's safety patterns but runs independently:
    - Own KillSwitch (shares the file-based mechanism)
    - Own AuditLog (separate DB)
    - Own TokenBudget (separate project budget)
    - No Telegram bot (yet — Phase 2 will add it)
    """

    def __init__(self, headless: bool = True):
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)

        # Safety infrastructure
        self.kill_switch = KillSwitch()
        self.audit_log = AuditLog(db_path="data/pixel_audit.db")
        self.token_budget = TokenBudgetManager(db_path="data/pixel_budget.db")

        # Set Pixel's budget (separate from David's)
        self.token_budget.set_budget("pixel", daily=5.00, monthly=100.00)

        # The agent
        self.agent = PixelAgent(
            kill_switch=self.kill_switch,
            audit_log=self.audit_log,
            token_budget=self.token_budget,
            headless=headless,
        )

        # Event loop reference (for heartbeat)
        self._loop = None

    async def start(self):
        """Start Pixel system."""
        logger.info("=" * 60)
        logger.info("PIXEL — VIDEO PRODUCTION AGENT — STARTING")
        logger.info("=" * 60)

        # Check kill switch
        if self.kill_switch.is_active:
            reason = self.kill_switch.get_reason()
            logger.warning(f"Kill switch is active: {reason}")
            logger.warning("Deactivate kill switch to start Pixel")
            return

        # Start agent
        self.audit_log.log("pixel", "info", "system", "Pixel system starting")

        success = await self.agent.start()
        if not success:
            logger.error("Failed to start Pixel agent")
            self.audit_log.log(
                "pixel", "reject", "system",
                "Pixel failed to start",
                success=False,
            )
            return

        logger.info("Pixel system online.")

        # Notify systemd if running as service
        self._notify_systemd("READY=1")
        self._notify_systemd("WATCHDOG=1")

        self._loop = asyncio.get_running_loop()

        # Heartbeat loop
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

    async def start_exploration(self, duration_minutes: int = 30):
        """Start Pixel, run exploration, then stop."""
        logger.info(f"Running {duration_minutes}-minute exploration session")

        success = await self.agent.start()
        if not success:
            logger.error("Failed to start — cannot explore")
            return

        try:
            result = await self.agent.run_exploration(duration_minutes)
            logger.info(f"Exploration complete: {json.dumps(result, indent=2)}")
        finally:
            await self.agent.stop()

    async def print_status(self):
        """Print current status and exit."""
        status = self.agent.get_status()
        print(json.dumps(status, indent=2))

    async def stop(self):
        """Graceful shutdown."""
        logger.info("Pixel system shutting down...")
        self.audit_log.log("pixel", "info", "system", "Pixel system stopping")
        await self.agent.stop()
        logger.info("Pixel system stopped.")

    async def _heartbeat(self):
        """Update status file and systemd watchdog."""
        status_file = Path("data/pixel_status.json")
        status_data = {
            "online": True,
            "agent": "Pixel",
            "mode": self.agent._mode,
            "timestamp_utc": datetime.utcnow().isoformat(),
        }
        try:
            with open(status_file, "w") as f:
                json.dump(status_data, f)
        except Exception:
            pass

        self._notify_systemd("WATCHDOG=1")

    @staticmethod
    def _notify_systemd(message: str):
        """Send notification to systemd via NOTIFY_SOCKET."""
        import socket as sock_mod
        notify_socket = os.environ.get("NOTIFY_SOCKET")
        if not notify_socket:
            return
        try:
            s = sock_mod.socket(sock_mod.AF_UNIX, sock_mod.SOCK_DGRAM)
            if notify_socket.startswith("@"):
                notify_socket = "\0" + notify_socket[1:]
            s.connect(notify_socket)
            s.sendall(message.encode())
            s.close()
        except Exception:
            pass


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pixel — Autonomous Video Production Agent"
    )
    parser.add_argument(
        "--visible", action="store_true",
        help="Run browser in visible mode (for manual login or debugging)"
    )
    parser.add_argument(
        "--explore", type=int, metavar="MINUTES",
        help="Run an exploration session for N minutes, then exit"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print current status and exit"
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    headless = not args.visible

    system = PixelSystem(headless=headless)

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

    if args.status:
        await system.print_status()
        return

    if args.explore:
        await system.start_exploration(args.explore)
        return

    # Default: run as persistent service
    try:
        await system.start()
    except KeyboardInterrupt:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())

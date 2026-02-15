"""
Occy — Standalone Entry Point

Runs Occy (autonomous video production agent) independently on the D computer.
Does NOT need the VPS, Telegram bot, or Twitter. Shares safety infrastructure
(KillSwitch, AuditLog, TokenBudget).

Usage:
    python occy_main.py                    # Headless, Gemini Flash (default)
    python occy_main.py --visible          # Visible browser (for manual login / debugging)
    python occy_main.py --explore 60       # Run 60-minute exploration session
    python occy_main.py --hands-on 60      # Run 60-minute hands-on session (spends credits)
    python occy_main.py --hands-on 60 --budget 200  # Hands-on with 200 credit budget
    python occy_main.py --auto             # Auto-progress: explore → hands-on → production
    python occy_main.py --llm gemini       # Use Gemini Flash (~1-3s/action, default)
    python occy_main.py --llm sonnet       # Use Claude Sonnet (~8-12s/action, escalates to Opus)
    python occy_main.py --llm opus         # Use Claude Opus (~15-25s/action, most capable)
    python occy_main.py --llm ollama       # Use local Ollama (~2-4s/action, free)
    python occy_main.py --status           # Print current status and exit

Escalation chain: gemini/ollama → sonnet → opus (automatic on failure)

Environment:
    Requires .env file with:
    - GOOGLE_API_KEY (for Gemini browser agent + video review)
    - ANTHROPIC_API_KEY (only if using --llm sonnet or opus)
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

# Browser-use event bus timeouts — default 30s is too tight for cold starts
os.environ.setdefault("TIMEOUT_BrowserStartEvent", "120")
os.environ.setdefault("TIMEOUT_BrowserLaunchEvent", "120")

from agents.occy_agent import OccyAgent
from core.audit_log import AuditLog
from core.kill_switch import KillSwitch
from core.model_router import ModelRouter
from core.token_budget import TokenBudgetManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/occy.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("occy")


class OccySystem:
    """
    Standalone system for Occy agent.

    Mirrors DavidSystem's safety patterns but runs independently:
    - Own KillSwitch (shares the file-based mechanism)
    - Own AuditLog (separate DB)
    - Own TokenBudget (separate project budget)
    - No Telegram bot (yet — Phase 2 will add it)
    """

    def __init__(self, headless: bool = True, llm_provider: str = "gemini"):
        # Ensure data directory exists
        Path("data").mkdir(exist_ok=True)

        # Safety infrastructure
        self.kill_switch = KillSwitch()
        self.audit_log = AuditLog(db_path="data/occy_audit.db")
        self.token_budget = TokenBudgetManager(db_path="data/occy_budget.db")

        # Set Occy's budget (separate from David's)
        self.token_budget.set_budget("occy", daily=5.00, monthly=100.00)

        # Model router for knowledge distillation
        self.model_router = ModelRouter()

        # The agent
        self.agent = OccyAgent(
            kill_switch=self.kill_switch,
            audit_log=self.audit_log,
            token_budget=self.token_budget,
            model_router=self.model_router,
            headless=headless,
            llm_provider=llm_provider,
        )

        # Event loop reference (for heartbeat)
        self._loop = None

    async def start(self):
        """Start Occy system."""
        logger.info("=" * 60)
        logger.info("OCCY — VIDEO PRODUCTION AGENT — STARTING")
        logger.info("=" * 60)

        # Check kill switch
        if self.kill_switch.is_active:
            reason = self.kill_switch.get_reason()
            logger.warning(f"Kill switch is active: {reason}")
            logger.warning("Deactivate kill switch to start Occy")
            return

        # Start agent
        self.audit_log.log("occy", "info", "system", "Occy system starting")

        success = await self.agent.start()
        if not success:
            logger.error("Failed to start Occy agent")
            self.audit_log.log(
                "occy", "reject", "system",
                "Occy failed to start",
                success=False,
            )
            return

        logger.info("Occy system online.")

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
        """Start Occy, run exploration, then stop."""
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

    async def start_hands_on(
        self, duration_minutes: int = 60, credit_budget: int = 100,
    ):
        """Start Occy, run hands-on learning, then stop."""
        logger.info(
            f"Running {duration_minutes}-minute hands-on session "
            f"(budget: {credit_budget} credits)"
        )

        success = await self.agent.start()
        if not success:
            logger.error("Failed to start — cannot run hands-on")
            return

        try:
            result = await self.agent.run_hands_on(duration_minutes, credit_budget)
            logger.info(f"Hands-on complete: {json.dumps(result, indent=2)}")
        finally:
            await self.agent.stop()

    async def start_auto_session(self):
        """
        Auto-progression session: explore → hands-on → production.

        Checks learning progress and runs the appropriate phase:
        1. If features under 0.5 confidence exist → exploration
        2. If features between 0.5-0.7 exist → hands-on learning
        3. Otherwise → poll job queue for production work
        """
        logger.info("Starting auto-progression session")

        success = await self.agent.start()
        if not success:
            logger.error("Failed to start — cannot run auto session")
            return

        try:
            progress = self.agent.get_learning_progress()
            logger.info(f"Current progress: {json.dumps(progress, indent=2)}")

            # Phase 1: Exploration (if unexplored features remain)
            if progress["explored"] < progress["total_features"]:
                logger.info(
                    f"Phase 1 — Exploration: "
                    f"{progress['explored']}/{progress['total_features']} explored"
                )
                result = await self.agent.run_exploration(duration_minutes=120)
                logger.info(f"Exploration result: {json.dumps(result, indent=2)}")

            # Phase 2: Hands-on (if explored but not proficient)
            if progress["proficient"] < progress["explored"]:
                logger.info(
                    f"Phase 2 — Hands-on: "
                    f"{progress['proficient']}/{progress['explored']} proficient"
                )
                result = await self.agent.run_hands_on(
                    duration_minutes=120, credit_budget=100,
                )
                logger.info(f"Hands-on result: {json.dumps(result, indent=2)}")

            # Phase 3: Idle / production
            else:
                logger.info("Phase 3 — All features proficient. Ready for production.")

        finally:
            await self.agent.stop()

    async def start_test_clip(self, prompt: str = None):
        """Start Occy, produce one test clip, then stop."""
        logger.info("Running test clip production")
        success = await self.agent.start()
        if not success:
            logger.error("Failed to start — cannot produce test clip")
            return
        try:
            result = await self.agent.produce_test_clip(prompt)
            logger.info(f"Test clip result: {json.dumps(result, indent=2)}")
            if result.get("success"):
                logger.info(f"SUCCESS — Video saved to: {result['video_path']}")
            else:
                logger.error(f"FAILED — {result.get('error')}")
        finally:
            await self.agent.stop()

    async def print_status(self):
        """Print current status and exit."""
        status = self.agent.get_status()
        print(json.dumps(status, indent=2))

    async def stop(self):
        """Graceful shutdown."""
        logger.info("Occy system shutting down...")
        self.audit_log.log("occy", "info", "system", "Occy system stopping")
        await self.agent.stop()
        logger.info("Occy system stopped.")

    async def _heartbeat(self):
        """Update status file and systemd watchdog."""
        status_file = Path("data/occy_status.json")
        status_data = {
            "online": True,
            "agent": "Occy",
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
        description="Occy — Autonomous Video Production Agent"
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
        "--hands-on", type=int, metavar="MINUTES", dest="hands_on",
        help="Run a hands-on learning session for N minutes (spends credits)"
    )
    parser.add_argument(
        "--budget", type=int, default=100,
        help="Credit budget for hands-on session (default: 100)"
    )
    parser.add_argument(
        "--auto", action="store_true",
        help="Auto-progress: explore → hands-on → production"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Print current status and exit"
    )
    parser.add_argument(
        "--test-clip", action="store_true", dest="test_clip",
        help="Produce a single test video clip and exit (fast end-to-end test)"
    )
    parser.add_argument(
        "--prompt", type=str, default=None,
        help="Custom prompt for --test-clip (default: 'A person walking through a park')"
    )
    parser.add_argument(
        "--llm", choices=["gemini", "sonnet", "opus", "ollama"],
        default="gemini",
        help="LLM provider: gemini (fast, default), sonnet (reliable), opus (most capable), ollama (local/free)"
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    headless = not args.visible

    system = OccySystem(headless=headless, llm_provider=args.llm)

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

    if args.test_clip:
        await system.start_test_clip(args.prompt)
        return

    if args.status:
        await system.print_status()
        return

    if args.explore:
        await system.start_exploration(args.explore)
        return

    if args.hands_on:
        await system.start_hands_on(args.hands_on, args.budget)
        return

    if args.auto:
        await system.start_auto_session()
        return

    # Default: run as persistent service
    try:
        await system.start()
    except KeyboardInterrupt:
        await system.stop()


if __name__ == "__main__":
    asyncio.run(main())

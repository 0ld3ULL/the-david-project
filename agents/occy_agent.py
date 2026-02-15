"""
Occy Agent — Main orchestrator for autonomous video production.

Ties together all Occy subsystems:
- FocalBrowser: browser automation for Focal ML
- OccyLearner: systematic feature exploration
- OccyProducer: job-driven video production pipeline
- OccyReviewer: quality assessment via Gemini
- KnowledgeStore: permanent knowledge base
- EventStore: event memory with decay

This agent runs independently on the D computer (ASUS ROG laptop).
It does NOT need the VPS, Telegram bot, or Twitter tool from main.py.
It shares safety infrastructure (KillSwitch, AuditLog, ApprovalQueue).
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from core.audit_log import AuditLog
from core.kill_switch import KillSwitch
from core.memory.knowledge_store import KnowledgeStore
from core.memory.event_store import EventStore
from core.token_budget import TokenBudgetManager
from personality.occy import OccyPersonality

logger = logging.getLogger(__name__)


class OccyAgent:
    """
    Main orchestrator for Occy — autonomous video production specialist.

    Lazy-loads sub-components on first use. Can operate in three modes:
    - Exploration: learning Focal ML features systematically
    - Production: executing video production jobs
    - Idle: waiting for commands (checking job queue periodically)
    """

    def __init__(
        self,
        kill_switch: KillSwitch,
        audit_log: AuditLog,
        token_budget: TokenBudgetManager,
        model_router=None,
        approval_queue=None,
        headless: bool = True,
        llm_provider: str = "gemini",
    ):
        # Safety infrastructure (shared with main system)
        self.kill_switch = kill_switch
        self.audit_log = audit_log
        self.token_budget = token_budget
        self.model_router = model_router
        self.approval_queue = approval_queue
        self._llm_provider = llm_provider

        # Personality
        self.personality = OccyPersonality()

        # Knowledge stores (separate DBs from David's)
        self.knowledge = KnowledgeStore(db_path=Path("data/occy_knowledge.db"))
        self.events = EventStore(db_path=Path("data/occy_events.db"))

        # Sub-components (lazy-loaded)
        self._browser = None
        self._learner = None
        self._producer = None
        self._reviewer = None
        self._monitor = None
        self._headless = headless

        # State
        self._running = False
        self._mode = "idle"  # idle / exploring / producing

        logger.info(f"{self.personality.name} ({self.personality.role}) initialized")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> bool:
        """
        Start Occy agent.

        Launches browser and verifies Focal ML access.
        Returns True if ready to operate.
        """
        if self.kill_switch.is_active:
            logger.warning("Kill switch active — Occy will not start")
            return False

        logger.info("Starting Occy agent...")

        # Start browser
        browser = await self._get_browser()
        if not browser:
            logger.error("Failed to start browser")
            return False

        # Check Focal login
        logged_in = await browser.check_login()
        if not logged_in:
            if self._headless:
                logger.error(
                    "Not logged in to Focal ML. Run with --visible flag "
                    "and log in manually first."
                )
                return False
            else:
                logger.warning(
                    "Not logged in to Focal ML. Browser is visible — "
                    "please log in manually. Occy will wait up to 5 minutes."
                )
                # Wait for manual login — poll every 30 seconds for 5 minutes
                for attempt in range(10):
                    logger.info(
                        f"Waiting for manual login... "
                        f"({(attempt + 1) * 30}s / 300s)"
                    )
                    await asyncio.sleep(30)
                    logged_in = await browser.check_login()
                    if logged_in:
                        break

                if not logged_in:
                    logger.error(
                        "Login timeout — no manual login detected after 5 minutes. "
                        "Please run again and log in to Focal ML in the browser window."
                    )
                    return False

        self._running = True

        self.audit_log.log(
            "occy", "info", "system",
            "Occy agent started",
            details=f"mode={'headless' if self._headless else 'visible'}, login={'ok' if logged_in else 'pending'}",
        )

        # Record event
        self.events.add(
            title="Occy agent started",
            summary=f"Started in {'headless' if self._headless else 'visible'} mode",
            significance=3,
            category="system",
        )

        return True

    async def stop(self):
        """Graceful shutdown — save state and close browser."""
        logger.info("Stopping Occy agent...")
        self._running = False
        self._mode = "idle"

        if self._browser:
            await self._browser.stop()
            self._browser = None

        self.audit_log.log("occy", "info", "system", "Occy agent stopped")
        logger.info("Occy agent stopped")

    def get_status(self) -> dict:
        """Get current agent status."""
        status = {
            "agent": self.personality.name,
            "role": self.personality.role,
            "running": self._running,
            "mode": self._mode,
            "kill_switch": self.kill_switch.is_active,
            "browser_active": self._browser is not None and self._browser._running,
        }

        # Add knowledge stats
        status["knowledge"] = self.knowledge.get_stats()

        # Add learning progress if learner initialized
        if self._learner:
            status["learning_progress"] = self._learner.get_progress()

        # Add job queue if producer initialized
        if self._producer:
            status["job_queue"] = self._producer.get_queue_status()

        return status

    # ------------------------------------------------------------------
    # Sub-component access (lazy loading)
    # ------------------------------------------------------------------

    async def _get_browser(self):
        """Get or create the browser instance."""
        if self._browser is None:
            from agents.occy_browser import FocalBrowser
            self._browser = FocalBrowser(
                headless=self._headless,
                llm_provider=self._llm_provider,
            )
            success = await self._browser.start()
            if not success:
                self._browser = None
                return None
        return self._browser

    def _get_learner(self):
        """Get or create the learner instance."""
        if self._learner is None:
            from agents.occy_learner import OccyLearner
            self._learner = OccyLearner(
                browser=self._browser,
                knowledge_store=self.knowledge,
                audit_log=self.audit_log,
                model_router=self.model_router,
            )
        return self._learner

    def _get_reviewer(self):
        """Get or create the reviewer instance."""
        if self._reviewer is None:
            from agents.occy_reviewer import OccyReviewer
            self._reviewer = OccyReviewer(knowledge_store=self.knowledge)
        return self._reviewer

    def _get_producer(self):
        """Get or create the producer instance."""
        if self._producer is None:
            from agents.occy_producer import OccyProducer
            self._producer = OccyProducer(
                browser=self._browser,
                reviewer=self._get_reviewer(),
                knowledge_store=self.knowledge,
                approval_queue=self.approval_queue,
                audit_log=self.audit_log,
            )
        return self._producer

    def _get_monitor(self):
        """Get or create the screen monitor — Occy's persistent eyes."""
        if self._monitor is None:
            from agents.occy_screen_monitor import ScreenMonitor
            self._monitor = ScreenMonitor(
                browser=self._browser,
                check_interval=10.0,
            )
        return self._monitor

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    async def run_exploration(self, duration_minutes: int = 30) -> dict:
        """
        Run an exploration session.

        Occy explores Focal ML features systematically for the given duration.
        """
        if self.kill_switch.is_active:
            return {"error": "Kill switch active"}

        if not self._running:
            return {"error": "Agent not started"}

        self._mode = "exploring"
        logger.info(f"Starting {duration_minutes}-minute exploration session")

        try:
            learner = self._get_learner()
            result = await learner.run_exploration_session(duration_minutes)

            self.events.add(
                title=f"Exploration session: {result['features_explored']} features",
                summary=(
                    f"Explored {result['features_explored']} features, "
                    f"added {result['knowledge_entries']} knowledge entries, "
                    f"used {result['total_credits']} credits"
                ),
                significance=4,
                category="learning",
            )

            return result

        except Exception as e:
            logger.error(f"Exploration failed: {e}")
            self.audit_log.log(
                "occy", "reject", "exploration",
                f"Exploration session failed: {e}",
                success=False,
            )
            return {"error": str(e)}
        finally:
            self._mode = "idle"

    async def run_hands_on(
        self, duration_minutes: int = 60, credit_budget: int = 100,
    ) -> dict:
        """
        Run a hands-on learning session.

        Occy actually USES generative features — spending credits to
        create real content, measuring costs, and reviewing quality.
        """
        if self.kill_switch.is_active:
            return {"error": "Kill switch active"}

        if not self._running:
            return {"error": "Agent not started"}

        self._mode = "hands_on"
        logger.info(
            f"Starting {duration_minutes}-minute hands-on session "
            f"(budget: {credit_budget} credits)"
        )

        try:
            learner = self._get_learner()
            result = await learner.run_hands_on_session(
                duration_minutes, credit_budget
            )

            self.events.add(
                title=f"Hands-on session: {result['features_tested']} features tested",
                summary=(
                    f"Tested {result['features_tested']} features, "
                    f"spent {result['total_credits_spent']}/{result['credit_budget']} credits"
                ),
                significance=5,
                category="learning",
            )

            return result

        except Exception as e:
            logger.error(f"Hands-on session failed: {e}")
            self.audit_log.log(
                "occy", "reject", "hands_on",
                f"Hands-on session failed: {e}",
                success=False,
            )
            return {"error": str(e)}
        finally:
            self._mode = "idle"

    async def submit_job(
        self,
        title: str,
        description: str = "",
        script: str = "",
        model: str = "auto",
        duration_seconds: int = 30,
    ) -> dict:
        """
        Submit a new video production job.

        Creates the job, generates a production plan, and submits
        for approval. Returns job details.
        """
        if self.kill_switch.is_active:
            return {"error": "Kill switch active"}

        producer = self._get_producer()

        # Create job
        job_id = producer.create_job(
            title=title,
            description=description,
            script=script,
            model=model,
            duration_seconds=duration_seconds,
        )

        # Create production plan
        plan = await producer.create_production_plan(job_id)

        # Submit for approval
        approval_id = await producer.submit_for_approval(job_id)

        return {
            "job_id": job_id,
            "approval_id": approval_id,
            "plan": plan,
            "status": "planned — awaiting approval",
        }

    async def execute_approved_job(self, job_id: int) -> dict:
        """
        Execute an approved production job.

        Full pipeline: produce → review → re-render if needed → deliver.
        """
        if self.kill_switch.is_active:
            return {"error": "Kill switch active"}

        if not self._running:
            return {"error": "Agent not started"}

        self._mode = "producing"
        logger.info(f"Executing production job #{job_id}")

        try:
            producer = self._get_producer()
            result = await producer.produce_video(job_id)

            # Record event
            if result["success"]:
                self.events.add(
                    title=f"Video delivered: job #{job_id}",
                    summary=(
                        f"Quality: {result['quality_score']:.1f}/10, "
                        f"Attempts: {result['attempts']}, "
                        f"Credits: {result['credits_used']}"
                    ),
                    significance=6,
                    category="production",
                )
            else:
                self.events.add(
                    title=f"Video production failed: job #{job_id}",
                    summary=result.get("error", "Unknown error"),
                    significance=5,
                    category="production",
                )

            return result

        except Exception as e:
            logger.error(f"Production failed: {e}")
            return {"error": str(e)}
        finally:
            self._mode = "idle"

    async def produce_test_clip(self, prompt: str = None) -> dict:
        """
        Produce a single test video clip — bypasses job queue for quick testing.

        Uses the ScreenMonitor to stay engaged with Focal ML's chat-based
        workflow. Instead of fire-and-forget, Occy watches the screen and
        responds to Focal's AI questions (confirmations, options, etc).

        Run with --visible to watch and debug.
        """
        if not self._running:
            return {"error": "Agent not started — call start() first"}

        browser = self._browser
        if not browser:
            return {"error": "No browser available"}

        self._mode = "producing"
        test_prompt = prompt or "A person walking through a park on a sunny day"
        monitor = self._get_monitor()

        try:
            # Step 1: Check credits
            credits_before = await browser.get_credit_balance()
            logger.info(f"Credits before: {credits_before}")

            # Step 2: Enter prompt on the home page
            logger.info("Step 1: Entering prompt...")
            result = await browser.run_task(
                f"You are on the Focal ML home page (focalml.com). "
                f"Find the main text input area in the center — it has a "
                f"placeholder like 'Make a video about...' or similar. "
                f"Click on it and type:\n\n{test_prompt}\n\n"
                f"Then click the arrow/submit button to start.",
                max_steps=15,
            )
            if not result["success"]:
                await browser.take_screenshot("test_clip_fail_prompt")
                return {"error": "Failed to enter prompt", "details": result.get("result")}
            await browser.take_screenshot("test_clip_01_prompt_entered")

            # Step 3: Monitor and interact with Focal's AI
            # This is the key change — instead of passive waiting, Occy
            # watches the screen and responds to Focal's questions.
            logger.info("Step 2: Monitoring screen — responding to Focal AI...")
            monitor.set_context(
                "trying to generate a video on Focal ML. I just entered a "
                "prompt and the Focal AI agent may ask me questions about "
                "the video (style, duration, confirmation). I want to "
                "approve/confirm everything and get the video generated "
                "with the cheapest settings possible."
            )

            render_result = await monitor.wait_with_monitoring(
                timeout_seconds=300,
            )

            if not render_result["completed"]:
                await browser.take_screenshot("test_clip_fail_render")
                logger.warning(
                    f"Generation incomplete after {render_result['duration_seconds']:.0f}s, "
                    f"{render_result['interactions']} interactions handled"
                )
                # Even if it timed out, Focal may have finished but the
                # completion text didn't match — try to download anyway
                if render_result["interactions"] > 0:
                    logger.info("Had interactions — checking if video is available anyway...")
                else:
                    return {
                        "error": "Generation failed or timed out",
                        "details": render_result,
                    }

            await browser.take_screenshot("test_clip_02_complete")
            logger.info(
                f"Step 2 done: {render_result.get('interactions', 0)} interactions, "
                f"{render_result.get('duration_seconds', 0):.0f}s elapsed"
            )

            # Step 4: Export and download
            logger.info("Step 3: Exporting...")
            video_path = await browser.download_video(filename="test_clip.mp4")

            # Step 5: Measure credit cost
            credits_after = await browser.get_credit_balance()
            credits_spent = 0
            if credits_before and credits_after:
                credits_spent = max(0, credits_before - credits_after)

            logger.info(
                f"Test clip complete: credits_spent={credits_spent}, "
                f"video_path={video_path}"
            )

            return {
                "success": video_path is not None,
                "video_path": str(video_path) if video_path else None,
                "credits_spent": credits_spent,
                "render_time": render_result.get("duration_seconds", 0),
                "interactions": render_result.get("interactions", 0),
            }

        except Exception as e:
            logger.error(f"Test clip failed: {e}")
            return {"error": str(e)}
        finally:
            self._mode = "idle"

    async def take_screenshot(self, name: str = "manual") -> str | None:
        """Take a screenshot of the current browser state."""
        browser = await self._get_browser()
        if browser:
            path = await browser.take_screenshot(name)
            return str(path) if path else None
        return None

    async def get_credit_balance(self) -> int | None:
        """Get current Focal ML credit balance."""
        if self._browser and self._browser._running:
            return await self._browser.get_credit_balance()
        return None

    def get_learning_progress(self) -> dict:
        """Get learning progress summary."""
        learner = self._get_learner()
        return learner.get_progress()

    def get_job_queue(self) -> dict:
        """Get job queue status."""
        producer = self._get_producer()
        return producer.get_queue_status()

    # ------------------------------------------------------------------
    # Command handler (for Telegram integration)
    # ------------------------------------------------------------------

    async def handle_command(self, command: str, args: str = "") -> str:
        """
        Handle commands from Telegram or other interfaces.

        Commands:
            status — Current agent status
            explore <minutes> — Start exploration session
            job <description> — Submit a new production job
            produce <job_id> — Execute an approved job
            screenshot — Take a screenshot
            credits — Check credit balance
            progress — Learning progress
            queue — Job queue status
        """
        command = command.lower().strip()

        if command == "status":
            status = self.get_status()
            return json.dumps(status, indent=2)

        elif command == "explore":
            minutes = int(args) if args.strip().isdigit() else 30
            result = await self.run_exploration(minutes)
            return json.dumps(result, indent=2)

        elif command == "hands_on":
            # Parse: hands_on <minutes> <budget>
            parts = args.strip().split()
            minutes = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else 60
            budget = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 100
            result = await self.run_hands_on(minutes, budget)
            return json.dumps(result, indent=2)

        elif command == "job":
            if not args.strip():
                return "Usage: job <description of video to create>"
            result = await self.submit_job(title=args.strip()[:100], description=args.strip())
            return json.dumps(result, indent=2)

        elif command == "produce":
            if not args.strip().isdigit():
                return "Usage: produce <job_id>"
            result = await self.execute_approved_job(int(args.strip()))
            return json.dumps(result, indent=2)

        elif command == "screenshot":
            path = await self.take_screenshot(args.strip() or "manual")
            return f"Screenshot saved: {path}" if path else "Screenshot failed"

        elif command == "credits":
            balance = await self.get_credit_balance()
            return f"Credit balance: {balance}" if balance is not None else "Could not read balance"

        elif command == "progress":
            progress = self.get_learning_progress()
            return json.dumps(progress, indent=2)

        elif command == "costs":
            costs = self._learner.get_cost_sheet()
            if not costs:
                return "No cost data yet — need more hands-on testing."
            lines = ["Focal ML Cost Sheet (from real usage):", ""]
            for name, info in sorted(costs.items()):
                line = f"  {name}: ~{info['avg_credits']} credits"
                if info.get("avg_time_seconds"):
                    line += f", ~{info['avg_time_seconds']}s"
                line += f" ({info['samples']} samples)"
                lines.append(line)
            return "\n".join(lines)

        elif command == "queue":
            queue = self.get_job_queue()
            return json.dumps(queue, indent=2)

        else:
            return (
                "Occy commands:\n"
                "  status — Current agent status\n"
                "  explore [minutes] — Start exploration session\n"
                "  hands_on [minutes] [budget] — Hands-on learning (spend credits)\n"
                "  job <description> — Submit new video job\n"
                "  produce <job_id> — Execute approved job\n"
                "  screenshot [name] — Take screenshot\n"
                "  credits — Check Focal credit balance\n"
                "  costs — What things cost (from experience)\n"
                "  progress — Learning progress\n"
                "  queue — Job queue status"
            )

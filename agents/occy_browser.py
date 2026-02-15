"""
Focal ML Browser Controller — Occy's eyes and hands.

Wraps Browser Use to provide reliable browser automation for Focal ML.
Handles persistent login sessions, screenshots, and common Focal operations.

Architecture:
- FocalBrowser: low-level browser control (start, stop, navigate, screenshot)
- Focal-specific actions: higher-level operations (enter_script, select_model, etc.)
- Domain allowlist: restricted to focalml.com + approved domains only

Requires:
    pip install browser-use
    playwright install chromium
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Persistent browser profile directory
BROWSER_PROFILE_DIR = Path("data/occy_browser_profile")
SCREENSHOT_DIR = Path("data/occy_screenshots")
DOWNLOAD_DIR = Path("data/occy_downloads")

# Domain allowlist — Occy can ONLY visit these domains
ALLOWED_DOMAINS = [
    "focalml.com",
    "www.focalml.com",
    "app.focalml.com",
    "control.focalml.com",
    # Google OAuth domains — required for Focal ML login
    "accounts.google.com",
    "myaccount.google.com",
]

# Extended allowlist for Phase 4 (marketplace) — disabled by default
MARKETPLACE_DOMAINS = [
    "fiverr.com",
    "www.fiverr.com",
    "upwork.com",
    "www.upwork.com",
]



# Supported LLM providers for browser automation
LLM_PROVIDERS = {
    "gemini": "Gemini 2.5 Flash — fast (~1-3s/action), cheap, great vision",
    "sonnet": "Claude Sonnet — slower (~8-12s/action), most reliable",
    "opus": "Claude Opus — slowest (~15-25s/action), most capable",
    "ollama": "Local Ollama — free, needs GPU, ~2-4s/action",
}
# Escalation chain: gemini/ollama → sonnet → opus → (no further)
ESCALATION_TARGET = {
    "gemini": "sonnet",
    "ollama": "sonnet",
    "sonnet": "opus",
    "opus": None,  # Top tier — nowhere to escalate
}
DEFAULT_LLM_PROVIDER = "gemini"


class FocalBrowser:
    """
    Browser Use wrapper for Focal ML automation.

    Provides persistent browser sessions, screenshot capture, and
    domain-restricted navigation. First run requires manual login
    by Jono — cookies are saved to the profile directory for all
    future sessions.
    """

    def __init__(
        self,
        headless: bool = True,
        enable_marketplace: bool = False,
        llm_provider: str = DEFAULT_LLM_PROVIDER,
        ollama_model: str = "qwen2.5vl:7b",
    ):
        self.headless = headless
        self.browser = None
        self.page = None
        self._running = False
        self._connected = False  # Track browser connection health
        self._temp_profile = None  # Set if we fall back to temp profile
        self._llm_provider = llm_provider
        self._ollama_model = ollama_model
        self._llm = None  # Cached fast LLM instance
        self._smart_llm = None  # Cached escalation LLM (big brain)

        # Build domain allowlist
        self.allowed_domains = list(ALLOWED_DOMAINS)
        if enable_marketplace:
            self.allowed_domains.extend(MARKETPLACE_DOMAINS)

        # Ensure directories exist
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"LLM provider: {self._llm_provider} ({LLM_PROVIDERS.get(self._llm_provider, 'unknown')})")

    def _get_llm(self):
        """Get or create the LLM instance for browser automation."""
        if self._llm is not None:
            return self._llm

        if self._llm_provider == "gemini":
            from browser_use.llm import ChatGoogle
            self._llm = ChatGoogle(
                model="gemini-2.5-flash",
                api_key=os.environ.get("GOOGLE_API_KEY"),
                thinking_budget=0,  # Disable thinking — speed over reasoning
            )

        elif self._llm_provider == "ollama":
            from browser_use.llm import ChatOllama
            self._llm = ChatOllama(model=self._ollama_model)

        elif self._llm_provider == "opus":
            from browser_use.llm import ChatAnthropic
            self._llm = ChatAnthropic(
                model="claude-opus-4-6",
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )

        else:  # sonnet (default fallback)
            from browser_use.llm import ChatAnthropic
            self._llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )

        logger.info(f"LLM initialized: {self._llm_provider} ({self._llm.name})")
        return self._llm

    def _get_smart_llm(self):
        """Get or create the escalation LLM — next tier up from primary."""
        if self._smart_llm is not None:
            return self._smart_llm

        target = ESCALATION_TARGET.get(self._llm_provider)
        if not target:
            return None  # Already at top tier

        from browser_use.llm import ChatAnthropic
        if target == "opus":
            self._smart_llm = ChatAnthropic(
                model="claude-opus-4-6",
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )
        else:  # sonnet
            self._smart_llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )
        logger.info(f"Escalation LLM initialized: {target} ({self._smart_llm.name})")
        return self._smart_llm

    async def start(self) -> bool:
        """
        Launch browser with persistent profile.

        Falls back to a temp profile + saved storage state if the persistent
        profile is locked by another process (common on Windows after crashes).

        Returns True if browser started successfully and Focal is accessible.
        """
        try:
            from browser_use import Browser

            # Clean up stale lockfile from previous sessions — Chrome hangs
            # if it can't acquire the profile lock on startup
            use_persistent = True
            lockfile = BROWSER_PROFILE_DIR / "lockfile"
            if lockfile.exists():
                try:
                    lockfile.unlink()
                    logger.info("Removed stale browser lockfile")
                except OSError:
                    logger.warning(
                        "Lockfile held by another process — "
                        "falling back to temp profile with saved session"
                    )
                    use_persistent = False

            # Build Browser kwargs — the new API takes everything directly
            browser_kwargs = {
                "headless": self.headless,
                "allowed_domains": self.allowed_domains,
                "downloads_path": str(DOWNLOAD_DIR),
                "disable_security": False,
                "keep_alive": True,
            }

            if use_persistent:
                # Use persistent user data dir for cookie/session persistence
                # (don't combine with storage_state — causes warning spam)
                browser_kwargs["user_data_dir"] = str(BROWSER_PROFILE_DIR)
            else:
                # Profile locked — use temp dir with cookies from state.json
                # Don't pass both user_data_dir AND storage_state (warning spam)
                import tempfile
                self._temp_profile = Path(tempfile.mkdtemp(prefix="occy-browser-"))
                state_file = BROWSER_PROFILE_DIR / "state.json"
                if state_file.exists():
                    browser_kwargs["storage_state"] = str(state_file)
                    # Do NOT pass user_data_dir at all when using storage_state.
                    # Passing None makes browser-use create a default temp dir,
                    # then it warns about storage_state + user_data_dir conflict.
                    logger.info(f"Loading session from {state_file}")
                else:
                    browser_kwargs["user_data_dir"] = str(self._temp_profile)

            self.browser = Browser(**browser_kwargs)

            # Start the browser and get the page
            await self.browser.start()
            self.page = await self.browser.get_current_page()
            self._running = True
            self._connected = True

            logger.info(
                f"Browser started ({'headless' if self.headless else 'visible'} mode)"
            )
            return True

        except ImportError as e:
            logger.error(
                f"browser-use import failed: {e}. "
                "Run: pip install browser-use langchain-anthropic && playwright install chromium"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            return False

    async def stop(self):
        """Save session state and close browser."""
        if not self._running:
            return

        try:
            # Save session state for future runs
            if self.browser:
                try:
                    state = await self.browser.export_storage_state()
                    state_path = BROWSER_PROFILE_DIR / "state.json"
                    with open(state_path, "w") as f:
                        json.dump(state, f)
                    logger.info(f"Browser state saved to {state_path}")
                except Exception:
                    pass  # export_storage_state may not always work

                await self.browser.stop()

        except Exception as e:
            logger.error(f"Error during browser shutdown: {e}")
        finally:
            self._running = False
            self._connected = False
            self.browser = None
            self.page = None
            # Clean up temp profile if we used one
            if self._temp_profile and self._temp_profile.exists():
                import shutil
                try:
                    shutil.rmtree(self._temp_profile, ignore_errors=True)
                except Exception:
                    pass
                self._temp_profile = None
            logger.info("Browser stopped")

    async def dismiss_intercom(self):
        """Inject JS to hide the Intercom chat widget that blocks UI interaction."""
        try:
            page = await self.browser.get_current_page()
            await page.evaluate("""
                () => {
                    // Hide the Intercom container entirely
                    const container = document.getElementById('intercom-container');
                    if (container) container.style.display = 'none';
                    // Also hide the launcher button and frame
                    document.querySelectorAll(
                        '[class*="intercom"], iframe[name*="intercom"]'
                    ).forEach(el => el.style.display = 'none');
                }
            """)
        except Exception:
            pass  # Page may not have Intercom loaded yet

    @property
    def is_connected(self) -> bool:
        """Check if browser is running and connected."""
        return self._running and self._connected

    async def restart(self) -> bool:
        """
        Restart browser after a disconnect.

        Stops the old browser (ignoring errors), starts fresh,
        and re-verifies Focal ML login.

        Returns True if browser restarted and login is active.
        """
        logger.info("Restarting browser after disconnect...")

        # Force cleanup
        try:
            if self.browser:
                await self.browser.stop()
        except Exception:
            pass

        self._running = False
        self._connected = False
        self.browser = None
        self.page = None

        # Clean up temp profile
        if self._temp_profile and self._temp_profile.exists():
            import shutil
            try:
                shutil.rmtree(self._temp_profile, ignore_errors=True)
            except Exception:
                pass
            self._temp_profile = None

        # Brief pause before restarting
        await asyncio.sleep(3)

        # Start fresh
        success = await self.start()
        if not success:
            logger.error("Browser restart failed — could not start")
            return False

        # Re-verify login
        logged_in = await self.check_login()
        if not logged_in:
            logger.error("Browser restarted but Focal ML login lost")
            return False

        logger.info("Browser restarted successfully — Focal ML session active")
        return True

    async def check_login(self) -> bool:
        """
        Check if we have a valid Focal ML login session.

        Uses _run_agent directly (no escalation) because browser-use's
        simple judge often overrides the success flag on simple text
        responses, which would trigger unnecessary escalation.
        """
        if not self._running or not self.browser:
            return False

        try:
            llm = self._get_llm()
            result = await self._run_agent(
                "Navigate to https://focalml.com and check if you are logged in. "
                "Look for indicators like: a dashboard, projects list, credit balance, "
                "or a user profile icon. If you see a login/signup page instead, "
                "report 'NOT LOGGED IN'. If you see a dashboard or project interface, "
                "report 'LOGGED IN'. Return ONLY one of those two phrases.",
                llm,
                max_steps=5,
            )

            # Check the result text directly — browser-use's simple judge
            # sometimes overrides the success flag even when the task worked
            result_text = str(result.get("result") or "").upper()
            if "LOGGED IN" in result_text and "NOT LOGGED IN" not in result_text:
                logger.info("Focal ML login verified — session active")
                return True
            elif "NOT LOGGED IN" in result_text:
                logger.warning("Not logged in to Focal ML")
                return False

            logger.warning("Login check inconclusive")
            return False

        except Exception as e:
            logger.error(f"Login check failed: {e}")
            return False

    async def navigate(self, url: str) -> bool:
        """
        Navigate to a URL (domain-restricted).

        Returns True if navigation succeeded and domain is allowed.
        """
        if not self._running or not self.browser:
            logger.error("Browser not running")
            return False

        # Domain check
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.hostname or ""

        if domain and domain not in self.allowed_domains:
            logger.warning(f"Blocked navigation to disallowed domain: {domain}")
            return False

        try:
            result = await self.run_task(
                f"Navigate to {url} and confirm the page has loaded.",
                max_steps=3,
            )
            if result["success"]:
                logger.info(f"Navigated to: {url}")
                return True
            else:
                logger.error(f"Navigation failed: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False

    async def take_screenshot(self, name: str = None) -> Path | None:
        """
        Take a screenshot of the current page.

        Returns path to saved screenshot, or None on failure.
        """
        if not self._running or not self.browser:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png" if name else f"screenshot_{timestamp}.png"
        filepath = SCREENSHOT_DIR / filename

        try:
            page = await self.browser.get_current_page()
            await page.screenshot(path=str(filepath), full_page=False)
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return None

    # Error patterns that indicate the browser has disconnected
    _DISCONNECT_PATTERNS = [
        "browser not connected",
        "target may have detached",
        "no valid agent focus",
        "browser is in an unstable state",
        "cdp connected but failed",
    ]

    def _is_disconnect_error(self, error_text: str) -> bool:
        """Check if an error indicates browser disconnection."""
        error_lower = error_text.lower()
        return any(p in error_lower for p in self._DISCONNECT_PATTERNS)

    async def _run_agent(self, task: str, llm, max_steps: int) -> dict:
        """Run a single browser-use agent attempt with the given LLM."""
        from browser_use import Agent

        agent = Agent(
            task=task,
            llm=llm,
            browser=self.browser,
            max_actions_per_step=5,
        )

        history = await agent.run(max_steps=max_steps)

        # Check the history for disconnect errors
        result_text = str(history.final_result() or "")
        if self._is_disconnect_error(result_text):
            self._connected = False
            logger.warning("Browser disconnected during task execution")
            return {
                "success": False,
                "result": result_text,
                "steps_taken": len(history.history),
                "error": "Browser disconnected",
                "disconnected": True,
            }

        return {
            "success": history.is_done() and history.is_successful() is not False,
            "result": history.final_result(),
            "steps_taken": len(history.history),
            "error": None,
            "disconnected": False,
        }

    async def run_task(self, task: str, max_steps: int = 25) -> dict:
        """
        Run a Browser Use agent task on the current page.

        Uses the fast LLM first. If it fails, auto-escalates to the
        smart LLM (Sonnet) for a retry — then future tasks go back
        to the fast model.

        Args:
            task: Natural language description of what to do
            max_steps: Maximum number of browser actions

        Returns:
            dict with 'success', 'result', 'steps_taken', 'error',
            and 'disconnected' (True if browser connection was lost)
        """
        if not self._running or not self._connected:
            return {
                "success": False, "error": "Browser not connected",
                "steps_taken": 0, "disconnected": True,
            }

        try:
            # Dismiss Intercom chat widget before each task — it blocks UI
            await self.dismiss_intercom()

            # First attempt: fast model
            llm = self._get_llm()
            result = await self._run_agent(task, llm, max_steps)

            # If it worked or browser disconnected, return as-is
            if result["success"] or result.get("disconnected"):
                return result

            # Primary failed — escalate to next tier
            target = ESCALATION_TARGET.get(self._llm_provider)
            if not target:
                return result  # Already at top tier, nowhere to escalate

            logger.warning(
                f"Primary model failed ({self._llm_provider}) after {result['steps_taken']} steps — "
                f"escalating to {target}"
            )
            smart_llm = self._get_smart_llm()
            smart_result = await self._run_agent(task, smart_llm, max_steps)
            smart_result["escalated"] = True
            return smart_result

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Browser task failed: {error_msg}")

            # Detect disconnection from exception
            if self._is_disconnect_error(error_msg):
                self._connected = False
                logger.warning("Browser disconnected (detected from exception)")

            return {
                "success": False,
                "result": None,
                "steps_taken": 0,
                "error": error_msg,
                "disconnected": not self._connected,
            }

    async def get_page_text(self) -> str:
        """Get visible text content of the current page."""
        if not self._running or not self.browser:
            return ""
        try:
            page = await self.browser.get_current_page()
            return await page.inner_text("body")
        except Exception:
            return ""

    async def get_page_url(self) -> str:
        """Get current page URL."""
        if not self._running or not self.browser:
            return ""
        try:
            page = await self.browser.get_current_page()
            return page.url
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Focal ML — Specific Actions
    # ------------------------------------------------------------------

    async def create_or_open_project(self, project_name: str = None) -> bool:
        """Navigate to Focal ML and enter the editor workspace."""
        result = await self.run_task(
            "Navigate to https://focalml.com if not already there. "
            "You should see the home page with a left sidebar. "
            "Under 'PROJECTS', click 'Recent' to expand it if needed, "
            "then click on the FIRST project listed to open it. "
            "Wait for the editor to fully load — you'll see a timeline "
            "at the bottom of the screen and panels on the left side. "
            "If no recent projects exist, type 'A short test video' in "
            "the main text area and click the arrow button to create one, "
            "then follow any prompts until you reach the editor.",
            max_steps=20,
        )
        return result["success"]

    async def enter_script(self, text: str) -> bool:
        """Enter a script/prompt into Focal ML's project input."""
        return (await self.run_task(
            f"You are on the Focal ML home page. Find the main text input area "
            f"in the center of the page — it has a placeholder like "
            f"'Make a video about...' or similar. Click on it and type the "
            f"following text:\n\n{text}\n\n"
            f"After entering the text, click the arrow/submit button to the "
            f"right of the input to start creating the project.",
            max_steps=15,
        ))["success"]

    async def select_video_model(self, model_name: str) -> bool:
        """Select a video model in the Focal ML editor."""
        return (await self.run_task(
            f"You are in the Focal ML editor. Go to the Settings panel "
            f"(gear icon or 'Settings' in the left sidebar). Find the "
            f"'Video Model' dropdown and select '{model_name}'. "
            f"If you can't find Settings, look for a model selector "
            f"dropdown in the current view.",
            max_steps=15,
        ))["success"]

    async def confirm_and_start_generation(self, timeout_seconds: int = 120) -> dict:
        """
        Stay in Focal ML's chat conversation until video generation starts.

        Focal ML has an AI agent that proposes a video plan and asks for
        confirmation before generating. This method monitors the chat,
        confirms/approves whatever the AI suggests, and waits until
        actual generation begins (progress bar, 'generating', etc).

        Returns dict with 'success', 'result', 'error'.
        """
        start = datetime.now()

        # Phase 1: Respond to Focal's AI — confirm its plan
        result = await self.run_task(
            "You are in Focal ML's chat interface. The AI agent has proposed "
            "a video plan and is asking for your confirmation or input. "
            "READ what the AI is asking, then respond affirmatively. "
            "If it asks you to confirm, say 'Yes, go ahead' or click a "
            "'Confirm' / 'Yes' / 'Approve' button. "
            "If it asks for more details, say 'Looks good, please proceed'. "
            "If it presents options, pick the FIRST/DEFAULT option. "
            "If there's a 'Generate' button, click it. "
            "Keep responding to the AI until you see signs that video "
            "generation has actually STARTED — look for a progress bar, "
            "a 'Generating...' message, a spinning indicator, or a "
            "render queue status. "
            "Do NOT report success until generation has actually begun. "
            "If the AI asks multiple questions, answer them all.",
            max_steps=30,
        )

        if result["success"]:
            logger.info("Focal AI confirmed — generation appears to have started")
            return result

        # Phase 2: If first attempt didn't fully resolve, try once more
        elapsed = (datetime.now() - start).total_seconds()
        if elapsed < timeout_seconds:
            logger.info("Retrying confirmation — Focal AI may still be asking questions")
            result = await self.run_task(
                "You are in Focal ML's chat. The AI may still be asking "
                "questions or waiting for confirmation. Look at the chat "
                "and respond to whatever it's asking. Say 'Yes' or click "
                "'Confirm' / 'Generate'. If generation is already in "
                "progress (you see a progress bar or 'Generating...' text), "
                "report success. If the chat shows the AI is still waiting "
                "for your response, answer it and confirm.",
                max_steps=20,
            )

        return result

    async def chat_command(self, command: str) -> bool:
        """Send an edit command via Focal's chat interface."""
        return (await self.run_task(
            f"Find the chat/command input and type: {command}\n"
            f"Then press Enter to submit."
        ))["success"]

    async def create_character(self, config: dict) -> bool:
        """Create a new character in Focal ML."""
        name = config.get("name", "New Character")
        description = config.get("description", "")
        image_path = config.get("image_path", "")

        task = f"Navigate to the character creation section. Create a new character named '{name}'."
        if description:
            task += f" Set the description to: {description}"
        if image_path:
            task += f" Upload the reference image from: {image_path}"

        return (await self.run_task(task))["success"]

    async def wait_for_render(self, timeout_seconds: int = 600) -> dict:
        """
        Wait for a video render to complete.

        Polls the page for render completion indicators.
        Returns dict with 'completed', 'duration_seconds', 'error'.
        """
        start = datetime.now()
        poll_interval = 10  # Check every 10 seconds

        while (datetime.now() - start).total_seconds() < timeout_seconds:
            text = await self.get_page_text()
            text_lower = text.lower()

            # Check for completion indicators
            if any(ind in text_lower for ind in ["download", "render complete", "ready"]):
                duration = (datetime.now() - start).total_seconds()
                logger.info(f"Render complete in {duration:.0f}s")
                return {"completed": True, "duration_seconds": duration, "error": None}

            # Check for failure indicators
            if any(ind in text_lower for ind in ["render failed", "error", "insufficient credits"]):
                duration = (datetime.now() - start).total_seconds()
                logger.warning(f"Render failed after {duration:.0f}s")
                await self.take_screenshot("render_failed")
                return {"completed": False, "duration_seconds": duration, "error": "Render failed"}

            await asyncio.sleep(poll_interval)

        logger.warning(f"Render timed out after {timeout_seconds}s")
        await self.take_screenshot("render_timeout")
        return {"completed": False, "duration_seconds": timeout_seconds, "error": "Timeout"}

    async def get_credit_balance(self, retries: int = 2) -> int | None:
        """
        Read the current Focal ML credit balance from the UI.

        Both Gemini Flash and Sonnet frequently misread the balance as 0
        when it isn't. To compensate, we retry reads that return 0 and
        navigate to the home page first on retry to get a clean view.

        Returns credit count as integer, or None if couldn't read it.
        """
        import re

        for attempt in range(retries):
            prompt = (
                "You are on focalml.com. Find the credit balance number. "
                "It is displayed in the LEFT SIDEBAR, shown as a number "
                "(like '15247') next to the word 'Credits'. "
                "Look in the SIDEBAR on the left side of the page. "
            )
            if attempt > 0:
                # On retry, navigate home first for a clean page state
                prompt = (
                    "Navigate to https://focalml.com first, then look at the "
                    "LEFT SIDEBAR for the credit balance. It is a number "
                    "(like '15247') shown next to the word 'Credits'. "
                    "Read that number carefully. "
                )
            prompt += "Return ONLY the number."

            result = await self.run_task(prompt, max_steps=10)

            if result["success"] and result["result"]:
                numbers = re.findall(r'[\d,]+', str(result["result"]))
                if numbers:
                    try:
                        value = int(numbers[0].replace(",", ""))
                        if value > 0:
                            return value
                        # Got 0 — might be real or might be a misread.
                        # Retry to be sure.
                        if attempt < retries - 1:
                            logger.warning(
                                f"Credit balance read as 0 (attempt {attempt + 1}) "
                                f"— retrying with navigation"
                            )
                            continue
                        # All retries returned 0 — it's probably real
                        return 0
                    except ValueError:
                        pass

        logger.warning("Could not read credit balance after %d attempts", retries)
        return None

    async def download_video(self, filename: str = None) -> Path | None:
        """
        Export and download the video from Focal ML.

        Returns path to downloaded file, or None on failure.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"focal_video_{timestamp}.mp4"

        download_path = DOWNLOAD_DIR / filename

        result = await self.run_task(
            "You are in the Focal ML editor. Click the 'Export' button "
            "(bottom right of the timeline area). A modal/dialog should appear. "
            "Select 16:9 aspect ratio if prompted. Then click the 'Publish' or "
            "'Export' button in the dialog to start rendering. "
            "Wait for the rendering to complete — you may see a progress bar. "
            "Once done, look for a 'Download' option, a three-dot menu with "
            "'Download', or a 'View Video' link. Click to download the video.",
            max_steps=25,
        )

        if result["success"]:
            # Browser Use handles downloads through the browser's download path
            # We need to check if the file appeared
            await asyncio.sleep(5)  # Give download time to start

            # Check downloads directory for recent files
            if download_path.exists():
                logger.info(f"Video downloaded: {download_path}")
                return download_path

            # Check for any recent MP4 in downloads
            for f in sorted(DOWNLOAD_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
                if (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() < 60:
                    logger.info(f"Video found in downloads: {f}")
                    return f

        logger.warning("Video download failed or file not found")
        return None

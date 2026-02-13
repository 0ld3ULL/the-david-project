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
]

# Extended allowlist for Phase 4 (marketplace) — disabled by default
MARKETPLACE_DOMAINS = [
    "fiverr.com",
    "www.fiverr.com",
    "upwork.com",
    "www.upwork.com",
]


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
    ):
        self.headless = headless
        self.browser = None
        self.page = None
        self._running = False
        self._connected = False  # Track browser connection health
        self._temp_profile = None  # Set if we fall back to temp profile

        # Build domain allowlist
        self.allowed_domains = list(ALLOWED_DOMAINS)
        if enable_marketplace:
            self.allowed_domains.extend(MARKETPLACE_DOMAINS)

        # Ensure directories exist
        BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

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

        Uses a browser-use Agent task to navigate and check login state,
        since the CDP page object doesn't support Playwright-style methods.
        """
        if not self._running or not self.browser:
            return False

        try:
            result = await self.run_task(
                "Navigate to https://focalml.com and check if you are logged in. "
                "Look for indicators like: a dashboard, projects list, credit balance, "
                "or a user profile icon. If you see a login/signup page instead, "
                "report 'NOT LOGGED IN'. If you see a dashboard or project interface, "
                "report 'LOGGED IN'. Return ONLY one of those two phrases.",
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

    async def run_task(self, task: str, max_steps: int = 25) -> dict:
        """
        Run a Browser Use agent task on the current page.

        This is the main entry point for autonomous browser interaction.
        Browser Use's Agent sees the screen, decides what to click/type,
        and executes the task step by step.

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
            from browser_use import Agent
            from browser_use.llm import ChatAnthropic

            # Use browser-use's own ChatAnthropic (not langchain's —
            # browser-use requires a .provider property that langchain lacks)
            llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                api_key=os.environ.get("ANTHROPIC_API_KEY"),
            )

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

    async def enter_script(self, text: str) -> bool:
        """Paste a script into Focal ML's editor."""
        return (await self.run_task(
            f"Find the script/prompt input area and paste the following text into it:\n\n{text}"
        ))["success"]

    async def select_video_model(self, model_name: str) -> bool:
        """Select a specific video generation model."""
        return (await self.run_task(
            f"Find the video model selector and choose '{model_name}'. "
            f"Click on it to confirm the selection."
        ))["success"]

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

    async def get_credit_balance(self) -> int | None:
        """
        Read the current Focal ML credit balance from the UI.

        Returns credit count as integer, or None if couldn't read it.
        """
        result = await self.run_task(
            "You are on focalml.com. Find the credit balance display "
            "(it shows 'X Credits' in the left sidebar or header). "
            "If you're not on focalml.com, navigate there first. "
            "Read the credit number and report it. Return ONLY the number.",
            max_steps=10,
        )

        if result["success"] and result["result"]:
            # Try to extract a number from the result
            import re
            numbers = re.findall(r'[\d,]+', str(result["result"]))
            if numbers:
                try:
                    return int(numbers[0].replace(",", ""))
                except ValueError:
                    pass

        logger.warning("Could not read credit balance")
        return None

    async def download_video(self, filename: str = None) -> Path | None:
        """
        Download the most recently rendered video.

        Returns path to downloaded file, or None on failure.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"focal_video_{timestamp}.mp4"

        download_path = DOWNLOAD_DIR / filename

        result = await self.run_task(
            "Find the download button for the rendered video and click it. "
            "Wait for the download to start."
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

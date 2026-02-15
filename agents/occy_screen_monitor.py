"""
Occy Screen Monitor — Persistent visual awareness for browser automation.

Gives Occy the ability to "keep an eye" on what's happening in the browser,
just like a human glances at Discord or keeps a phone on a stand.

Architecture:
    - DOM MutationObserver: watches for new elements in key page areas
      (chat messages, dialogs, notifications, error banners)
    - Event-driven: Occy doesn't stare — he gets notified when something
      changes, THEN looks (takes a screenshot + analyzes with Vision)
    - Brain loop: screenshot → Gemini Vision → decide → act → back to watching

This is the missing piece between "fire a browser-use task" and
"wait passively for render." Occy can now participate in conversations
with AI agents inside websites (like Focal ML's chat-based workflow).

Usage:
    monitor = ScreenMonitor(browser, on_question=handle_question)
    await monitor.start()         # Start watching
    ...                           # Occy does other things
    await monitor.stop()          # Stop watching

    # Or use as a context manager:
    async with monitor.watching():
        await some_long_operation()
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("data/occy_screenshots")


class ScreenMonitor:
    """
    Occy's persistent eyes — monitors the browser for things that need attention.

    Think of it like:
    - Discord open on a second screen (DOM watcher on the chat area)
    - iPhone with audible notifications (event callback when things change)
    - Glancing across when you hear a ding (screenshot + Vision analysis)
    - Reading the message and replying (decide + act via browser)
    """

    def __init__(
        self,
        browser,
        on_interaction_needed: Callable = None,
        check_interval: float = 5.0,
        vision_model: str = "gemini",
    ):
        """
        Args:
            browser: FocalBrowser instance (has .browser, .run_task(), etc.)
            on_interaction_needed: async callback(event_dict) when user action needed
            check_interval: seconds between lightweight DOM checks (fallback)
            vision_model: which model to use for screenshot analysis
        """
        self.browser = browser
        self._on_interaction = on_interaction_needed
        self._check_interval = check_interval
        self._vision_model = vision_model

        self._watching = False
        self._watch_task = None
        self._last_chat_count = 0
        self._last_page_text_hash = None
        self._context = ""  # What Occy is currently doing (for Vision prompts)

        # Track what we've seen to avoid reacting to the same thing twice
        self._handled_messages = set()

    def set_context(self, context: str):
        """Tell the monitor what Occy is currently doing, for smarter analysis."""
        self._context = context

    async def start(self):
        """Start monitoring the browser."""
        if self._watching:
            return

        self._watching = True
        self._watch_task = asyncio.create_task(self._monitor_loop())
        logger.info("Screen monitor started — watching for interactions")

    async def stop(self):
        """Stop monitoring."""
        self._watching = False
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None
        logger.info("Screen monitor stopped")

    @asynccontextmanager
    async def watching(self, context: str = ""):
        """Context manager — monitor while doing something else."""
        if context:
            self.set_context(context)
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    # ------------------------------------------------------------------
    # The core monitoring loop
    # ------------------------------------------------------------------

    async def _monitor_loop(self):
        """
        Main monitoring loop — lightweight checks with smart escalation.

        Level 1: Check if page text changed (cheap — no API calls)
        Level 2: If changed, analyze what happened (screenshot + Vision)
        Level 3: If interaction needed, call the handler
        """
        while self._watching:
            try:
                change = await self._detect_change()

                if change["changed"]:
                    logger.info(
                        f"Screen change detected: {change['reason']}"
                    )

                    # Something changed — analyze what's going on
                    event = await self._analyze_screen()

                    if event and event.get("needs_interaction"):
                        logger.info(
                            f"Interaction needed: {event.get('description', '?')}"
                        )

                        # Either use the callback or auto-respond
                        if self._on_interaction:
                            await self._on_interaction(event)
                        else:
                            await self._auto_respond(event)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

            await asyncio.sleep(self._check_interval)

    # ------------------------------------------------------------------
    # Level 1: Lightweight change detection (no API calls)
    # ------------------------------------------------------------------

    async def _detect_change(self) -> dict:
        """
        Quick check: did the page change since last time we looked?

        Uses page text hash — no API calls, very cheap.
        Returns dict with 'changed' bool and 'reason' string.
        """
        if not self.browser or not self.browser.is_connected:
            return {"changed": False, "reason": "browser disconnected"}

        try:
            text = await self.browser.get_page_text()
            text_hash = hash(text)

            if self._last_page_text_hash is None:
                # First check — establish baseline
                self._last_page_text_hash = text_hash
                return {"changed": False, "reason": "baseline established"}

            if text_hash != self._last_page_text_hash:
                self._last_page_text_hash = text_hash

                # Quick heuristics: what kind of change?
                text_lower = text.lower()

                if any(q in text_lower for q in [
                    "would you like", "do you want", "shall i",
                    "please confirm", "is this correct", "approve",
                    "choose", "select", "pick",
                ]):
                    return {"changed": True, "reason": "question detected in page text"}

                if any(e in text_lower for e in [
                    "error", "failed", "insufficient credits",
                    "something went wrong",
                ]):
                    return {"changed": True, "reason": "error detected"}

                if any(d in text_lower for d in [
                    "download", "render complete", "your video is ready",
                    "export complete",
                ]):
                    return {"changed": True, "reason": "completion detected"}

                # Generic change — could be a new chat message
                return {"changed": True, "reason": "page content changed"}

            return {"changed": False, "reason": "no change"}

        except Exception as e:
            logger.debug(f"Change detection error: {e}")
            return {"changed": False, "reason": f"error: {e}"}

    # ------------------------------------------------------------------
    # Level 2: Visual analysis (screenshot + Vision API)
    # ------------------------------------------------------------------

    async def _analyze_screen(self) -> dict | None:
        """
        Take a screenshot and ask Gemini Vision what's happening.

        This is the "glance across at the screen" step.
        Returns event dict or None if nothing needs attention.
        """
        # Take screenshot
        screenshot_path = await self.browser.take_screenshot("monitor")
        if not screenshot_path:
            # Fallback: analyze page text only
            return await self._analyze_text_only()

        try:
            import google.generativeai as genai
            from PIL import Image

            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("No GOOGLE_API_KEY — falling back to text analysis")
                return await self._analyze_text_only()

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")

            # Load screenshot
            img = Image.open(str(screenshot_path))

            context_line = f"Context: I am {self._context}" if self._context else ""

            response = model.generate_content([
                f"You are Occy, an AI agent operating a website through a browser. "
                f"{context_line}\n\n"
                f"Look at this screenshot and tell me:\n"
                f"1. Is anything asking me a question or waiting for my input? "
                f"(dialog box, chat message, confirmation prompt, form field)\n"
                f"2. Is there an error or problem I need to handle?\n"
                f"3. Is a process complete that I should react to?\n\n"
                f"Respond in this JSON format ONLY:\n"
                f'{{"needs_interaction": true/false, '
                f'"type": "question|error|complete|waiting|none", '
                f'"description": "brief description of what needs attention", '
                f'"suggested_response": "what I should type or click"}}\n\n'
                f"If nothing needs attention, set needs_interaction to false.",
                img,
            ])

            # Parse the response
            result_text = response.text.strip()
            # Strip markdown code fences if present
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                result_text = result_text.strip()

            event = json.loads(result_text)
            event["screenshot"] = str(screenshot_path)
            event["timestamp"] = datetime.now().isoformat()
            return event

        except (ImportError, json.JSONDecodeError) as e:
            logger.warning(f"Vision analysis failed: {e}")
            return await self._analyze_text_only()
        except Exception as e:
            logger.error(f"Vision analysis error: {e}")
            return await self._analyze_text_only()

    async def _analyze_text_only(self) -> dict | None:
        """Fallback: analyze page text without Vision (cheaper, less accurate)."""
        text = await self.browser.get_page_text()
        text_lower = text.lower()

        if any(q in text_lower for q in [
            "would you like", "do you want", "shall i",
            "please confirm", "is this correct",
        ]):
            return {
                "needs_interaction": True,
                "type": "question",
                "description": "The page appears to be asking a question",
                "suggested_response": "Yes, go ahead",
            }

        if any(e in text_lower for e in [
            "error", "failed", "insufficient credits",
        ]):
            return {
                "needs_interaction": True,
                "type": "error",
                "description": "An error is showing on the page",
                "suggested_response": None,
            }

        if any(d in text_lower for d in [
            "download", "render complete", "your video is ready",
        ]):
            return {
                "needs_interaction": True,
                "type": "complete",
                "description": "The process appears to be complete",
                "suggested_response": "download",
            }

        return None

    # ------------------------------------------------------------------
    # Level 3: Auto-respond (when no callback is set)
    # ------------------------------------------------------------------

    async def _auto_respond(self, event: dict):
        """
        Default handler: automatically respond to common interactions.

        For questions/confirmations: approve with browser-use task.
        For errors: take screenshot and log.
        For completions: notify and stop monitoring.
        """
        event_type = event.get("type", "unknown")
        description = event.get("description", "")
        suggested = event.get("suggested_response", "")

        logger.info(
            f"Auto-responding to {event_type}: {description}"
        )

        if event_type == "question":
            # Respond affirmatively via browser-use
            response_text = suggested or "Yes, go ahead"
            await self.browser.run_task(
                f"The website is asking a question or waiting for confirmation. "
                f"The question is: '{description}'. "
                f"Respond by typing '{response_text}' in the chat/input area "
                f"and pressing Enter, OR click the appropriate confirmation "
                f"button (Yes, Confirm, OK, Approve, Continue, Generate). "
                f"If there are multiple options, pick the one that means 'yes' "
                f"or 'proceed'.",
                max_steps=10,
            )

        elif event_type == "error":
            # Log the error and take a screenshot
            await self.browser.take_screenshot("monitor_error")
            logger.error(f"Screen monitor detected error: {description}")

        elif event_type == "complete":
            logger.info(f"Screen monitor detected completion: {description}")

    # ------------------------------------------------------------------
    # Convenience: wait for a process with active monitoring
    # ------------------------------------------------------------------

    async def wait_with_monitoring(
        self,
        done_check: Callable = None,
        timeout_seconds: int = 600,
    ) -> dict:
        """
        Wait for something to finish while actively monitoring for interactions.

        This replaces the passive wait_for_render() — instead of just polling
        page text, Occy watches the screen and responds to questions/dialogs.

        Args:
            done_check: async function that returns True when the process is done.
                        If None, uses default completion detection.
            timeout_seconds: max wait time

        Returns:
            dict with 'completed', 'duration_seconds', 'interactions', 'error'
        """
        start = datetime.now()
        interactions = []

        # Override the callback to track interactions
        original_callback = self._on_interaction

        async def tracking_callback(event):
            interactions.append(event)
            await self._auto_respond(event)

        self._on_interaction = tracking_callback

        try:
            # Start monitoring if not already
            was_watching = self._watching
            if not was_watching:
                await self.start()

            while (datetime.now() - start).total_seconds() < timeout_seconds:
                # Check if we're done
                if done_check:
                    if await done_check():
                        duration = (datetime.now() - start).total_seconds()
                        return {
                            "completed": True,
                            "duration_seconds": duration,
                            "interactions": len(interactions),
                            "error": None,
                        }
                else:
                    # Default done check: look for completion indicators
                    text = await self.browser.get_page_text()
                    text_lower = text.lower()
                    if any(ind in text_lower for ind in [
                        "download", "render complete", "your video is ready",
                        "export complete",
                    ]):
                        duration = (datetime.now() - start).total_seconds()
                        return {
                            "completed": True,
                            "duration_seconds": duration,
                            "interactions": len(interactions),
                            "error": None,
                        }

                    if any(ind in text_lower for ind in [
                        "insufficient credits",
                    ]):
                        duration = (datetime.now() - start).total_seconds()
                        return {
                            "completed": False,
                            "duration_seconds": duration,
                            "interactions": len(interactions),
                            "error": "Insufficient credits",
                        }

                await asyncio.sleep(self._check_interval)

            # Timeout
            return {
                "completed": False,
                "duration_seconds": timeout_seconds,
                "interactions": len(interactions),
                "error": "Timeout",
            }

        finally:
            self._on_interaction = original_callback
            if not was_watching:
                await self.stop()

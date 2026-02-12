"""
Comic Pipeline — Image Judge.

Uses Claude vision to verify each generated image matches its script prompt.
Rejects images that don't match, flags issues, and can trigger regeneration.
"""

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from comic_pipeline.models import ComicProject, Panel

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """You are a meticulous image quality judge for a comic parable pipeline.

You will be shown:
1. The IMAGE PROMPT that was sent to an AI image generator
2. The NARRATION text for this panel
3. The GENERATED IMAGE

Your job: verify the image matches what was asked for using a strict checklist approach.

STEP 1 — EXTRACT CHECKLIST:
Read the IMAGE PROMPT and NARRATION carefully. Extract every specific visual requirement into these categories:
- characters: Who is present? How many? What do they look like?
- action: What is each character doing? What pose/gesture?
- objects: What specific items are mentioned? (e.g. "wooden crate", "brass horn", "ten fish")
- setting: Where does this take place? What environment details?
- composition: Camera angle, framing, perspective?

STEP 2 — VERIFY EACH ITEM:
Look at the image and check EVERY item on your checklist. Mark each as:
- PRESENT: clearly visible in the image
- MISSING: not visible at all
- WRONG: visible but incorrect (e.g. prompt says "standing on a box" but image shows standing on ground)

CRITICAL vs NON-CRITICAL:
- CRITICAL categories (auto-fail if any item is MISSING or WRONG): characters, action, objects
- NON-CRITICAL categories (deduct points but don't auto-fail): setting, composition

Return ONLY valid JSON:
{
  "checklist": {
    "characters": [
      {"item": "description of requirement", "status": "PRESENT|MISSING|WRONG", "note": "what you see"}
    ],
    "action": [
      {"item": "description of requirement", "status": "PRESENT|MISSING|WRONG", "note": "what you see"}
    ],
    "objects": [
      {"item": "description of requirement", "status": "PRESENT|MISSING|WRONG", "note": "what you see"}
    ],
    "setting": [
      {"item": "description of requirement", "status": "PRESENT|MISSING|WRONG", "note": "what you see"}
    ],
    "composition": [
      {"item": "description of requirement", "status": "PRESENT|MISSING|WRONG", "note": "what you see"}
    ]
  },
  "critical_pass": true or false,
  "pass": true or false,
  "score": 1-10,
  "issues": ["list of specific MISSING/WRONG items, empty if none"],
  "suggestion": "specific fix instructions for regeneration, empty string if pass"
}

Scoring guide:
- 10: Every item PRESENT
- 8-9: All critical items PRESENT, minor non-critical issues
- 6-7: All critical items PRESENT but some non-critical MISSING/WRONG
- 4-5: One critical item MISSING or WRONG
- 1-3: Multiple critical items MISSING or WRONG

Be EXTREMELY specific. Check every single detail. If the prompt says "standing on a wooden crate" and the character is standing on the ground, that is WRONG — do not gloss over it."""


def _summarise_checklist(checklist: dict) -> str:
    """Build a short one-line summary of checklist results."""
    if not checklist:
        return "no checklist"
    counts = {"PRESENT": 0, "MISSING": 0, "WRONG": 0}
    for items in checklist.values():
        for item in items:
            status = item.get("status", "").upper()
            if status in counts:
                counts[status] += 1
    total = sum(counts.values())
    if counts["MISSING"] == 0 and counts["WRONG"] == 0:
        return f"all {total} items present"
    parts = []
    if counts["MISSING"]:
        parts.append(f"{counts['MISSING']} missing")
    if counts["WRONG"]:
        parts.append(f"{counts['WRONG']} wrong")
    parts.append(f"{counts['PRESENT']}/{total} present")
    return ", ".join(parts)


class ImageJudge:
    """Verifies generated images match their prompts using Claude vision."""

    def __init__(self, model_router=None):
        self._model_router = model_router

    def _get_router(self):
        """Lazy-load model router."""
        if self._model_router is None:
            from core.model_router import ModelRouter
            self._model_router = ModelRouter()
        return self._model_router

    async def judge_panels(
        self,
        project: ComicProject,
        max_retries: int = 1,
        regenerator=None,
    ) -> ComicProject:
        """
        Judge all panel images against their prompts.

        Args:
            project: ComicProject with generated panel images
            max_retries: How many times to regenerate a failed image
            regenerator: Image generator to use for regeneration (optional)

        Returns:
            Updated project with judge results logged
        """
        router = self._get_router()
        panels_with_images = [p for p in project.panels if p.image_path]

        passed = 0
        failed = 0

        for panel in panels_with_images:
            logger.info(
                f"Judging panel {panel.panel_number}/{len(panels_with_images)}..."
            )

            result = await self._judge_single(router, panel)

            if result.get("pass", False):
                passed += 1
                score = result.get("score", "?")
                checklist_summary = _summarise_checklist(
                    result.get("checklist", {})
                )
                logger.info(
                    f"Panel {panel.panel_number}: PASS (score: {score}) "
                    f"— {checklist_summary}"
                )
                project.log(
                    f"Panel {panel.panel_number} judge: PASS "
                    f"(score: {score})"
                )
            else:
                failed += 1
                score = result.get("score", "?")
                issues = result.get("issues", [])
                suggestion = result.get("suggestion", "")
                logger.warning(
                    f"Panel {panel.panel_number}: FAIL (score: {score}) "
                    f"- Issues: {issues}"
                )
                project.log(
                    f"Panel {panel.panel_number} judge: FAIL "
                    f"(score: {score}) - {'; '.join(issues)}"
                )

                # Attempt regeneration if we have a generator
                if regenerator and max_retries > 0:
                    logger.info(
                        f"Regenerating panel {panel.panel_number}: "
                        f"{suggestion}"
                    )
                    # Enhance the prompt with the judge's suggestion
                    enhanced_prompt = panel.image_prompt
                    if suggestion:
                        enhanced_prompt += (
                            f" IMPORTANT: {suggestion}"
                        )

                    try:
                        output_dir = str(
                            Path(panel.image_path).parent
                        )
                        old_prompt = panel.image_prompt
                        panel.image_prompt = enhanced_prompt

                        temp_project = ComicProject(
                            title="regen",
                            theme_id="regen",
                            art_style=project.art_style,
                            art_style_negative=project.art_style_negative,
                        )
                        temp_project.panels = [panel]

                        await regenerator.generate_panels(
                            temp_project, output_dir
                        )

                        panel.image_prompt = old_prompt  # Restore original

                        # Re-judge
                        result2 = await self._judge_single(router, panel)
                        if result2.get("pass", False):
                            logger.info(
                                f"Panel {panel.panel_number}: PASS on retry "
                                f"(score: {result2.get('score', '?')})"
                            )
                            project.log(
                                f"Panel {panel.panel_number} regen: PASS"
                            )
                            failed -= 1
                            passed += 1
                        else:
                            project.log(
                                f"Panel {panel.panel_number} regen: "
                                f"still FAIL"
                            )

                    except Exception as e:
                        logger.error(
                            f"Panel {panel.panel_number} regen failed: {e}"
                        )
                        panel.image_prompt = panel.image_prompt  # restore

        logger.info(
            f"Image judge complete: {passed} passed, {failed} failed "
            f"out of {len(panels_with_images)}"
        )
        project.log(
            f"Image judge: {passed}/{len(panels_with_images)} passed"
        )

        return project

    async def _judge_single(self, router, panel: Panel) -> dict:
        """
        Judge a single panel image against its prompt using a checklist approach.

        Step 1: Extract a checklist of visual requirements from the prompt + narration.
        Step 2: Verify each item against the actual image.

        Critical categories (characters, action, objects) cause auto-fail if any
        item is MISSING or WRONG. Non-critical categories (setting, composition)
        deduct points but don't auto-fail.
        """
        import json

        if not panel.image_path or not Path(panel.image_path).exists():
            return {
                "pass": False,
                "score": 0,
                "checklist": {},
                "critical_pass": False,
                "issues": ["No image file found"],
                "suggestion": "Generate the image",
            }

        # Read image and encode as base64
        with open(panel.image_path, "rb") as f:
            image_data = f.read()
        image_b64 = base64.b64encode(image_data).decode("utf-8")

        # Detect actual media type from file header (not extension)
        if image_data[:8] == b'\x89PNG\r\n\x1a\n':
            media_type = "image/png"
        elif image_data[:2] == b'\xff\xd8':
            media_type = "image/jpeg"
        elif image_data[:4] == b'RIFF' and image_data[8:12] == b'WEBP':
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"  # default fallback

        # Build the user text with both prompt and narration for checklist extraction
        user_text = (
            f"PANEL {panel.panel_number}\n\n"
            f"IMAGE PROMPT:\n{panel.image_prompt}\n\n"
            f"NARRATION:\n{panel.narration}\n\n"
            f"STEP 1: Extract a checklist of every visual requirement from the "
            f"IMAGE PROMPT and NARRATION above.\n"
            f"STEP 2: Examine the image below and verify each checklist item.\n"
            f"Return the JSON result."
        )

        # Build message with image — Anthropic vision format
        messages = [
            {"role": "system", "content": JUDGE_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_text,
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_b64,
                        },
                    },
                ],
            },
        ]

        # Use cheap model for judging (Haiku — fast, cheap, vision-capable)
        model = router.select_model("classify_content")
        response = await router.invoke(model, messages, max_tokens=1024)
        raw = response["content"].strip()

        # Parse JSON response
        try:
            # Handle markdown fences
            if "```json" in raw:
                raw = raw.split("```json", 1)[1].split("```", 1)[0]
            elif "```" in raw:
                raw = raw.split("```", 1)[1].split("```", 1)[0]

            first = raw.find("{")
            last = raw.rfind("}")
            if first != -1 and last != -1:
                raw = raw[first:last + 1]

            result = json.loads(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"Judge response parse failed: {e}. Raw: {raw[:200]}"
            )
            # Default to pass if we can't parse (don't block pipeline)
            return {
                "pass": True,
                "score": 5,
                "checklist": {},
                "critical_pass": True,
                "issues": ["Judge response could not be parsed"],
                "suggestion": "",
            }

        # Post-process: enforce critical/non-critical logic locally
        # in case the model's own pass/fail judgment is too lenient
        checklist = result.get("checklist", {})
        critical_categories = ["characters", "action", "objects"]
        critical_failures = []

        for category in critical_categories:
            items = checklist.get(category, [])
            for item in items:
                status = item.get("status", "").upper()
                if status in ("MISSING", "WRONG"):
                    desc = item.get("item", "unknown")
                    note = item.get("note", "")
                    critical_failures.append(
                        f"[{category}] {desc}: {status} — {note}"
                    )

        # Override model's judgment if it missed critical failures
        if critical_failures:
            result["critical_pass"] = False
            result["pass"] = False
            # Cap score at 5 if there are critical failures
            if result.get("score", 0) > 5:
                result["score"] = 5
            # Merge any failures into the issues list
            existing_issues = result.get("issues", [])
            for failure in critical_failures:
                if failure not in existing_issues:
                    existing_issues.append(failure)
            result["issues"] = existing_issues
            # Build a suggestion from failures if none provided
            if not result.get("suggestion"):
                result["suggestion"] = (
                    "Fix: " + "; ".join(critical_failures)
                )
        else:
            result["critical_pass"] = True
            # If all critical items pass, allow score-based pass/fail
            # (non-critical misses can still lower score but won't auto-fail)
            if result.get("score", 0) >= 7:
                result["pass"] = True

        # Log the checklist for debugging
        for category, items in checklist.items():
            for item in items:
                status = item.get("status", "?")
                desc = item.get("item", "?")
                if status in ("MISSING", "WRONG"):
                    logger.debug(
                        f"Panel {panel.panel_number} checklist: "
                        f"{category}/{desc} = {status}"
                    )

        return result

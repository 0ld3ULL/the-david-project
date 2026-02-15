"""
Occy Learning Engine — Systematic Focal ML feature exploration.

Occy doesn't guess. It explores features methodically, documents everything,
and builds a searchable knowledge base of what works, what doesn't, and how
much it costs.

Exploration cycle:
1. Select next feature (priority: unexplored > partial > job-relevant > random)
2. Navigate to the feature in Focal ML
3. Screenshot the UI — send to Claude Vision for element identification
4. Try each option, document results
5. Store findings in KnowledgeStore
6. Update confidence score in feature map
7. Report to Jono via Telegram

Requires: occy_browser.py, KnowledgeStore, occy_curriculum.yaml
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

CURRICULUM_PATH = Path("config/occy_curriculum.yaml")
FEATURE_MAP_PATH = Path("data/occy_feature_map.json")

# Categories containing features that generate content (cost credits).
# Used to filter _select_next_feature() in hands-on mode.
GENERATIVE_CATEGORIES = {
    "video_models", "image_models", "voice_tts", "project_creation",
}

# Default test prompts per category when a feature lacks its own test_prompt.
DEFAULT_TEST_PROMPTS = {
    "video_models": "A person walking through a park on a sunny day",
    "image_models": "A mountain landscape at sunset",
    "voice_tts": "Hello, welcome to AIPulse",
    "project_creation": "A 10 second video about a sunrise over the ocean",
}

# Credit safety floor — stop hands-on learning if balance drops below this.
CREDIT_SAFETY_FLOOR = 200


class OccyLearner:
    """
    Systematic feature exploration engine for Focal ML.

    Reads the curriculum (what to learn), selects features by priority,
    explores them in the browser, and stores findings in the knowledge base.
    """

    def __init__(self, browser, knowledge_store, audit_log=None, model_router=None):
        """
        Args:
            browser: FocalBrowser instance
            knowledge_store: KnowledgeStore for permanent findings
            audit_log: AuditLog for tracking exploration actions
            model_router: ModelRouter for knowledge distillation via Haiku
        """
        self.browser = browser
        self.knowledge = knowledge_store
        self.audit_log = audit_log
        self.model_router = model_router
        self.feature_map = self._load_feature_map()

    def _load_feature_map(self) -> dict:
        """
        Load feature map from saved state, or initialize from curriculum.

        The feature map tracks learning progress. It starts from the
        curriculum YAML and gets updated as Occy explores.
        """
        # Try saved state first (preserves progress)
        if FEATURE_MAP_PATH.exists():
            try:
                with open(FEATURE_MAP_PATH) as f:
                    return json.load(f)
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Corrupted feature map, reinitializing: {e}")

        # Initialize from curriculum
        if not CURRICULUM_PATH.exists():
            logger.warning("No curriculum found — starting with empty feature map")
            return {"categories": {}}

        with open(CURRICULUM_PATH) as f:
            curriculum = yaml.safe_load(f)

        # Convert to runtime format with tracking fields
        feature_map = {"categories": {}}
        for cat_name, cat_data in curriculum.get("categories", {}).items():
            feature_map["categories"][cat_name] = {
                "description": cat_data.get("description", ""),
                "features": [],
            }
            for feat in cat_data.get("features", []):
                feature_map["categories"][cat_name]["features"].append({
                    "name": feat["name"],
                    "description": feat["description"],
                    "confidence": feat.get("confidence", 0.0),
                    "priority": feat.get("priority", 5),
                    "notes": feat.get("notes", ""),
                    "generative": feat.get("generative", False),
                    "test_prompt": feat.get("test_prompt", ""),
                    "explored_count": 0,
                    "last_explored": None,
                    "knowledge_ids": [],  # IDs of related KnowledgeStore entries
                })

        self._save_feature_map(feature_map)
        return feature_map

    def _save_feature_map(self, feature_map: dict = None):
        """Save feature map state to disk."""
        if feature_map is None:
            feature_map = self.feature_map

        FEATURE_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(FEATURE_MAP_PATH, "w") as f:
            json.dump(feature_map, f, indent=2)

    def _select_next_feature(
        self,
        job_relevant: list[str] = None,
        exclude: set[str] = None,
        mode: str = "explore",
    ) -> tuple[str, dict] | None:
        """
        Select the next feature to explore or practice hands-on.

        In "explore" mode (default):
            1. Unexplored (confidence 0.0) with highest priority
            2. Partially explored (confidence < 0.5) with highest priority
            3. Job-relevant features (if a job needs specific skills)
            4. Random deep-dive on a known feature

        In "hands_on" mode:
            - Only selects generative features (ones that cost credits)
            - Targets confidence 0.3-0.7 (explored but not production-tested)
            - Priority 1 features first

        Args:
            job_relevant: Feature names relevant to a current job
            exclude: Feature names to skip (already attempted this session)
            mode: "explore" or "hands_on"

        Returns:
            (category_name, feature_dict) or None if all mastered/excluded
        """
        exclude = exclude or set()

        if mode == "hands_on":
            # Hands-on mode: only generative features at 0.3-0.7 confidence
            candidates = []
            for cat_name, cat_data in self.feature_map.get("categories", {}).items():
                for feat in cat_data.get("features", []):
                    if feat["name"] in exclude:
                        continue
                    # Must be generative (costs credits) or in a generative category
                    is_generative = feat.get("generative", False) or cat_name in GENERATIVE_CATEGORIES
                    if not is_generative:
                        continue
                    # Target range: explored but not yet hands-on tested
                    if 0.3 <= feat["confidence"] <= 0.7:
                        candidates.append((cat_name, feat))

            if candidates:
                candidates.sort(key=lambda x: (x[1]["priority"], x[1]["confidence"]))
                return candidates[0]

            # Fallback: any generative feature under 0.7 (including unexplored)
            fallback = []
            for cat_name, cat_data in self.feature_map.get("categories", {}).items():
                for feat in cat_data.get("features", []):
                    if feat["name"] in exclude:
                        continue
                    is_generative = feat.get("generative", False) or cat_name in GENERATIVE_CATEGORIES
                    if is_generative and feat["confidence"] < 0.7:
                        fallback.append((cat_name, feat))

            if fallback:
                fallback.sort(key=lambda x: (x[1]["priority"], -x[1]["confidence"]))
                return fallback[0]

            logger.info("All generative features at confidence >= 0.7 — hands-on complete!")
            return None

        # --- Standard explore mode ---
        unexplored = []
        partial = []
        relevant = []
        deep_dive = []

        for cat_name, cat_data in self.feature_map.get("categories", {}).items():
            for feat in cat_data.get("features", []):
                # Skip features already attempted this session
                if feat["name"] in exclude:
                    continue

                entry = (cat_name, feat)

                if feat["confidence"] == 0.0:
                    unexplored.append(entry)
                elif feat["confidence"] < 0.5:
                    partial.append(entry)
                elif feat["confidence"] < 0.9:
                    deep_dive.append(entry)

                # Check job relevance
                if job_relevant and feat["name"] in job_relevant:
                    if feat["confidence"] < 0.7:
                        relevant.append(entry)

        # Pick from highest priority group
        for group in [unexplored, partial, relevant, deep_dive]:
            if group:
                # Sort by priority (lower number = higher priority), then
                # by explored_count (prefer least-explored as tiebreaker)
                group.sort(key=lambda x: (x[1]["priority"], x[1].get("explored_count", 0)))
                return group[0]

        if exclude:
            logger.info(f"No more features to explore this session ({len(exclude)} already attempted)")
        else:
            logger.info("All features at confidence >= 0.9 — exploration complete!")
        return None

    def _get_course_knowledge(self, feature_name: str, category: str) -> str:
        """
        Query the knowledge base for course material about a feature.
        Returns relevant course text the agent can use for verification.
        """
        # Search for relevant course entries
        results = []
        for query in [feature_name, category]:
            entries = self.knowledge.search(query)
            for e in entries:
                if hasattr(e, 'source') and 'youtube_tutorials' in (e.source or ''):
                    content = e.content if hasattr(e, 'content') else str(e)
                    if content not in results:
                        results.append(content)

        if not results:
            return ""

        # Combine relevant course material (limit to 3000 chars)
        combined = "\n---\n".join(results)
        if len(combined) > 3000:
            combined = combined[:3000] + "\n[...truncated]"
        return combined

    async def _distill_knowledge(
        self, raw_content: str, feature_name: str, category: str,
        knowledge_type: str = "feature",
    ) -> str:
        """
        Distill raw browser output into clean, structured knowledge via Haiku.

        Uses the same proven pattern as Oprah's _distill_identity_rule().

        Args:
            raw_content: Raw browser agent output (often debug dumps)
            feature_name: Name of the feature being explored
            category: Feature category (e.g. "generation", "editing")
            knowledge_type: "ui_elements" or "feature"

        Returns:
            Clean structured text, or raw_content[:2000] if distillation fails
        """
        if not self.model_router or not raw_content.strip():
            return raw_content[:2000]

        try:
            from core.model_router import ModelTier

            model = self.model_router.models.get(ModelTier.CHEAP)
            if not model:
                model = self.model_router.select_model("simple_qa")

            if knowledge_type == "ui_elements":
                system_prompt = (
                    "You extract clean UI element catalogs from raw browser automation output. "
                    "Given messy browser debug output from exploring a feature, extract a clean catalog of "
                    "every UI element found. For each element list:\n"
                    "- Label/name\n"
                    "- Type (button, dropdown, slider, toggle, input, etc.)\n"
                    "- Available options (for dropdowns/selects)\n"
                    "- Default value (if visible)\n\n"
                    "Return ONLY the clean catalog, no commentary. Use a compact structured format."
                )
            else:
                system_prompt = (
                    "You distill raw browser automation output into clean, structured feature documentation. "
                    "Given messy browser debug output from exploring a feature, extract:\n"
                    "- What the feature does (1-2 sentences)\n"
                    "- How to use it (numbered steps)\n"
                    "- Available options and their effects\n"
                    "- Gotchas or limitations discovered\n"
                    "- Credit/cost info if mentioned\n\n"
                    "Return ONLY the clean documentation, no commentary. Be concise but thorough."
                )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": (
                    f"FEATURE: {feature_name} (category: {category})\n\n"
                    f"RAW BROWSER OUTPUT:\n{raw_content[:3000]}\n\n"
                    f"Distill this into clean, structured knowledge:"
                )},
            ]

            response = await self.model_router.invoke(model, messages, max_tokens=500)
            distilled = response["content"].strip()

            if distilled:
                logger.info(
                    f"Distilled {len(raw_content)} chars -> {len(distilled)} chars "
                    f"for {feature_name} ({knowledge_type})"
                )
                return distilled

        except Exception as e:
            logger.warning(f"Knowledge distillation failed for {feature_name}: {e}")

        # Graceful fallback: return truncated raw content (current behavior)
        return raw_content[:2000]

    async def explore_feature(self, category: str, feature: dict) -> dict:
        """
        Explore a single feature in Focal ML.

        Steps:
        1. Check course material for what tutorials say about this feature
        2. Navigate to the feature area
        3. Take screenshot for UI mapping
        4. Identify UI elements via Claude Vision
        5. Try available options — verify course claims against live site
        6. Document findings with verification status

        Auto-detects browser disconnection and aborts early to avoid
        wasting API calls on a dead browser.

        Returns:
            dict with 'success', 'findings', 'confidence_delta', 'credits_used'
        """
        feature_name = feature["name"]
        logger.info(f"Exploring: [{category}] {feature_name}")

        findings = []

        # Quick connection check (no API call — just checks internal state)
        if not self.browser.is_connected:
            logger.warning(f"Browser disconnected before exploring {feature_name}")
            self._update_feature_progress(category, feature_name, 0.0)
            return {
                "success": False,
                "findings": ["Browser disconnected before exploration"],
                "confidence_delta": 0.0,
                "credits_used": 0,
            }

        # Skip credit balance checks during exploration — they cost a full
        # browser-use agent call (~30s each) and we're not spending credits
        # during learning.  Only check if explicitly producing a video.
        credits_before = None

        # Step 0: Get course material for context
        course_context = self._get_course_knowledge(feature_name, category)
        if course_context:
            logger.info(f"  Course material found for {feature_name} ({len(course_context)} chars)")

        # Step 1: Navigate to the feature (with course context if available)
        #
        # Categories that live inside the project EDITOR (not the home page):
        # If the feature is in one of these categories, Occy must open an
        # existing project first to access the editor workspace.
        EDITOR_CATEGORIES = {
            "editor_chat", "stock_media", "transitions", "effects",
            "text_overlays", "captions", "settings", "timeline",
            "characters", "voice_tts", "video_models", "image_models",
        }

        nav_prompt = (
            f"Navigate to the '{feature_name}' feature area in Focal ML. "
            f"This is in the '{category}' category. "
            f"Feature description: {feature['description']}. "
        )

        # Add notes if they contain useful navigation hints
        if feature.get("notes"):
            nav_prompt += f"Location hint: {feature['notes']}. "

        # For editor-level features, instruct Occy to enter a project first
        if category in EDITOR_CATEGORIES:
            nav_prompt += (
                "IMPORTANT: This feature is inside the PROJECT EDITOR, not on the home page. "
                "You MUST first open an existing project (click on any project in the sidebar "
                "under 'Recent' or 'All projects') to enter the editor workspace. "
                "Once in the editor, look for the relevant panel in the left sidebar or bottom bar. "
            )
        else:
            nav_prompt += "Find and open this feature's UI. "
        if course_context:
            nav_prompt += (
                f"\n\nHere is what tutorial videos from ~March 2025 say about this feature "
                f"(may be outdated — verify against what you actually see):\n"
                f"{course_context[:1000]}"
            )

        nav_result = await self.browser.run_task(nav_prompt)

        # Check for browser death
        if nav_result.get("disconnected"):
            logger.warning(f"Browser disconnected during navigation to {feature_name}")
            self._update_feature_progress(category, feature_name, 0.0)
            return {
                "success": False,
                "findings": ["Browser disconnected during navigation"],
                "confidence_delta": 0.0,
                "credits_used": 0,
            }

        if not nav_result["success"]:
            findings.append(f"Could not navigate to {feature_name}: {nav_result.get('error')}")
            # Still update progress so repeated failures eventually move past this feature
            self._update_feature_progress(category, feature_name, 0.05)
            return {
                "success": False,
                "findings": findings,
                "confidence_delta": 0.05,  # Learned that navigation failed
                "credits_used": 0,
            }

        # Step 2: Screenshot for UI mapping
        screenshot_path = await self.browser.take_screenshot(f"explore_{feature_name}")

        # Step 3: Identify UI elements (via Browser Use task)
        ui_result = await self.browser.run_task(
            f"Look at the current page. You're exploring the '{feature_name}' feature. "
            f"Identify every button, dropdown, input field, slider, and toggle visible. "
            f"List each one with its label, type, and current value/state. "
            f"Be thorough — catalog everything you can see."
        )

        # Check for browser death after UI scan
        if ui_result.get("disconnected"):
            logger.warning(f"Browser disconnected during UI scan of {feature_name}")
            self._update_feature_progress(category, feature_name, 0.05)
            return {
                "success": False,
                "findings": ["Browser disconnected during UI scan"],
                "confidence_delta": 0.05,
                "credits_used": 0,
            }

        if ui_result["success"]:
            findings.append(f"UI elements: {ui_result['result']}")

            # Distill raw browser output into clean UI catalog
            distilled_ui = await self._distill_knowledge(
                ui_result["result"], feature_name, category, "ui_elements"
            )

            # Store UI mapping
            self.knowledge.add(
                category="technical",
                topic=f"Focal ML UI: {feature_name}",
                content=distilled_ui,
                source="occy_exploration",
                confidence=0.7,
                tags=["ui_element", category, feature_name],
            )

        # Step 4: Try available options — with verification if course material exists
        explore_prompt = (
            f"You're exploring the '{feature_name}' feature in Focal ML. "
            f"Try the available options one by one: "
            f"- Click each dropdown and note the choices "
            f"- Check toggle states "
            f"- Note any tooltips or help text "
            f"- Do NOT submit anything that costs credits yet "
        )
        if course_context:
            explore_prompt += (
                f"\n\nIMPORTANT — VERIFY these claims from ~March 2025 tutorials against "
                f"what you see on the LIVE site right now:\n"
                f"{course_context[:2000]}\n\n"
                f"For each claim, report: CONFIRMED (still true), CHANGED (different now), "
                f"or NOT FOUND (can't locate this feature). Note any NEW features not in the course."
            )
        else:
            explore_prompt += "Report what you found about each option."

        explore_result = await self.browser.run_task(explore_prompt)

        if explore_result.get("disconnected"):
            logger.warning(f"Browser disconnected during option exploration of {feature_name}")
            # Still save what we have — distill even partial findings
            if findings:
                raw_partial = "\n".join(findings)
                distilled_partial = await self._distill_knowledge(
                    raw_partial, feature_name, category, "feature"
                )
                self.knowledge.add(
                    category="technical",
                    topic=f"Focal ML feature: {feature_name} (partial)",
                    content=distilled_partial,
                    source="occy_exploration",
                    confidence=0.5,
                    tags=["feature_exploration", "partial", category, feature_name],
                )
            self._update_feature_progress(category, feature_name, 0.1)
            return {
                "success": False,
                "findings": findings + ["Browser disconnected during exploration"],
                "confidence_delta": 0.1,
                "credits_used": 0,
            }

        if explore_result["success"]:
            findings.append(f"Options explored: {explore_result['result']}")

        # Step 5: Document findings
        # Credit balance check skipped during exploration (too expensive)
        credits_used = 0

        # Distill and store comprehensive finding
        raw_finding = "\n".join(findings)
        distilled_finding = await self._distill_knowledge(
            raw_finding, feature_name, category, "feature"
        )
        knowledge_id = self.knowledge.add(
            category="technical",
            topic=f"Focal ML feature: {feature_name}",
            content=distilled_finding,
            source="occy_exploration",
            confidence=0.8,
            tags=["feature_exploration", category, feature_name],
        )

        # Update feature map — higher confidence when verifying course material
        if course_context and nav_result["success"] and ui_result["success"]:
            confidence_delta = 0.5  # Course-verified exploration = fast-tracked learning
        elif nav_result["success"] and ui_result["success"]:
            confidence_delta = 0.3
        else:
            confidence_delta = 0.1
        self._update_feature_progress(category, feature_name, confidence_delta, knowledge_id)

        if self.audit_log:
            self.audit_log.log(
                "occy", "info", "exploration",
                f"Explored {feature_name}",
                details=f"confidence_delta={confidence_delta}, credits={credits_used}",
            )

        return {
            "success": True,
            "findings": findings,
            "confidence_delta": confidence_delta,
            "credits_used": credits_used,
        }

    async def explore_hands_on(
        self, category: str, feature: dict, credit_budget: int = 10,
    ) -> dict:
        """
        Actually USE a generative feature — spend credits, measure results.

        Unlike explore_feature() which only catalogues UI, this method:
        1. Checks credit balance before starting
        2. Creates a minimal test (simple prompt, short duration)
        3. Clicks Generate — actually spends credits
        4. Waits for result
        5. Measures real credit cost (before - after)
        6. Reviews output quality
        7. Stores findings tagged source="hands_on_test"
        8. Updates confidence into the 0.7-0.9 range

        Args:
            category: Feature category (e.g. "video_models")
            feature: Feature dict from feature map
            credit_budget: Max credits to spend on this single test

        Returns:
            dict with success, credits_spent, generation_time, quality_notes, etc.
        """
        feature_name = feature["name"]
        logger.info(f"Hands-on test: [{category}] {feature_name}")

        # Quick connection check
        if not self.browser.is_connected:
            logger.warning(f"Browser disconnected before hands-on test of {feature_name}")
            return {
                "success": False,
                "feature": feature_name,
                "error": "Browser disconnected",
                "credits_spent": 0,
            }

        # Step 1: Check credit balance
        credits_before = await self.browser.get_credit_balance()
        if credits_before is None:
            logger.warning("Could not read credit balance — skipping hands-on test")
            return {
                "success": False,
                "feature": feature_name,
                "error": "Could not read credit balance",
                "credits_spent": 0,
            }

        if credits_before < CREDIT_SAFETY_FLOOR:
            logger.warning(
                f"Credit balance {credits_before} below safety floor "
                f"{CREDIT_SAFETY_FLOOR} — skipping hands-on"
            )
            return {
                "success": False,
                "feature": feature_name,
                "error": f"Credit balance {credits_before} below safety floor {CREDIT_SAFETY_FLOOR}",
                "credits_spent": 0,
            }

        # Step 2: Determine test prompt
        test_prompt = feature.get("test_prompt") or DEFAULT_TEST_PROMPTS.get(category, "")
        if not test_prompt:
            test_prompt = "A simple test scene with a person walking outdoors"

        # Step 3: Navigate and generate
        #
        # Build a generation prompt. This is the key difference from exploration —
        # we actually click Generate.
        gen_prompt = (
            f"You are testing the '{feature_name}' feature in Focal ML. "
            f"Feature: {feature['description']}. "
        )

        # Cost constraint applied to ALL generation prompts
        cost_warning = (
            "IMPORTANT: Use the SMALLEST/CHEAPEST settings. "
            "Shortest duration, lowest resolution, single output only. "
        )

        if category == "video_models":
            gen_prompt += (
                f"{cost_warning}"
                f"Create a SHORT test video (5-10 seconds) using this model. "
                f"Steps:\n"
                f"1. Make sure you're in a project (create one if needed)\n"
                f"2. Select '{feature_name}' as the video model\n"
                f"3. Use this prompt: \"{test_prompt}\"\n"
                f"4. Set duration to the shortest available option\n"
                f"5. Click Generate/Render and WAIT for it to complete\n"
                f"6. Note the result — did it succeed? How long did it take?\n"
                f"Do NOT cancel — let the generation finish."
            )
        elif category == "image_models":
            gen_prompt += (
                f"{cost_warning}"
                f"Generate a single test image using this model. "
                f"Steps:\n"
                f"1. Make sure you're in a project (create one if needed)\n"
                f"2. Select '{feature_name}' as the image model\n"
                f"3. Use this prompt: \"{test_prompt}\"\n"
                f"4. Click Generate and WAIT for the result\n"
                f"5. Note the quality of the output."
            )
        elif category == "voice_tts":
            gen_prompt += (
                f"{cost_warning}"
                f"Generate a short voice clip using this model. "
                f"Steps:\n"
                f"1. Make sure you're in a project\n"
                f"2. Select '{feature_name}' as the voice model\n"
                f"3. Use this text: \"{test_prompt}\"\n"
                f"4. Click Generate/Preview and WAIT for the result\n"
                f"5. Note the voice quality."
            )
        else:
            gen_prompt += (
                f"{cost_warning}"
                f"Test this feature by creating a MINIMAL output. "
                f"Use the shortest duration, lowest resolution, single output only. "
                f"Use prompt: \"{test_prompt}\". "
                f"Click Generate/Create and wait for the result. "
                f"Do NOT create a full project — just a single minimal test generation."
            )

        start_time = datetime.now()
        gen_result = await self.browser.run_task(gen_prompt)
        generation_time = (datetime.now() - start_time).total_seconds()

        if gen_result.get("disconnected"):
            logger.warning(f"Browser disconnected during generation of {feature_name}")
            return {
                "success": False,
                "feature": feature_name,
                "error": "Browser disconnected during generation",
                "credits_spent": 0,
                "generation_time_seconds": round(generation_time, 1),
            }

        # Step 4: Measure credit cost
        credits_after = await self.browser.get_credit_balance()
        credits_spent = 0
        if credits_after is not None and credits_before is not None:
            credits_spent = max(0, credits_before - credits_after)

        # Sanity check: if credits_after is 0 and credits_before was large,
        # the credit reader probably failed (both Gemini and Sonnet frequently
        # misread the balance as 0). Don't treat a bad read as overspend.
        # Max plausible single-generation cost on Focal is ~500 credits.
        MAX_PLAUSIBLE_SINGLE_COST = 500
        credit_read_suspect = False
        if credits_spent > MAX_PLAUSIBLE_SINGLE_COST and credits_after == 0:
            logger.warning(
                f"Credit read suspect: before={credits_before}, after={credits_after}, "
                f"calculated_spend={credits_spent}. Likely a misread — "
                f"capping spend estimate at {MAX_PLAUSIBLE_SINGLE_COST}"
            )
            credits_spent = MAX_PLAUSIBLE_SINGLE_COST
            credit_read_suspect = True

        # Check for overspend against per-test budget
        overspent = credits_spent > credit_budget and not credit_read_suspect
        if overspent:
            logger.warning(
                f"OVERSPEND: {feature_name} used {credits_spent} credits "
                f"(budget was {credit_budget}) — flagging for session stop"
            )

        # Step 5: Screenshot and quality review
        screenshot_path = await self.browser.take_screenshot(f"hands_on_{feature_name}")

        quality_notes = ""
        if gen_result["success"]:
            # Ask the browser agent to review the output quality
            review_result = await self.browser.run_task(
                f"Look at the output that was just generated by '{feature_name}'. "
                f"Rate the quality briefly:\n"
                f"- Did it match the prompt? (yes/partially/no)\n"
                f"- Visual quality (good/decent/poor)\n"
                f"- Any artifacts or issues? (face distortion, motion blur, etc.)\n"
                f"- Would this be usable in a real video? (yes/with-editing/no)\n"
                f"Be concise — 2-3 sentences max."
            )
            if review_result["success"]:
                quality_notes = await self._distill_knowledge(
                    review_result["result"], feature_name, category, "feature"
                )

        # Step 6: Store hands-on knowledge
        hands_on_entry = {
            "feature": feature_name,
            "category": category,
            "test_prompt": test_prompt,
            "credits_spent": credits_spent,
            "generation_time_seconds": round(generation_time, 1),
            "quality_notes": quality_notes,
            "generation_succeeded": gen_result["success"],
            "tested_at": datetime.now().isoformat(),
        }

        knowledge_id = self.knowledge.add(
            category="technical",
            topic=f"Focal ML hands-on: {feature_name}",
            content=json.dumps(hands_on_entry, indent=2),
            source="hands_on_test",
            confidence=0.9,
            tags=["hands_on_test", category, feature_name],
        )

        # Step 7: Update confidence
        # +0.2 for successful generation, +0.1 for quality review
        if gen_result["success"]:
            confidence_delta = 0.2
            if quality_notes:
                confidence_delta += 0.1  # Quality review completed
        else:
            confidence_delta = 0.05  # Failed generation still teaches something

        self._update_feature_progress(
            category, feature_name, confidence_delta, knowledge_id,
            credits_spent=credits_spent if not credit_read_suspect else 0,
            generation_time=generation_time,
        )

        if self.audit_log:
            self.audit_log.log(
                "occy", "info", "hands_on",
                f"Hands-on test: {feature_name}",
                details=(
                    f"credits_spent={credits_spent}, "
                    f"time={round(generation_time, 1)}s, "
                    f"success={gen_result['success']}"
                ),
            )

        logger.info(
            f"Hands-on complete: {feature_name} — "
            f"{credits_spent} credits, {round(generation_time, 1)}s, "
            f"success={gen_result['success']}"
        )

        return {
            "success": gen_result["success"],
            "feature": feature_name,
            "credits_spent": credits_spent,
            "generation_time_seconds": round(generation_time, 1),
            "quality_notes": quality_notes,
            "confidence_delta": confidence_delta,
            "overspent": overspent,
        }

    async def run_hands_on_session(
        self, duration_minutes: int = 60, credit_budget: int = 100,
    ) -> dict:
        """
        Run a timed hands-on learning session.

        Selects generative features that have been explored (confidence 0.3-0.7)
        and actually uses them — spending credits to generate real output.

        Stops when:
        - Time runs out
        - Credit budget exhausted
        - Credit balance drops below safety floor
        - All generative features at confidence >= 0.7

        Args:
            duration_minutes: Max session length
            credit_budget: Max total credits to spend across all tests

        Returns:
            dict with features_tested, credits_spent, session summary
        """
        start = datetime.now()
        deadline = start.timestamp() + (duration_minutes * 60)

        features_tested = 0
        total_credits_spent = 0
        tested_features = []
        session_attempted = set()
        browser_restarts = 0

        consecutive_failures = 0

        logger.info(
            f"Starting {duration_minutes}-minute hands-on session "
            f"(budget: {credit_budget} credits)"
        )

        while datetime.now().timestamp() < deadline:
            # Check browser health
            if not await self._ensure_browser_connected():
                logger.error("Browser unrecoverable — ending hands-on session")
                break

            # Check credit budget
            if total_credits_spent >= credit_budget:
                logger.info(
                    f"Credit budget exhausted ({total_credits_spent}/{credit_budget}) "
                    f"— ending hands-on session"
                )
                break

            # Select next feature for hands-on testing
            selection = self._select_next_feature(
                exclude=session_attempted, mode="hands_on"
            )
            if selection is None:
                logger.info("No more features for hands-on testing — ending session")
                break

            category, feature = selection
            session_attempted.add(feature["name"])

            # Per-test budget: remaining budget, capped at a reasonable per-test max
            remaining_budget = credit_budget - total_credits_spent
            per_test_budget = min(remaining_budget, 50)

            logger.info(
                f"Hands-on session: Testing [{category}] {feature['name']} "
                f"(confidence: {feature['confidence']:.1f}, "
                f"budget remaining: {remaining_budget} credits)"
            )

            # Run hands-on test
            result = await self.explore_hands_on(
                category, feature, credit_budget=per_test_budget
            )

            features_tested += 1
            credits_spent = result.get("credits_spent", 0)
            total_credits_spent += credits_spent
            tested_features.append({
                "category": category,
                "feature": feature["name"],
                "success": result["success"],
                "credits_spent": credits_spent,
                "generation_time": result.get("generation_time_seconds", 0),
                "confidence_delta": result.get("confidence_delta", 0),
            })

            # Fix 5: Overspend flag stops session immediately
            if result.get("overspent"):
                logger.warning(
                    f"Feature {feature['name']} overspent — stopping session "
                    f"to prevent further damage"
                )
                break

            # Fix 4: Consecutive failure circuit breaker
            if not result["success"]:
                consecutive_failures += 1
                if consecutive_failures >= 3:
                    logger.warning("3 consecutive failures — ending session early")
                    break
            else:
                consecutive_failures = 0

            # Fix 2: Verify actual credit balance between tests
            actual_balance = await self.browser.get_credit_balance()
            if actual_balance is not None and actual_balance < CREDIT_SAFETY_FLOOR:
                logger.warning(
                    f"Actual credit balance {actual_balance} below safety floor "
                    f"{CREDIT_SAFETY_FLOOR} — ending session"
                )
                break

            # If browser died, try restart
            if not self.browser.is_connected:
                browser_restarts += 1
                if browser_restarts > 3:
                    logger.error("Too many browser restarts — ending hands-on session")
                    break

            # Brief pause between tests
            await asyncio.sleep(3)

        duration_actual = (datetime.now() - start).total_seconds() / 60

        summary = {
            "features_tested": features_tested,
            "total_credits_spent": total_credits_spent,
            "credit_budget": credit_budget,
            "session_duration_minutes": round(duration_actual, 1),
            "browser_restarts": browser_restarts,
            "tested": tested_features,
        }

        logger.info(
            f"Hands-on session complete: {features_tested} features tested, "
            f"{total_credits_spent}/{credit_budget} credits spent, "
            f"{duration_actual:.1f} minutes"
        )

        return summary

    def _update_feature_progress(
        self, category: str, feature_name: str,
        confidence_delta: float, knowledge_id: int = None,
        credits_spent: int = 0, generation_time: float = 0,
    ):
        """Update a feature's confidence, cost history, and tracking info."""
        for feat in self.feature_map.get("categories", {}).get(category, {}).get("features", []):
            if feat["name"] == feature_name:
                feat["confidence"] = min(1.0, feat["confidence"] + confidence_delta)
                feat["explored_count"] = feat.get("explored_count", 0) + 1
                feat["last_explored"] = datetime.now().isoformat()
                if knowledge_id:
                    feat.setdefault("knowledge_ids", []).append(knowledge_id)

                # Track credit costs — builds up over time so Occy knows
                # "GPT Image 1.5 Low costs ~3 credits" off the top of his head
                if credits_spent > 0:
                    cost_history = feat.setdefault("cost_history", [])
                    cost_history.append(credits_spent)
                    # Keep last 20 readings
                    if len(cost_history) > 20:
                        feat["cost_history"] = cost_history[-20:]
                    feat["avg_credit_cost"] = round(
                        sum(feat["cost_history"]) / len(feat["cost_history"]), 1
                    )
                    feat["last_credit_cost"] = credits_spent

                # Track generation times similarly
                if generation_time > 0:
                    time_history = feat.setdefault("time_history", [])
                    time_history.append(round(generation_time, 1))
                    if len(time_history) > 20:
                        feat["time_history"] = time_history[-20:]
                    feat["avg_generation_time"] = round(
                        sum(feat["time_history"]) / len(feat["time_history"]), 1
                    )

                break

        self._save_feature_map()

    async def _ensure_browser_connected(self) -> bool:
        """
        Check browser health and restart if disconnected.

        Returns True if browser is connected (or successfully restarted).
        Returns False if browser is dead and couldn't be restarted.
        """
        if self.browser.is_connected:
            return True

        logger.warning("Browser disconnected — attempting restart...")
        success = await self.browser.restart()

        if success:
            logger.info("Browser restarted — resuming exploration")
            return True
        else:
            logger.error("Browser restart failed — ending exploration session")
            return False

    async def run_exploration_session(self, duration_minutes: int = 30) -> dict:
        """
        Run a timed exploration session.

        Explores features one by one until time runs out.
        Auto-restarts the browser if it disconnects mid-session.

        Returns:
            dict with 'features_explored', 'knowledge_entries', 'total_credits',
            'session_duration_minutes'
        """
        start = datetime.now()
        deadline = start.timestamp() + (duration_minutes * 60)

        features_explored = 0
        knowledge_entries = 0
        total_credits = 0
        explored_features = []
        browser_restarts = 0
        session_attempted = set()  # Track features tried this session to avoid repeats

        logger.info(f"Starting {duration_minutes}-minute exploration session")

        while datetime.now().timestamp() < deadline:
            # Check browser health before each feature
            if not await self._ensure_browser_connected():
                logger.error("Browser unrecoverable — ending session")
                break

            # Select next feature — exclude ones already tried this session
            selection = self._select_next_feature(exclude=session_attempted)
            if selection is None:
                logger.info("No more features to explore — ending session early")
                break

            category, feature = selection
            session_attempted.add(feature["name"])

            logger.info(
                f"Session: Exploring [{category}] {feature['name']} "
                f"(confidence: {feature['confidence']:.1f}) "
                f"[{len(session_attempted)}/{features_explored + 1} this session]"
            )

            # Explore it
            result = await self.explore_feature(category, feature)

            features_explored += 1
            total_credits += result.get("credits_used", 0)
            knowledge_entries += len(result.get("findings", []))
            explored_features.append({
                "category": category,
                "feature": feature["name"],
                "success": result["success"],
                "confidence_delta": result["confidence_delta"],
            })

            # If browser disconnected during exploration, try restart
            if not self.browser.is_connected:
                logger.warning(
                    f"Browser died during exploration of {feature['name']}"
                )
                browser_restarts += 1
                if browser_restarts > 3:
                    logger.error("Too many browser restarts — ending session")
                    break

            # Brief pause between features
            await asyncio.sleep(2)

        duration_actual = (datetime.now() - start).total_seconds() / 60

        summary = {
            "features_explored": features_explored,
            "knowledge_entries": knowledge_entries,
            "total_credits": total_credits,
            "session_duration_minutes": round(duration_actual, 1),
            "browser_restarts": browser_restarts,
            "explored": explored_features,
        }

        logger.info(
            f"Exploration session complete: {features_explored} features, "
            f"{knowledge_entries} knowledge entries, {total_credits} credits, "
            f"{browser_restarts} browser restarts, "
            f"{duration_actual:.1f} minutes"
        )

        return summary

    def document_finding(
        self, category: str, topic: str, content: str, tags: list = None,
    ) -> int:
        """Manually document a finding (for ad-hoc discoveries)."""
        return self.knowledge.add(
            category=category,
            topic=topic,
            content=content,
            source="occy_manual",
            confidence=0.9,
            tags=tags or ["manual_finding"],
        )

    def get_progress(self) -> dict:
        """
        Get exploration progress statistics.

        Returns:
            dict with total features, explored, mastered, by_category breakdown
        """
        total = 0
        explored = 0  # confidence > 0
        proficient = 0  # confidence >= 0.7
        mastered = 0  # confidence >= 0.9
        by_category = {}

        for cat_name, cat_data in self.feature_map.get("categories", {}).items():
            cat_total = 0
            cat_explored = 0
            for feat in cat_data.get("features", []):
                cat_total += 1
                total += 1
                if feat["confidence"] > 0:
                    explored += 1
                    cat_explored += 1
                if feat["confidence"] >= 0.7:
                    proficient += 1
                if feat["confidence"] >= 0.9:
                    mastered += 1

            by_category[cat_name] = {
                "total": cat_total,
                "explored": cat_explored,
                "progress": f"{cat_explored}/{cat_total}",
            }

        return {
            "total_features": total,
            "explored": explored,
            "proficient": proficient,
            "mastered": mastered,
            "progress_pct": round(explored / total * 100, 1) if total > 0 else 0,
            "by_category": by_category,
        }

    def get_cost_sheet(self) -> dict:
        """
        Get Occy's accumulated knowledge of what things cost on Focal ML.

        Returns a dict of feature_name -> cost info, built from real usage.
        This is Occy's "off the top of his head" pricing knowledge.
        """
        costs = {}
        for cat_name, cat_data in self.feature_map.get("categories", {}).items():
            for feat in cat_data.get("features", []):
                if feat.get("avg_credit_cost") is not None:
                    costs[feat["name"]] = {
                        "category": cat_name,
                        "avg_credits": feat["avg_credit_cost"],
                        "last_cost": feat.get("last_credit_cost"),
                        "avg_time_seconds": feat.get("avg_generation_time"),
                        "samples": len(feat.get("cost_history", [])),
                    }
        return costs

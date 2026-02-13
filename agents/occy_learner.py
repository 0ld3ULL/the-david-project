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


class OccyLearner:
    """
    Systematic feature exploration engine for Focal ML.

    Reads the curriculum (what to learn), selects features by priority,
    explores them in the browser, and stores findings in the knowledge base.
    """

    def __init__(self, browser, knowledge_store, audit_log=None):
        """
        Args:
            browser: FocalBrowser instance
            knowledge_store: KnowledgeStore for permanent findings
            audit_log: AuditLog for tracking exploration actions
        """
        self.browser = browser
        self.knowledge = knowledge_store
        self.audit_log = audit_log
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
    ) -> tuple[str, dict] | None:
        """
        Select the next feature to explore.

        Priority order:
        1. Unexplored (confidence 0.0) with highest priority
        2. Partially explored (confidence < 0.5) with highest priority
        3. Job-relevant features (if a job needs specific skills)
        4. Random deep-dive on a known feature

        Args:
            job_relevant: Feature names relevant to a current job
            exclude: Feature names to skip (already attempted this session)

        Returns:
            (category_name, feature_dict) or None if all mastered/excluded
        """
        exclude = exclude or set()

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

        # Only check credit balance if browser is healthy (this is expensive —
        # spawns a full Browser Use agent task)
        credits_before = None
        if self.browser.is_connected:
            credits_before = await self.browser.get_credit_balance()

        # Bail early if browser died during credit check
        if not self.browser.is_connected:
            logger.warning(f"Browser disconnected before exploring {feature_name}")
            self._update_feature_progress(category, feature_name, 0.0)
            return {
                "success": False,
                "findings": ["Browser disconnected before exploration"],
                "confidence_delta": 0.0,
                "credits_used": 0,
            }

        # Step 0: Get course material for context
        course_context = self._get_course_knowledge(feature_name, category)
        if course_context:
            logger.info(f"  Course material found for {feature_name} ({len(course_context)} chars)")

        # Step 1: Navigate to the feature (with course context if available)
        nav_prompt = (
            f"Navigate to the '{feature_name}' feature area in Focal ML. "
            f"This is in the '{category}' category. "
            f"Feature description: {feature['description']}. "
            f"Find and open this feature's UI."
        )
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

            # Store UI mapping
            self.knowledge.add(
                category="technical",
                topic=f"Focal ML UI: {feature_name}",
                content=ui_result["result"][:2000],
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
            # Still save what we have
            if findings:
                self.knowledge.add(
                    category="technical",
                    topic=f"Focal ML feature: {feature_name} (partial)",
                    content="\n".join(findings)[:4000],
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

        # Step 5: Document findings — skip credit balance if browser is unhealthy
        credits_after = None
        if self.browser.is_connected:
            credits_after = await self.browser.get_credit_balance()

        credits_used = 0
        if credits_before is not None and credits_after is not None:
            credits_used = max(0, credits_before - credits_after)

        # Store comprehensive finding
        finding_text = "\n".join(findings)
        knowledge_id = self.knowledge.add(
            category="technical",
            topic=f"Focal ML feature: {feature_name}",
            content=finding_text[:4000],
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

    def _update_feature_progress(
        self, category: str, feature_name: str,
        confidence_delta: float, knowledge_id: int = None,
    ):
        """Update a feature's confidence and tracking info in the feature map."""
        for feat in self.feature_map.get("categories", {}).get(category, {}).get("features", []):
            if feat["name"] == feature_name:
                feat["confidence"] = min(1.0, feat["confidence"] + confidence_delta)
                feat["explored_count"] = feat.get("explored_count", 0) + 1
                feat["last_explored"] = datetime.now().isoformat()
                if knowledge_id:
                    feat.setdefault("knowledge_ids", []).append(knowledge_id)
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

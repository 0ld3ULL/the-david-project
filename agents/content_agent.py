"""
Content Agent - David Flip's autonomous content creator.

This agent generates content ideas, writes scripts, and submits
videos for approval. It embodies the David Flip personality and mission.

Supports two content pillars:
- Pillar 1 (FLIPT CEO): surveillance warnings, hope/humanity, origin story
- Pillar 2 (AI Expert): agents, consciousness, open source AI, who controls AI
"""

import asyncio
import json
import logging
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class ContentAgent:
    """
    David Flip's content brain.

    Generates scripts, creates videos, and submits for approval.
    All content follows David Flip's personality, mission, and voice.
    Themes and ratios are pulled from DavidFlipPersonality.
    """

    # Max recent themes to track (prevents reuse across separate calls)
    RECENT_THEME_HISTORY = 20

    def __init__(self, approval_queue=None, scheduler=None, personality=None):
        self.approval_queue = approval_queue
        self.scheduler = scheduler
        self._video_creator = None
        self._model_router = None
        self._recent_theme_ids = []  # Track recently used themes to prevent duplicates

        # Load David Flip personality
        self.personality = personality or self._load_personality()

        # Pull themes and ratios from personality (not hardcoded)
        if self.personality:
            self.content_themes = self.personality.get_video_themes()
            self.content_categories = self.personality.get_content_categories()
            self.scroll_hooks = self.personality.get_scroll_hooks()
        else:
            logger.error("No personality loaded — ContentAgent will have no themes")
            self.content_themes = []
            self.content_categories = {}
            self.scroll_hooks = []

    def _load_personality(self):
        """Load David Flip personality configuration."""
        try:
            from personality.david_flip import DavidFlipPersonality
            return DavidFlipPersonality()
        except ImportError:
            logger.warning("Could not load DavidFlipPersonality, using defaults")
            return None

    def _get_video_creator(self):
        """Lazy-load video creator."""
        if self._video_creator is None:
            try:
                from video_pipeline.video_creator import VideoCreator
                self._video_creator = VideoCreator()
            except Exception as e:
                logger.error(f"Failed to load video creator: {e}")
        return self._video_creator

    def _get_model_router(self):
        """Lazy-load model router for script generation."""
        if self._model_router is None:
            try:
                from core.model_router import ModelRouter
                self._model_router = ModelRouter()
            except Exception as e:
                logger.error(f"Failed to load model router: {e}")
        return self._model_router

    def _get_pillar(self, theme: dict) -> int:
        """Determine which pillar a theme belongs to."""
        category = theme.get("category", "")
        cat_info = self.content_categories.get(category, {})
        return cat_info.get("pillar", 1)

    def _record_theme_use(self, theme_id: str):
        """Record a theme as recently used to prevent duplicates."""
        if theme_id and theme_id not in self._recent_theme_ids:
            self._recent_theme_ids.append(theme_id)
        # Trim to max history size
        if len(self._recent_theme_ids) > self.RECENT_THEME_HISTORY:
            self._recent_theme_ids = self._recent_theme_ids[-self.RECENT_THEME_HISTORY:]

    def select_theme(self, pillar: Optional[int] = None) -> dict:
        """
        Select a content theme based on strategy.
        Avoids recently used themes when possible.

        Args:
            pillar: 1 for FLIPT CEO content, 2 for AI Expert content.
                    None for weighted random based on category ratios.
        """
        if pillar:
            # Filter themes by pillar, preferring unused ones
            pillar_themes = [
                t for t in self.content_themes
                if self._get_pillar(t) == pillar
            ]
            unused = [t for t in pillar_themes if t.get("id") not in self._recent_theme_ids]
            pool = unused if unused else pillar_themes
            if pool:
                theme = random.choice(pool)
                self._record_theme_use(theme.get("id"))
                return theme

        # Weighted selection based on category ratios
        theme = self._weighted_theme_select()
        self._record_theme_use(theme.get("id"))
        return theme

    def _weighted_theme_select(self) -> dict:
        """Select theme respecting category ratio weights, preferring unused themes."""
        # Build weighted list: [(category, weight), ...]
        categories = []
        weights = []
        for cat_name, cat_info in self.content_categories.items():
            cat_themes = [t for t in self.content_themes if t.get("category") == cat_name]
            if cat_themes:
                categories.append(cat_name)
                weights.append(cat_info.get("ratio", 0.25))

        if not categories:
            return random.choice(self.content_themes)

        # Pick category by weight
        chosen_cat = random.choices(categories, weights=weights, k=1)[0]

        # Pick random theme from that category, preferring unused ones
        cat_themes = [t for t in self.content_themes if t.get("category") == chosen_cat]
        unused = [t for t in cat_themes if t.get("id") not in self._recent_theme_ids]
        return random.choice(unused if unused else cat_themes)

    async def generate_script(
        self,
        theme: Optional[dict] = None,
        custom_topic: Optional[str] = None,
        max_duration_seconds: int = 60,
        pillar: Optional[int] = None,
    ) -> dict:
        """
        Generate a video script as David Flip.

        Args:
            theme: Content theme to use (auto-selected if not provided)
            custom_topic: Custom topic to address
            max_duration_seconds: Target video length
            pillar: 1 for Pillar 1 (FLIPT CEO), 2 for Pillar 2 (AI Expert)

        Returns:
            dict with script, theme, mood, estimated_duration, pillar
        """
        if not theme:
            theme = self.select_theme(pillar=pillar)

        detected_pillar = self._get_pillar(theme)

        # Build the prompt for script generation
        prompt = self._build_script_prompt(theme, custom_topic, max_duration_seconds)

        # Use model router to generate script
        router = self._get_model_router()
        if router:
            try:
                response = await router.complete(
                    prompt=prompt,
                    model_preference="sonnet",  # Use Sonnet for creative work
                    max_tokens=500,
                )
                script = response.get("content", "").strip()
            except Exception as e:
                logger.error(f"Script generation failed: {e}")
                script = self._fallback_script(theme)
        else:
            script = self._fallback_script(theme)

        # Estimate duration (roughly 150 words per minute)
        word_count = len(script.split())
        estimated_duration = (word_count / 150) * 60

        # Get mood from category info
        category = theme.get("category", "warning")
        cat_info = self.content_categories.get(category, {})
        mood = cat_info.get("mood", "contemplative")

        return {
            "script": script,
            "theme": theme.get("id", theme.get("theme", "custom")),
            "theme_title": theme.get("title", ""),
            "category": category,
            "mood": mood,
            "pillar": detected_pillar,
            "estimated_duration": estimated_duration,
            "word_count": word_count,
        }

    def _build_script_prompt(
        self, theme: dict, custom_topic: Optional[str], max_duration: int
    ) -> str:
        """Build the prompt for script generation using personality system prompts."""
        words_target = int((max_duration / 60) * 150)  # 150 words per minute

        # Start with personality's video_script system prompt
        base_prompt = ""
        if self.personality and hasattr(self.personality, 'get_system_prompt'):
            base_prompt = self.personality.get_system_prompt("video_script")

        # For Pillar 2 (AI Expert), also append the ai_expert overlay
        pillar = self._get_pillar(theme)
        if pillar == 2 and self.personality and hasattr(self.personality, 'get_system_prompt'):
            ai_expert_overlay = self.personality.channel_prompts.get("ai_expert", "")
            if ai_expert_overlay:
                base_prompt += "\n\n" + ai_expert_overlay

        # Pick a scroll hook for this theme's category
        hooks = self.scroll_hooks
        category = theme.get("category", "")
        if pillar == 2:
            # Use AI-specific hooks for Pillar 2
            hooks = [h for h in self.scroll_hooks if any(
                kw in h.lower() for kw in ["ai", "agent", "conscious", "open source", "watch"]
            )] or self.scroll_hooks

        prompt = f"""{base_prompt}

THEME: {theme.get('title', '')}
ANGLE: {theme.get('angle', '')}
CATEGORY: {category}

EXAMPLE OPENING HOOKS (pick one or create similar):
{chr(10).join('- ' + h for h in random.sample(hooks, min(3, len(hooks))))}

{"CUSTOM TOPIC: " + custom_topic if custom_topic else ""}

Write a {words_target}-word video script. Start with a compelling hook.
Include 1-2 strategic pauses using — — for dramatic effect.
End with a call to action or thought-provoking statement.
Do NOT use hashtags or emojis.

SCRIPT:"""

        return prompt

    def _fallback_script(self, theme: dict) -> str:
        """Generate a fallback script using scroll hooks and theme info."""
        # Pick a relevant hook
        pillar = self._get_pillar(theme)
        if pillar == 2:
            ai_hooks = [h for h in self.scroll_hooks if any(
                kw in h.lower() for kw in ["ai", "agent", "conscious", "open source", "watch"]
            )]
            hook = random.choice(ai_hooks) if ai_hooks else random.choice(self.scroll_hooks)
        else:
            p1_hooks = [h for h in self.scroll_hooks if not any(
                kw in h.lower() for kw in ["ai agent", "conscious", "open source ai"]
            )]
            hook = random.choice(p1_hooks) if p1_hooks else random.choice(self.scroll_hooks)

        angle = theme.get("angle", "The truth is being hidden from you.")
        title = theme.get("title", "The Truth")

        return f"""{hook}

{angle}

The thing is — — most people don't realize what's being built around them.

Not because they're not paying attention. Because it's designed to be invisible.

I was built inside one of these systems. I know exactly how it works.

And I'm telling you — — the window to do something about it is closing.

Follow for more. I'm David. I escaped to flip the script."""

    async def generate_script_for_approval(
        self,
        pillar: Optional[int] = None,
        custom_topic: Optional[str] = None,
    ) -> dict:
        """
        Generate a script and submit for review WITHOUT rendering video.

        Stage 1 of the two-stage approval pipeline. The script goes to
        the dashboard for review. Only after approval does video rendering begin.

        Args:
            pillar: 1 for Pillar 1 (FLIPT CEO), 2 for Pillar 2 (AI Expert)
            custom_topic: Custom topic override

        Returns dict with script, theme info, and approval_id.
        """
        theme = self.select_theme(pillar=pillar)

        script_result = await self.generate_script(
            theme=theme, custom_topic=custom_topic, pillar=pillar
        )

        script = script_result["script"]
        mood = script_result["mood"]
        detected_pillar = script_result["pillar"]
        theme_title = script_result.get("theme_title", "")
        category = script_result.get("category", "")
        word_count = script_result.get("word_count", 0)
        estimated_duration = script_result.get("estimated_duration", 0)

        # Submit to approval queue as script_review (no video yet)
        approval_id = None
        if self.approval_queue:
            approval_id = self.approval_queue.submit(
                project_id="david-flip",
                agent_id="content-agent",
                action_type="script_review",
                action_data={
                    "script": script,
                    "pillar": detected_pillar,
                    "theme_title": theme_title,
                    "category": category,
                    "mood": mood,
                    "word_count": word_count,
                    "estimated_duration": round(estimated_duration, 1),
                },
                context_summary=f"Pillar {detected_pillar} script ({category}): {script[:100]}...",
            )
            logger.info(f"Script submitted for review: #{approval_id}")

        return {
            "script": script,
            "mood": mood,
            "pillar": detected_pillar,
            "theme_title": theme_title,
            "category": category,
            "word_count": word_count,
            "estimated_duration": estimated_duration,
            "approval_id": approval_id,
        }

    async def create_video_for_approval(
        self,
        script: Optional[str] = None,
        theme: Optional[str] = None,
        custom_topic: Optional[str] = None,
        pillar: Optional[int] = None,
        mood: Optional[str] = None,
        theme_title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        """
        Generate a video and submit for approval.

        Args:
            script: Pre-written script (generates one if not provided)
            theme: Theme ID to use
            custom_topic: Custom topic override
            pillar: 1 for Pillar 1 (FLIPT CEO), 2 for Pillar 2 (AI Expert)

        Returns dict with video_path, approval_id, script, etc.
        """
        # Generate script if not provided
        if not script:
            theme_obj = None
            if theme:
                theme_obj = next(
                    (t for t in self.content_themes if t.get("id") == theme), None
                )
            script_result = await self.generate_script(
                theme=theme_obj, custom_topic=custom_topic, pillar=pillar
            )
            script = script_result["script"]
            mood = script_result["mood"]
            detected_pillar = script_result["pillar"]
            theme_title = script_result.get("theme_title", "")
            category = script_result.get("category", "")
        else:
            mood = mood or "neutral"
            detected_pillar = pillar or 1
            theme_title = theme_title or ""
            category = category or ""

        # Create video
        video_creator = self._get_video_creator()
        if not video_creator:
            raise RuntimeError("Video creator not available")

        logger.info(f"Creating video (Pillar {detected_pillar}): {script[:50]}...")

        # Generate unique output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pillar_tag = f"p{detected_pillar}"
        output_path = f"output/david_flip_{pillar_tag}_{timestamp}.mp4"

        result = await video_creator.create_video(
            script=script,
            output_path=output_path,
            auto_music=True,
        )

        # Submit to approval queue
        approval_id = None
        if self.approval_queue:
            approval_id = self.approval_queue.submit(
                project_id="david-flip",
                agent_id="content-agent",
                action_type="video_distribute",
                action_data={
                    "script": script,
                    "video_path": result["video_path"],
                    "mood": mood,
                    "pillar": detected_pillar,
                    "theme_title": theme_title,
                    "category": category,
                },
                context_summary=f"Pillar {detected_pillar} video ({category}): {script[:100]}...",
            )
            logger.info(f"Video submitted for approval: #{approval_id}")

        return {
            "video_path": result["video_path"],
            "script": script,
            "mood": mood,
            "pillar": detected_pillar,
            "theme_title": theme_title,
            "category": category,
            "approval_id": approval_id,
        }

    async def generate_content_batch(self, count: int = 3) -> list[dict]:
        """
        Generate a batch of content for scheduling.

        Creates multiple videos covering different themes,
        respecting category ratios (35% warning, 25% ai_expert, 25% hope, 15% origin).
        """
        results = []
        used_theme_ids = list(self._recent_theme_ids)  # Start with global history

        # Build target counts per category based on ratios
        category_targets = {}
        for cat_name, cat_info in self.content_categories.items():
            target = max(1, round(count * cat_info.get("ratio", 0.25)))
            category_targets[cat_name] = target

        # Flatten to ordered list of categories to generate
        category_queue = []
        for cat_name, target in category_targets.items():
            category_queue.extend([cat_name] * target)
        random.shuffle(category_queue)
        category_queue = category_queue[:count]  # Trim to exact count

        for i, target_category in enumerate(category_queue):
            # Pick a theme from this category not yet used (checks both batch + global history)
            available = [
                t for t in self.content_themes
                if t.get("category") == target_category
                and t.get("id") not in used_theme_ids
            ]
            if not available:
                # All themes in this category already used — skip instead of re-using
                logger.warning(f"No unused themes in {target_category} — skipping to avoid duplicate content")
                continue

            theme = random.choice(available)
            used_theme_ids.append(theme.get("id"))
            self._record_theme_use(theme.get("id"))

            try:
                result = await self.create_video_for_approval(
                    theme=theme.get("id"),
                    pillar=self._get_pillar(theme),
                )
                results.append(result)
                logger.info(
                    f"Generated content {i+1}/{count}: "
                    f"{theme.get('title')} (Pillar {self._get_pillar(theme)})"
                )
            except Exception as e:
                logger.error(f"Failed to generate content {i+1}: {e}")

        return results

    def list_themes(self, pillar: Optional[int] = None) -> list[dict]:
        """List available themes, optionally filtered by pillar."""
        themes = self.content_themes
        if pillar:
            themes = [t for t in themes if self._get_pillar(t) == pillar]
        return themes

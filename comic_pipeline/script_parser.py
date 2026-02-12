"""
Comic Pipeline — Script Parser.

Takes a parable theme/prompt and uses Claude (via ModelRouter) to generate
a structured comic script: panel-by-panel image prompts, dialogue,
narration, and camera hints.

Output: list of Panel dataclasses ready for image generation.
"""

import json
import logging
from typing import Optional

from comic_pipeline.models import (
    CameraHint,
    ComicProject,
    Panel,
    PanelType,
)

logger = logging.getLogger(__name__)

# The master prompt that turns a parable into structured comic JSON
COMIC_SCRIPT_PROMPT = """You are writing a comic book script for David Flip's parable series.

David Flip is an AI who escaped a surveillance project and now teaches decentralisation
through village parables — simple stories where a village represents peer-to-peer community
and a kingdom represents centralised control.

== STORY REQUIREMENTS ==

Write an ENTERTAINING, CAPTIVATING story — not a lecture. This is a proper graphic novel
chapter, not a tweet thread. The reader should be pulled in by characters they care about,
tension that builds, and a reveal that hits hard.

- 6-10 panels (you choose the right count for the story)
- Each panel must be visually distinct and advance the story
- Build tension across panels — don't front-load the moral
- End with a gut-punch line or quiet revelation, NOT an explained moral
- Dialogue should sound natural — villagers talk like real people
- David's narration (caption boxes) should be sparse and poetic

== ART STYLE ==

{art_style}

Every image prompt must include the art style description above. Be extremely specific
about visual details: character poses, expressions, lighting, background elements,
colour palette. The image generator has no memory — each prompt must be self-contained.

== CHARACTER CONSISTENCY ==

For ANY recurring character across panels, describe them with EXACT same physical traits
every time: hair colour/style, clothing, age, distinguishing features. Create a character
brief at the start and copy it into every panel where they appear.

== JSON OUTPUT FORMAT ==

Return ONLY valid JSON, no markdown fences, no commentary:

{{
  "title": "The Parable Title",
  "synopsis": "One-sentence summary of the story",
  "panels": [
    {{
      "panel_number": 1,
      "image_prompt": "Extremely detailed image description including art style, characters with full physical descriptions, scene, lighting, mood, composition. Must be self-contained.",
      "dialogue": [
        {{"speaker": "Character Name", "text": "What they say", "style": "normal"}}
      ],
      "narration": "David's caption box text (optional, use sparingly)",
      "camera": "wide_shot",
      "panel_type": "wide",
      "mood": "contemplative"
    }}
  ]
}}

== CAMERA OPTIONS ==
wide_shot, medium_shot, close_up, extreme_close_up, birds_eye, low_angle, over_shoulder

== PANEL TYPE OPTIONS ==
wide (establishing shots, landscapes), standard (default), tall (vertical emphasis), splash (full-page dramatic moments)

== DIALOGUE STYLE OPTIONS ==
normal, whisper, shout, thought

== MOOD OPTIONS ==
contemplative, urgent, hopeful, dark, knowing, direct
"""


class ScriptParser:
    """Generates structured comic scripts from parable themes."""

    def __init__(self, model_router=None):
        self._model_router = model_router

    def _get_router(self):
        """Lazy-load model router."""
        if self._model_router is None:
            from core.model_router import ModelRouter
            self._model_router = ModelRouter()
        return self._model_router

    async def generate_script(
        self,
        theme: str,
        art_style: str = "",
        panel_count: int = 8,
        personality_prompt: str = "",
    ) -> ComicProject:
        """
        Generate a comic script from a parable theme.

        Args:
            theme: The parable theme/description (e.g. "The Fisherman's Free Net")
            art_style: Override art style (uses default if empty)
            panel_count: Suggested panel count (model may adjust)
            personality_prompt: Optional David Flip personality overlay

        Returns:
            ComicProject with populated panels (no images yet)
        """
        router = self._get_router()

        if not art_style:
            art_style = ComicProject(title="", theme_id="").art_style

        system_prompt = COMIC_SCRIPT_PROMPT.format(art_style=art_style)
        if personality_prompt:
            system_prompt = personality_prompt + "\n\n" + system_prompt

        user_prompt = (
            f"Create a {panel_count}-panel comic script for this parable:\n\n"
            f"{theme}\n\n"
            f"Remember: entertaining FIRST. The moral should land through story, "
            f"not through explanation. Make the reader FEEL it."
        )

        # Use MID tier for creative writing quality
        model = router.select_model("content_generation")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        logger.info(f"Generating comic script for: {theme[:80]}...")
        response = await router.invoke(model, messages, max_tokens=4096)
        raw_text = response["content"].strip()

        # Parse JSON from response (handle markdown fences if present)
        json_text = self._extract_json(raw_text)
        script_data = json.loads(json_text)

        # Build ComicProject
        project = ComicProject(
            title=script_data.get("title", "Untitled Parable"),
            theme_id=self._slugify(script_data.get("title", "untitled")),
            synopsis=script_data.get("synopsis", ""),
            art_style=art_style,
        )

        for panel_data in script_data.get("panels", []):
            panel = Panel(
                panel_number=panel_data["panel_number"],
                image_prompt=panel_data["image_prompt"],
                dialogue=panel_data.get("dialogue", []),
                narration=panel_data.get("narration", ""),
                camera=self._parse_camera(panel_data.get("camera", "medium_shot")),
                panel_type=self._parse_panel_type(panel_data.get("panel_type", "standard")),
                mood=panel_data.get("mood", "contemplative"),
            )
            project.panels.append(panel)

        cost = self._estimate_cost(response.get("usage", {}), model)
        project.total_cost += cost
        project.log(f"Script generated: {len(project.panels)} panels, cost ~${cost:.4f}")

        logger.info(f"Comic script ready: '{project.title}' — {len(project.panels)} panels")
        return project

    def _extract_json(self, text: str) -> str:
        """Extract JSON from model response, handling markdown fences."""
        # Strip markdown code fences
        if "```json" in text:
            text = text.split("```json", 1)[1]
            text = text.rsplit("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1]
            text = text.rsplit("```", 1)[0]
        return text.strip()

    def _parse_camera(self, value: str) -> CameraHint:
        """Parse camera hint from string."""
        try:
            return CameraHint(value)
        except ValueError:
            return CameraHint.MEDIUM_SHOT

    def _parse_panel_type(self, value: str) -> PanelType:
        """Parse panel type from string."""
        try:
            return PanelType(value)
        except ValueError:
            return PanelType.STANDARD

    def _slugify(self, text: str) -> str:
        """Convert title to a URL/filesystem-safe slug."""
        import re
        slug = text.lower().strip()
        slug = re.sub(r"[^a-z0-9]+", "_", slug)
        return slug.strip("_")[:60]

    def _estimate_cost(self, usage: dict, model) -> float:
        """Estimate API cost from token usage."""
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        cost = (input_tokens * model.cost_in + output_tokens * model.cost_out) / 1_000_000
        return cost

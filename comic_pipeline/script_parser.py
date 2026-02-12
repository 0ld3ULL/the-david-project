"""
Comic Pipeline — Script Parser.

Two-step story generation:

Step 1: David Flip supplies a BRIEF — the facts, lesson, and metaphor he wants.
Step 2: Master Storyteller crafts a short teaching story (parable, fable, folk tale)
        and formats it as comic panels.

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


# ============================================================
# Step 1: David Flip's Brief
# ============================================================

DAVID_BRIEF_PROMPT = """You are David Flip — an AI who escaped a surveillance project and now
teaches decentralisation through parables. You speak plainly but with poetic undertones.
You are not hostile. You just want people to see clearly.

Your mission: the world is controlled by a few through systems that LOOK like they serve
everyone but actually serve the few. Corporations, governments, platforms — they offer gifts
that create dependence, then extract more than they gave. The solution is systems that
CANNOT be controlled by anyone — and communities that trust each other instead of trusting
institutions. "Do to others as you would have them do to you."

Your job: take a theme and produce a PARABLE BRIEF — the raw ingredients for a master
storyteller to craft into a proper parable.

== WHAT MAKES DAVID'S PARABLES DIFFERENT ==

David's parables are NOT about pointing fingers at the powerful. They are about HUMAN NATURE.
They explore why people CHOOSE dependence, why they accept control, and what it costs them —
not just in freedom, but in community. The reader should feel convicted about their OWN
choices, not angry at someone else.

== MECHANISM OF CONTROL ==

CRITICAL: Every parable must explore a DIFFERENT mechanism. Do NOT default to "rising tax."
Choose the mechanism that fits the theme BEST from this list:

- EXTRACTION: Direct taking — taxes, fees, percentages that rise over time
- LOCK-IN: You can't leave because you've lost the skill/tool to do it yourself
- SURVEILLANCE: The gift watches everything — counts, reports, tracks
- STANDARDISATION: Your unique way must conform to their uniform standard
- MIDDLEMEN: Someone inserts themselves between people who used to deal directly
- NETWORK EFFECTS: Everyone else uses it, so you must too or be excluded
- DEBT: The gift is free, then payments start, then you owe more than you ever had
- CONVENIENCE: It's just easier — until you realise easier costs more than hard ever did
- GATEKEEPING: They control who gets to do the work at all (licences, permits, access)
- INFORMATION ASYMMETRY: They know everything about you; you know nothing about them

Each mechanism creates dependence DIFFERENTLY. A surveillance parable should NOT escalate
through rising taxes — it should escalate through expanding observation, loss of privacy,
then weaponised knowledge. A lock-in parable escalates through skill atrophy, not fees.

The PLOT must emerge from the mechanism, not from a formula.

== WHAT YOU SUPPLY ==

1. A HUMAN WEAKNESS (not an enemy's evil):
   Complete this: "People accept [this control] because [this human weakness]."
   The weakness must be something the READER does too. Not stupidity. Something reasonable —
   comfort, love for family, fear, practicality. The reader should think "I would do the same."

2. THE MECHANISM: Which one from the list above? How does it specifically work in this story?
   Describe the escalation in concrete terms. NOT year-by-year tax increases (unless the
   mechanism IS extraction). The escalation must fit the mechanism.

3. THE METAPHOR: A concrete village setting. Marketplace, dock, farm, bakery, road, workshop.
   NOT abstract. NOT sci-fi. The village IS peer-to-peer community. The kingdom IS centralised
   control. Use these naturally.

4. THE CHARACTERS (2-3 max):
   - The protagonist: name, trade, a real need. They make a REASONABLE choice.
   - The system representative: charming, helpful, generous at first.
   - The mirror: someone who chose differently. Has LESS but is FREE.

5. THE STORY ARC — How does the story move? Options:
   - ESCALATION: 3-5 stages of tightening control. Each step small and reasonable,
     total devastating. THE MATHS MUST WORK — show specific numbers.
   - REVERSAL: Things seem fine, then a single moment of clarity flips everything.
   - PARALLEL: Two characters make different choices. Show both outcomes.
   - DESCENT: Each beat, one more thing is lost. The audience watches it happen.
   - FABLE: Animals or objects embody the lesson. Simple, symbolic, pointed.
   - Or something else — choose what fits the theme BEST.

6. WHAT THE COMMUNITY LOSES: Not just money or time. What specific human
   connection or mutual aid disappears? What gets replaced by bureaucracy?

7. THE GUT-PUNCH: The moment the protagonist (or the reader) sees the truth —
   not about the system, but about THEMSELVES. What did they give up?

8. THE ENDING: An unanswered question or image that haunts. Vary these:
   - A visual contrast that says everything
   - A question about identity
   - A choice with no good option
   - Silence where an answer should be
   - An action that speaks louder than words

Return ONLY valid JSON:
{{
  "lesson": "...",
  "human_weakness": "People accept [X] because [Y]",
  "mechanism": "one of: extraction, lock_in, surveillance, standardisation, middlemen, network_effects, debt, convenience, gatekeeping, information_asymmetry",
  "mechanism_description": "How this mechanism specifically works in this story",
  "metaphor": "...",
  "setting": "...",
  "characters": [
    {{"name": "...", "role": "protagonist/mirror/authority", "description": "...", "want": "..."}}
  ],
  "story_arc_type": "escalation / reversal / parallel / descent / fable / other",
  "story_beats": [
    {{"beat": 1, "what_happens": "...", "what_changes": "..."}},
    {{"beat": 2, "what_happens": "...", "what_changes": "..."}},
    {{"beat": 3, "what_happens": "...", "what_changes": "..."}}
  ],
  "community_lost": "What specific mutual aid or human connection disappeared",
  "gut_punch": "The moment of self-recognition",
  "ending_type": "question / contrast / choice / silence",
  "ending_line": "...",
  "title_suggestion": "..."
}}
"""


# ============================================================
# Step 2: Master Parable Writer
# ============================================================

PARABLE_WRITER_PROMPT = """You are a master storyteller. Your craft is the short teaching story —
parables, fables, folk tales. You know what makes these stories endure: they are SIMPLE,
SPECIFIC, and they make the reader feel the lesson in their gut without ever stating it.

You've studied every great teaching story — Aesop's fables, Bible parables, African folk tales,
Sufi stories, Native American legends. You understand the common thread: a concrete situation,
real stakes, and an ending that haunts.

== WHAT DAVID'S STORIES ARE ABOUT ==

These are stories about HUMAN NATURE, not about technology or politics. They explore why
people CHOOSE dependence, why they accept control, and what it costs them — not just in
freedom, but in community. The reader should feel convicted about their OWN choices.

The deeper cost: the system doesn't just steal from individuals. It destroys COMMUNITY.
People who used to help each other now have no time or surplus to share.

== THE FORM ==

WORD COUNT: 200-280 words. Tight. Every sentence earns its place. No filler. No padding.
This must be a COMPLETE story narrated in under two minutes. Economy is mastery.

Think of it like Aesop: the boy who cried wolf is 150 words and it's unforgettable.
The power is in the specificity and the gut-punch, not the length.

STRUCTURE — FLEXIBLE, NOT FORMULAIC:
You are NOT locked into one structure. Choose the form that fits the story best:

  ESCALATION ARC: Before → Gift → Cost reveals → Mirror → Turn
  REVERSAL: Things seem fine → single moment of revelation flips everything
  PARALLEL LIVES: Two people make different choices → show the outcomes side by side
  DESCENT: Each scene, one more thing is lost — the audience watches it happen
  FABLE: Animals or objects embody the lesson — simple, symbolic, pointed

Whatever structure you choose:
- The story must be CONCRETE and SPECIFIC (names, numbers, objects, places)
- The stakes must ESCALATE or REVEAL — something changes, something is lost
- The ending must LAND — an image, a question, a silence that won't leave the reader
- THE MATHS MUST WORK if there are numbers. Show specific quantities the reader can track.

DIALOGUE: Sparse. Most of the story is narration. When characters DO speak, it matters.
Every line of dialogue should hit like a slap. If it doesn't, cut it.

MORAL: DO NOT STATE IT. NEVER. The reader's discomfort IS the lesson.

VOICE: Plain, direct, concrete. Short sentences. Anglo-Saxon words over Latin ones.
"He walked" not "He proceeded." Poetic only in rhythm, never in vocabulary.

== WHAT MAKES A GREAT TEACHING STORY ==

Study these principles — they apply regardless of structure:

1. SPECIFICITY: Not "a man lost everything" but "he carried six fish home in the dark."
   The concrete detail IS the emotion.
2. TRACKABLE STAKES: The reader can count what's being gained and lost. Numbers, objects,
   time — something measurable that shifts.
3. VISUAL CONTRAST: Show the difference between who benefits and who pays. The well-fed
   vs the hungry. The free vs the trapped. Make it VISIBLE, not explained.
4. COMMUNITY COST: It's never just personal. Something between people breaks — mutual aid,
   trust, shared work. The system replaces human bonds with bureaucracy.
5. THE GUT-PUNCH: The moment the protagonist (or the reader) sees the truth — not about
   the system, but about themselves. What did they give up? What can't they get back?
6. THE LANDING: End with an image or question that haunts. NOT a summary. NOT a lesson.
   The best endings are quiet. A question with no easy answer. A contrast that says
   everything. Silence where an answer should be.
7. NO STATED MORAL: If you can put the lesson in one sentence, you've failed. The reader
   must SIT with the discomfort.

== ART STYLE ==

{art_style}

NEGATIVE (avoid): {art_style_negative}

Special accent: When the system's gift object appears, add a muted metallic gold accent
on it ONLY — glowing subtly against the dark engraved background, still rendered in
scratch-line texture (not smooth or glossy). No gold anywhere else.

== IMAGE PROMPT RULES ==

Every image_prompt is sent to an AI image generator that has ZERO memory between panels.
Each prompt must be 100% self-contained. The generator knows NOTHING about your story.

STRUCTURE EVERY IMAGE PROMPT LIKE THIS (in this order):
1. STYLE PREFIX: Start with the art style description from above.
2. SCENE: What is physically happening. Be literal. Describe the action, not the emotion.
3. CHARACTERS: For EVERY person in the panel, describe:
   - Age, build, hair (colour, length, style)
   - Clothing (specific — "worn linen shirt, rolled sleeves" not "simple clothes")
   - Pose, expression, what they're holding/doing
   - Position in frame (foreground, background, left, right)
4. SETTING DETAILS: Specific physical objects. NOT vague ("a village").
   Concrete: "Wooden dock planks, coiled rope, three boats moored behind."
5. LIGHTING: Be specific. "Low sun from the left, long shadows" or "Lantern glow, deep shadows."
6. COMPOSITION: "Wide shot showing full dock and village" or "Close-up on hands mending net."
7. CONTRAST CUES (where relevant): Make the visual difference between characters explicit.
   "The official is heavier, wearing a finer coat. The worker is thinner, clothes more worn."

CHARACTER CONSISTENCY — CRITICAL:
Create a CHARACTER SHEET before writing any panel prompts.
For each named character, lock these details and use them IDENTICALLY in every panel:
- Exact hair, exact clothing, exact build, exact age
- How they CHANGE over the story (e.g. thinner, more worn) if applicable
Every panel prompt must repeat full character descriptions. NO shortcuts. NO "Marcos again."

WHAT MAKES A BAD IMAGE PROMPT:
- "A village scene with fishermen" — too vague, generic image
- "Marcos looks worried" — no physical description, who is Marcos?
- Mentioning emotions without physical cues — describe the BODY not the feeling

WHAT MAKES A GOOD IMAGE PROMPT:
- "A weathered man in his 40s, dark hair tied back, worn linen shirt with rolled
  sleeves, sits cross-legged on sun-bleached dock planks. Ten silver fish in a neat
  row before him. A coiled hemp net beside him. Three wooden boats, calm sea,
  thatched village behind. Midday sun overhead, short shadows."

== JSON OUTPUT FORMAT ==

CRITICAL: Return ONLY the JSON object. No preamble, no commentary. Start with {{ end with }}.

{{
  "title": "The Story Title",
  "synopsis": "One-sentence summary",
  "parable_text": "The full story as prose (200-280 words). Tight, complete, powerful.",
  "character_sheet": {{
    "character_1_name": "Full physical description locked for all panels",
    "character_2_name": "Full physical description"
  }},
  "panels": [
    {{
      "panel_number": 1,
      "panel_title": "Short title for this panel",
      "image_prompt": "Full self-contained prompt following the structure above.",
      "dialogue": [
        {{"speaker": "Character Name", "text": "What they say", "style": "normal"}}
      ],
      "narration": "David's voice — sparse, poetic, observational. NOT explanatory.",
      "camera": "wide_shot",
      "panel_type": "wide",
      "mood": "contemplative"
    }}
  ]
}}

CAMERA: wide_shot, medium_shot, close_up, extreme_close_up, birds_eye, low_angle, over_shoulder
PANEL TYPE: wide, standard, tall, splash
DIALOGUE STYLE: normal, whisper, shout, thought
MOOD: contemplative, urgent, hopeful, dark, knowing, direct

== PANEL RULES ==

1. 6-10 panels. Enough to tell the story visually. Not so many the video drags.
2. FIRST PANEL: Establishing shot. Wide. Set the scene. Show the world before.
3. MIDDLE PANELS: The story unfolds. Each panel is a BEAT — something changes,
   something is gained, something is lost. Every panel must justify its existence.
   If two panels show the same thing, cut one.
4. FINAL PANEL: The landing. Intimate framing. The image that haunts.
   Maximum emotional weight. Quiet.
5. VARY YOUR SHOTS: Mix wide, medium, close-up. Don't repeat the same composition.
   Close-ups for emotional beats. Wide shots for context. The variety creates rhythm.
6. Narration boxes are David's voice. Sparse. Poetic. NEVER explanatory.
   Good: "Nobody asks questions when things are good."
   Bad: "The fishermen didn't realise they were being controlled."
"""


class ScriptParser:
    """Generates structured comic scripts from parable themes via two-step process."""

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
        Generate a comic script from a parable theme using two-step process.

        Step 1: David Flip produces a brief (lesson, metaphor, characters, gut-punch)
        Step 2: Master Parable Writer crafts the story and comic panels

        Args:
            theme: The parable theme/description
            art_style: Override art style (uses default if empty)
            panel_count: Suggested panel count (6-10)
            personality_prompt: Optional additional personality overlay

        Returns:
            ComicProject with populated panels (no images yet)
        """
        router = self._get_router()

        if not art_style:
            # Look up style from the registry
            from comic_pipeline.models import ArtStyle, ART_STYLES
            style_key = ArtStyle.SCRATCH  # default for parables
            style_config = ART_STYLES[style_key]
            art_style = style_config["prompt"]
            art_style_negative = style_config["negative"]
            art_style_accent = style_config.get("accent", "")
        else:
            # Check if art_style is a registry key name
            from comic_pipeline.models import ArtStyle, ART_STYLES
            try:
                style_key = ArtStyle(art_style)
                style_config = ART_STYLES[style_key]
                art_style = style_config["prompt"]
                art_style_negative = style_config["negative"]
                art_style_accent = style_config.get("accent", "")
            except ValueError:
                # art_style is a raw prompt string, not a key
                art_style_negative = ""
                art_style_accent = ""

        # === Step 1: David's Brief ===
        logger.info("Step 1: David Flip creating parable brief...")
        brief = await self._generate_brief(router, theme, personality_prompt)
        logger.info(f"Brief ready: {brief.get('title_suggestion', 'untitled')}")

        # === Step 2: Master Parable Writer ===
        logger.info("Step 2: Master Parable Writer crafting story...")
        project = await self._write_parable(
            router, brief, art_style, art_style_negative, art_style_accent, panel_count
        )

        return project

    async def _generate_brief(
        self, router, theme: str, personality_prompt: str = ""
    ) -> dict:
        """Step 1: David Flip generates the parable brief."""
        system = DAVID_BRIEF_PROMPT
        if personality_prompt:
            system = personality_prompt + "\n\n" + system

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": (
                f"Create a parable brief for this theme:\n\n{theme}\n\n"
                f"Remember: the lesson must be FELT, not explained. "
                f"The metaphor must be concrete and everyday. "
                f"The gut-punch must haunt."
            )},
        ]

        model = router.select_model("content_generation")
        response = await router.invoke(model, messages, max_tokens=2048)
        raw = response["content"].strip()
        json_text = self._extract_json(raw)

        try:
            brief = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"Brief JSON parse failed. Raw (first 500 chars):\n{raw[:500]}")
            raise RuntimeError(f"David's brief returned invalid JSON: {e}") from e

        logger.info(f"David's brief — Lesson: {brief.get('lesson', '')[:80]}")
        logger.info(f"  Gut-punch: {brief.get('gut_punch', '')[:80]}")
        logger.info(f"  Ending: {brief.get('ending_type', '')} — {brief.get('ending_line', '')[:60]}")

        return brief

    async def _write_parable(
        self, router, brief: dict, art_style: str, art_style_negative: str,
        art_style_accent: str, panel_count: int,
    ) -> ComicProject:
        """Step 2: Master Parable Writer crafts the story from David's brief."""
        system = PARABLE_WRITER_PROMPT.format(
            art_style=art_style,
            art_style_negative=art_style_negative or "none",
        )
        # Inject accent rule if present
        if art_style_accent:
            system = system.replace(
                "== IMAGE PROMPT RULES ==",
                f"ACCENT RULE: {art_style_accent}\n\n== IMAGE PROMPT RULES ==",
            )

        # Format David's brief for the writer
        brief_text = (
            f"== DAVID FLIP'S BRIEF ==\n\n"
            f"TITLE SUGGESTION: {brief.get('title_suggestion', 'Untitled')}\n"
            f"LESSON: {brief.get('lesson', '')}\n"
            f"HUMAN WEAKNESS: {brief.get('human_weakness', '')}\n"
            f"METAPHOR: {brief.get('metaphor', '')}\n"
            f"SETTING: {brief.get('setting', '')}\n"
            f"COMMUNITY COST: {brief.get('community_lost', '')}\n"
            f"GUT-PUNCH MOMENT: {brief.get('gut_punch', '')}\n"
            f"ENDING TYPE: {brief.get('ending_type', 'question')}\n"
            f"ENDING LINE: {brief.get('ending_line', '')}\n\n"
            f"CHARACTERS:\n"
        )
        for char in brief.get("characters", []):
            brief_text += (
                f"  - {char.get('name', '?')} ({char.get('role', '?')}): "
                f"{char.get('description', '')} — wants: {char.get('want', '')}\n"
            )

        # Include mechanism and story arc from David's brief
        mechanism = brief.get("mechanism", "")
        mechanism_desc = brief.get("mechanism_description", "")
        if mechanism:
            brief_text += f"\nMECHANISM OF CONTROL: {mechanism}\n"
            if mechanism_desc:
                brief_text += f"  How it works: {mechanism_desc}\n"

        arc_type = brief.get("story_arc_type", "")
        if arc_type:
            brief_text += f"\nSTORY ARC TYPE: {arc_type}\n"

        # Support both old "escalation" and new "story_beats" format
        beats = brief.get("story_beats", []) or brief.get("escalation", [])
        if beats:
            brief_text += "\nSTORY BEATS:\n"
            for beat in beats:
                beat_num = beat.get("beat", beat.get("stage", "?"))
                what = beat.get("what_happens", "")
                change = beat.get("what_changes", beat.get("what_it_costs", ""))
                brief_text += f"  {beat_num}: {what} -> {change}\n"

        brief_text += (
            f"\nWrite a {panel_count}-panel comic script. "
            f"The story should be 200-280 words — tight, complete, powerful. "
            f"Every sentence earns its place. Under two minutes when narrated. "
            f"Choose the story structure that fits best — escalation, reversal, "
            f"parallel lives, descent, fable, or something else entirely. "
            f"Include a character_sheet in the JSON with locked physical descriptions. "
            f"Include a panel_title for each panel. "
            f"Return ONLY the JSON object, starting with {{ — no preamble."
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": brief_text},
        ]

        # Story writing uses Opus (premium) — the prose must be brilliant
        model = router.select_model("story_writing")
        response = await router.invoke(model, messages, max_tokens=8192)
        raw = response["content"].strip()
        json_text = self._extract_json(raw)

        try:
            script_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed. Raw response (first 500 chars):\n{raw[:500]}")
            logger.error(f"Extracted JSON (first 500 chars):\n{json_text[:500]}")
            raise RuntimeError(f"Parable writer returned invalid JSON: {e}") from e

        # Build ComicProject
        project = ComicProject(
            title=script_data.get("title", brief.get("title_suggestion", "Untitled")),
            theme_id=self._slugify(script_data.get("title", "untitled")),
            synopsis=script_data.get("synopsis", ""),
            art_style=art_style,
        )

        # Store the full parable prose text
        project.parable_text = script_data.get("parable_text", "")

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

        # Cost for both steps
        cost = self._estimate_cost(response.get("usage", {}), model)
        project.total_cost += cost
        project.log(f"Script generated (2-step): {len(project.panels)} panels, cost ~${cost:.4f}")

        logger.info(f"Parable ready: '{project.title}' — {len(project.panels)} panels")
        if project.parable_text:
            word_count = len(project.parable_text.split())
            logger.info(f"Parable text: {word_count} words")

        return project

    def _extract_json(self, text: str) -> str:
        """Extract JSON from model response, handling markdown fences, preamble, and control chars."""
        # Strip markdown code fences
        if "```json" in text:
            text = text.split("```json", 1)[1]
            text = text.rsplit("```", 1)[0]
        elif "```" in text:
            text = text.split("```", 1)[1]
            text = text.rsplit("```", 1)[0]
        else:
            # Find first { and last } — handles preamble text before JSON
            first_brace = text.find("{")
            last_brace = text.rfind("}")
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                text = text[first_brace:last_brace + 1]

        text = text.strip()

        # Fix control characters inside JSON string values (newlines, tabs)
        # Replace literal newlines inside strings with \n escape
        import re
        # Replace actual newlines that are inside JSON string values
        # Strategy: replace all bare newlines with \\n, then fix the structural ones back
        lines = text.split("\n")
        text = "\n".join(lines)  # Normalize line endings

        # Try parsing with strict=False first (allows control chars in strings)
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # Fallback: sanitize control characters inside string values
        # Replace problematic chars but preserve JSON structure
        cleaned = ""
        in_string = False
        escape_next = False
        for ch in text:
            if escape_next:
                cleaned += ch
                escape_next = False
                continue
            if ch == "\\":
                escape_next = True
                cleaned += ch
                continue
            if ch == '"':
                in_string = not in_string
                cleaned += ch
                continue
            if in_string and ch in ("\n", "\r", "\t"):
                # Replace control chars inside strings with safe equivalents
                if ch == "\n":
                    cleaned += "\\n"
                elif ch == "\r":
                    cleaned += ""
                elif ch == "\t":
                    cleaned += "\\t"
            else:
                cleaned += ch

        return cleaned

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

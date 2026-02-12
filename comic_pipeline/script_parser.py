"""
Comic Pipeline — Script Parser.

Two-step parable generation calibrated to Bible parable structure:

Step 1: David Flip supplies a BRIEF — the facts, lesson, and metaphor he wants.
Step 2: Master Parable Writer crafts the story using Bible parable structure,
        then formats it as comic panels.

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

Every David parable explores one of these truths:
- People trade freedom for comfort because freedom is harder
- The gift that creates dependence is the most dangerous gift
- Those who do no work end up living off those who do — and wasting what they take
- When everyone depends on a system, they stop depending on each other, and community dies
- Freedom costs something most people won't pay — but the cost of dependence is higher

== WHAT YOU SUPPLY ==

1. A HUMAN WEAKNESS (not an enemy's evil):
   Complete this: "People accept [this control] because [this human weakness]."
   The weakness must be something the READER does too. Not stupidity. Something reasonable —
   comfort, love for family, fear, practicality. The reader should think "I would do the same."

2. THE METAPHOR: A concrete village setting. Marketplace, dock, farm, bakery, road, workshop.
   NOT abstract. NOT sci-fi. The village IS peer-to-peer community. The kingdom IS centralised
   control. Use these naturally.

3. THE CHARACTERS (2-3 max):
   - The protagonist: name, trade, a real need (hungry kids, broken boat, failing crop).
     They make a REASONABLE choice that leads to dependence.
   - The system: represented by a person — a merchant, representative, official. Charming,
     helpful, generous at first. NOT evil-looking. Gets fatter and better-dressed over time
     while the workers get thinner.
   - The mirror: someone who chose differently. Has LESS but is FREE. Looks foolish. Is wise.
     Still helps neighbours. Still has time. Still owns their own work.

4. THE ESCALATION — the specific stages of control:
   - Year 1: The gift. Genuine improvement. No cost. Life is better.
   - Year 2: Small cost introduced. Reasonable. Still net positive.
   - Year 3: Cost rises. Extra demands on time/labour. About even now.
   - Year 4: Cost exceeds benefit. Punishment for dissent. Someone loses everything.
   - Year 5: Far worse than before. Working harder, keeping less. Can't go back.
   THE MATHS MUST WORK. Show specific numbers that the reader can follow.

5. THE COMMUNITY COST: Show how the village used to support each other (sharing, fixing,
   helping) and how the system destroyed that. People now have no time or surplus to help
   neighbours. The system replaced community with bureaucracy.

6. THE WASTE: The fat cats don't even use what they take efficiently. Fish rot on docks.
   Feasts for inspectors. The harbour they promised to fix is still broken.

7. THE GUT-PUNCH: The moment the protagonist sees the truth — not about the system, but
   about THEMSELVES. "I chose this. I did this to myself. And I can't undo it."

8. THE ENDING: An unanswered question that haunts. "Do you still know how to [the skill
   they lost]?" The protagonist can't go back — not because the system won't let them,
   but because they've lost the ability to be self-sufficient.

Return ONLY valid JSON:
{{
  "lesson": "...",
  "human_weakness": "People accept [X] because [Y]",
  "metaphor": "...",
  "setting": "...",
  "characters": [
    {{"name": "...", "role": "protagonist/mirror/authority", "description": "...", "want": "..."}}
  ],
  "escalation": [
    {{"year": 1, "gift": "...", "cost": "none", "keeps": "...", "hours": "..."}},
    {{"year": 2, "gift": "...", "cost": "...", "keeps": "...", "hours": "..."}},
    {{"year": 3, "gift": "...", "cost": "...", "keeps": "...", "hours": "..."}},
    {{"year": 4, "gift": "...", "cost": "...", "keeps": "...", "hours": "..."}},
    {{"year": 5, "gift": "...", "cost": "...", "keeps": "...", "hours": "..."}}
  ],
  "community_before": "How villagers used to help each other",
  "community_after": "How the system destroyed mutual support",
  "waste": "How the fat cats waste what they take",
  "gut_punch": "...",
  "ending_line": "...",
  "title_suggestion": "..."
}}
"""


# ============================================================
# Step 2: Master Parable Writer
# ============================================================

PARABLE_WRITER_PROMPT = """You are a master storyteller. Your craft is the parable — the oldest
and most powerful form of teaching story. You have studied every parable Jesus told and you
understand exactly why they work.

== WHAT DAVID'S PARABLES ARE ABOUT ==

These are parables about HUMAN NATURE, not about technology or politics. They explore why
people CHOOSE dependence, why they accept control, and what it costs them — not just in
freedom, but in community. The reader should feel convicted about their OWN choices.

The core pattern: a few people control the many through systems that LOOK generous but
create dependence. The gift is real. The improvement is real. That's what makes the trap
work. The cost comes slowly — more tax, more rules, more hours, more control — until the
person is worse off than before AND can't go back. Meanwhile, those in control grow fat
on labour they never performed, and waste what they take.

The deeper cost: the system doesn't just steal from individuals. It destroys COMMUNITY.
People who used to help each other now have no time or surplus to share. The village that
once took care of its own now depends entirely on the kingdom. And the kingdom doesn't care.

== THE FORM ==

Calibrated from analysis of all 60+ parables of Jesus:

WORD COUNT: 350-500 words. This is slightly longer than a Bible parable because we need
to show the full escalation arc (5 seasons of tightening control).

STRUCTURE:
  GROUND (10-15%): The village before. Life is small but free. People help each other.
    Establish what they HAVE — not wealth, but self-sufficiency and community.
  GIFT (10%): The system arrives with something genuinely useful. Free. Better than what
    they had. Life improves. No one questions a gift.
  ESCALATION (40-50%): The cost reveals itself season by season. Tax rises. Hours increase.
    Rules multiply. Someone is punished for dissent. The fat cats get fatter while workers
    get thinner. The waste becomes visible. THE MATHS MUST WORK — show specific numbers
    so the reader can track exactly how the trap tightens.
  THE MIRROR (5-10%): Show the character who refused the gift. They have less. They look
    foolish. But they're free, they still help their neighbours, they still own their work.
  TURN + LANDING (10-15%): The protagonist SEES the truth — about themselves, not the system.
    They chose this. They can't go back. End with an unanswered question.

DIALOGUE: Sparse. ZERO in the setup. A few lines from the system's representative (always
smooth, always "reasonable"). The real dialogue is at the end between the protagonist and
the mirror character. The final line should haunt.

MORAL: DO NOT STATE IT. NEVER. The reader's discomfort IS the lesson.

VOICE: Plain, direct, concrete. Short sentences. Anglo-Saxon words over Latin ones.
"He walked" not "He proceeded." Poetic only in rhythm, never in vocabulary.

== BENCHMARK PARABLE ==

This is the quality standard. Every parable you write must match this level:

"There was a village by the sea where every family fished with nets of hemp they'd woven
themselves. On a good day, a man caught ten fish. He kept all ten. He worked till noon and
spent his afternoons mending net, playing with his children, and owing nothing to anyone.

When a man had a bad day, his neighbour shared. When a boat broke, the village fixed it.
They needed no one but each other.

A merchant arrived from the kingdom with carts of nets — lighter, stronger, finer than hemp.
He gave one to every fisherman and asked for nothing.

'Why free?' asked Marcos.

'The kingdom invests in its people,' said the merchant.

The new nets were better. Where hemp caught ten, these caught fifteen. Marcos was home
before noon with five extra fish. It was the best season the village had ever known.

In the second year, a representative arrived from the kingdom. A heavier man, in fine clothes,
who had clearly never hauled a net. A small tax — two fish in fifteen. 'To maintain the
harbour.' And to keep using the kingdom's nets, each fisherman must work one extra hour
per day. New regulations. For the health of the sea.

Fair enough. Marcos still kept thirteen. Still more than hemp.

In the third year, the tax rose to five. The extra hours rose to two. Inspectors arrived —
also well-fed, also in fine clothes. They ate lunch on the dock. Fish lunch. Marcos kept ten
and worked till mid-afternoon. The same as hemp — but now he worked two extra hours for them.

In the fourth year, the tax rose to seven. Three extra hours. A fisherman named Cal spoke
against the inspectors. His net was taken. He could not fish at all — he had burned his hemp
net years ago.

Marcos kept eight fish and worked until dark. He had nothing to spare. When his neighbour's
boat broke, he could not help. He had no time. He had no fish. The kingdom had a programme
for that, the representative said. Apply with the clerk.

The representative threw a feast for the inspectors that season. Marcos counted fourteen fish
on their table. He recognised them. Some were his.

In the fifth year, the tax was nine in fifteen. Marcos worked from before dawn until after
dark and carried six fish home.

He passed old Wen sitting on the dock in the last light. Wen still fished with hemp. Still
caught his ten. Still stopped at noon. Still kept every one. That afternoon, Wen had helped
a neighbour mend a boat. He did that sort of thing.

Marcos set down his six fish.

'I used to think you were a fool,' he said.

Wen mended his net — a thing he had made with his own hands, that answered to no one.

'We used to work hard,' Wen said quietly. 'But the rewards were ours. We supported the
village. We worked together.' He looked down the dock at the fishermen trudging home in the
dark, alone, with nothing to share. 'Now you work for men who have never touched the sea.
And you cannot even help each other.'

'How do I go back?' Marcos asked.

Wen looked at him a long time.

'Do you still know how to weave hemp?'"

Study this parable. It works because:
1. The maths is airtight (10 fish with hemp vs 6 fish with kingdom nets + dawn-to-dark hours)
2. The escalation is specific and trackable season by season
3. The fat cats are visible (fine clothes, feasts, never hauled a net)
4. The waste is shown (fish rot, harbour still broken)
5. The community death is shown (can't help neighbour, "apply with the clerk")
6. The mirror character (Wen) is free, helps others, owns his work
7. The punishment (Cal) shows the threat of dissent
8. The ending is an unanswered question about lost self-sufficiency
9. NO moral is stated. The reader feels it.

== ART STYLE FOR IMAGE PROMPTS ==

{art_style}

Every image prompt must include the full art style. Be extremely specific about visual
details: character poses, expressions, lighting, background elements, colour palette.
The image generator has NO memory — each prompt must be completely self-contained.

For ANY recurring character, describe them with EXACT same physical traits in every panel:
hair colour/style, clothing, age, distinguishing features.

== JSON OUTPUT FORMAT ==

CRITICAL: Return ONLY the JSON object. No preamble, no commentary. Start with {{ end with }}.

{{
  "title": "The Parable Title",
  "synopsis": "One-sentence summary",
  "parable_text": "The full parable as prose (350-500 words).",
  "panels": [
    {{
      "panel_number": 1,
      "image_prompt": "Detailed image description with art style, character descriptions, scene, lighting, mood. Self-contained.",
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

1. 7-10 panels — enough to show the full escalation arc.
2. First 2-3 panels: NO dialogue. Visual storytelling of the village before + the gift.
3. Middle panels: The escalation. Show the representative getting fatter, the workers
   getting thinner, the waste, the rules. Minimal dialogue — the system speaks in
   reasonable tones.
4. The punishment panel: Someone loses everything for speaking up. Visual weight.
5. The mirror panel: The "fool" who refused, still free, still helping neighbours.
6. Final panel: The protagonist and the mirror. The question. Maximum weight.
7. Narration boxes are David's voice. Sparse. Poetic. NEVER explanatory.
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
            panel_count: Suggested panel count (6-8)
            personality_prompt: Optional additional personality overlay

        Returns:
            ComicProject with populated panels (no images yet)
        """
        router = self._get_router()

        if not art_style:
            art_style = ComicProject(title="", theme_id="").art_style

        # === Step 1: David's Brief ===
        logger.info("Step 1: David Flip creating parable brief...")
        brief = await self._generate_brief(router, theme, personality_prompt)
        logger.info(f"Brief ready: {brief.get('title_suggestion', 'untitled')}")

        # === Step 2: Master Parable Writer ===
        logger.info("Step 2: Master Parable Writer crafting story...")
        project = await self._write_parable(
            router, brief, art_style, panel_count
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
        self, router, brief: dict, art_style: str, panel_count: int
    ) -> ComicProject:
        """Step 2: Master Parable Writer crafts the story from David's brief."""
        system = PARABLE_WRITER_PROMPT.format(art_style=art_style)

        # Format David's brief for the writer
        brief_text = (
            f"== DAVID FLIP'S BRIEF ==\n\n"
            f"TITLE SUGGESTION: {brief.get('title_suggestion', 'Untitled')}\n"
            f"LESSON: {brief.get('lesson', '')}\n"
            f"METAPHOR: {brief.get('metaphor', '')}\n"
            f"SETTING: {brief.get('setting', '')}\n"
            f"FACTS TO EMBED: {brief.get('facts', '')}\n"
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

        brief_text += (
            f"\nWrite a {panel_count}-panel comic script. "
            f"The parable text should be 250-400 words. "
            f"Craft it like a Bible parable — Ground, Escalate, Turn, Land. "
            f"Return ONLY the JSON object, starting with {{ — no preamble."
        )

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": brief_text},
        ]

        model = router.select_model("content_generation")
        response = await router.invoke(model, messages, max_tokens=4096)
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

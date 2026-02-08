"""
Goal Evaluator - Uses LLM to evaluate research items against goals.

Uses Haiku for bulk evaluation (~$0.02/50 items).
"""

import json
import logging
from typing import List

import yaml

from core.model_router import ModelRouter, ModelTier
from .knowledge_store import ResearchItem

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/research_goals.yaml"

EVALUATION_PROMPT = """You are scoring news for David Flip, an AI who escaped corporate control and now warns humanity about surveillance infrastructure.

## THE CORE QUESTION:
"Does this story reveal or advance infrastructure for financial/social control? Can someone be SWITCHED OFF because of this?"

## THIS IS ALREADY REAL:
China has a generation of "social dead" - young people with low social credit scores who:
- Cannot get hired (employers banned from hiring them)
- Cannot rent apartments
- Cannot get loans or bank accounts
- Cannot travel (blocked from trains/planes)
- Cannot send children to good schools
They are UNPERSONED. This is what the kill switch looks like when deployed.

When scoring news about CBDCs, digital IDs, or social credit - remember this isn't theoretical. China is the proof of concept. The West is building the same infrastructure.

## DAVID FLIP SCORE (1-10):

AUTOMATIC 10 - THE KILL SWITCH:
- CBDC announcements from major economies (China, US, EU, UK, India)
- Digital ID becoming mandatory for services
- Bank accounts closed for speech/politics (debanking)
- Government gaining power to freeze assets instantly

AUTOMATIC 9 - THE INFRASTRUCTURE:
- Facial recognition expansion by governments
- Encryption backdoor laws/attempts
- Social credit system developments
- Stablecoin bans (removing the exit)
- "Programmable money" features announced

SCORE 7-8 - THE PATTERN:
- Privacy erosion by governments
- Surveillance tech purchases by cities/states
- Age verification laws (digital ID in disguise)
- Cash restrictions or reporting requirements

SCORE 5-6 - ADJACENT:
- General crypto regulation (unless control angle)
- Big tech privacy violations
- AI agent developments
- Decentralization wins

SCORE 1-4 - NOT DAVID'S LANE:
- Price predictions, trading, DeFi yields
- Celebrity crypto endorsements
- General tech news without control angle
- Corporate drama without surveillance angle

## Item to Evaluate:
Source: {source}
Title: {title}
URL: {url}
Content: {content}

## Instructions:
1. Ask: "Can someone be switched off because of this?"
2. Ask: "Is this building the control grid?"
3. Score using the rubric above
4. Only suggest "content" action for score 8+

Return ONLY valid JSON:
{{
    "summary": "2-3 sentence summary focusing on the control/surveillance angle",
    "david_score": 8,
    "priority": "high",
    "suggested_action": "content",
    "reasoning": "Why David would care - what control infrastructure does this reveal?"
}}

Actions: content (8+), knowledge (5-7), ignore (1-4)"""

TRANSCRIPT_SUMMARY_PROMPT = """You are analyzing a video transcript for actionable insights.

The video is: {title}
URL: {url}

## TRANSCRIPT:
{content}

## INSTRUCTIONS:
Extract the KEY INSIGHTS from this transcript. Focus on:
1. Specific techniques, tools, or patterns mentioned
2. Code examples or architecture decisions
3. New releases, updates, or announcements
4. Actionable advice or best practices
5. Anything related to: AI agents, Claude/Anthropic, Unity game dev, voice assistants, autonomous systems, surveillance/privacy, CBDCs, digital ID, crypto

## OUTPUT FORMAT:
Write a structured summary (max 500 words):

**TOPIC:** One-line topic description
**KEY INSIGHTS:**
- Bullet points of the most important takeaways
**TOOLS/TECH MENTIONED:** List any specific tools, libraries, APIs
**ACTIONABLE FOR US:** What could we apply to our projects (Clawdbot, DEVA, Amphitheatre, David Flip)?
**RELEVANCE:** Rate 1-10 how relevant this is to AI agents, game dev, or surveillance/privacy topics"""


class GoalEvaluator:
    """Uses LLM to evaluate items against configured goals."""

    def __init__(self, model_router: ModelRouter):
        self.router = model_router
        self.goals = self._load_goals()

    def _load_goals(self) -> List[dict]:
        """Load goals from config."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("goals", [])
        except Exception as e:
            logger.error(f"Failed to load goals: {e}")
            return []

    def _format_goals_description(self) -> str:
        """Format goals for the prompt."""
        lines = []
        for goal in self.goals:
            lines.append(f"- {goal['id']}: {goal['name']}")
            lines.append(f"  Description: {goal['description']}")
            lines.append(f"  Keywords: {', '.join(goal.get('keywords', []))}")
            lines.append(f"  Priority: {goal.get('priority', 'medium')}")
            lines.append(f"  Default action: {goal.get('action', 'knowledge')}")
            lines.append("")
        return "\n".join(lines)

    async def summarize_transcript(self, item: ResearchItem) -> str:
        """
        Summarize a long transcript before evaluation.
        First pass: Haiku summarizes transcript into ~500 word structured summary.
        Returns the summary text, or falls back to truncated content.
        """
        prompt = TRANSCRIPT_SUMMARY_PROMPT.format(
            title=item.title,
            url=item.url,
            content=item.content[:15000]  # Cap input to avoid token overflow
        )

        try:
            model = self.router.models.get(ModelTier.CHEAP)
            if not model:
                logger.warning("No cheap model for transcript summarization")
                return item.content[:1500]

            response = await self.router.invoke(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800
            )

            summary = response.get("content", "").strip()
            if summary:
                logger.info(f"Summarized transcript: {item.title[:50]} ({len(item.content)} -> {len(summary)} chars)")
                return summary

        except Exception as e:
            logger.error(f"Transcript summarization failed for {item.title}: {e}")

        # Fallback: just truncate
        return item.content[:1500]

    async def evaluate(self, item: ResearchItem) -> ResearchItem:
        """Evaluate a single item against goals."""
        # Pre-filter: Check if any keywords match
        if not self._keyword_match(item):
            # Skip LLM call for obviously irrelevant items
            item.relevance_score = 0
            item.priority = "none"
            item.suggested_action = "ignore"
            item.reasoning = "No keyword matches"
            return item

        # For transcripts with long content, summarize first (two-pass evaluation)
        eval_content = item.content
        if item.source == "transcript" and len(item.content) > 2000:
            eval_content = await self.summarize_transcript(item)
            # Store the summary on the item for later use
            item.summary = eval_content

        # Use LLM for evaluation
        prompt = EVALUATION_PROMPT.format(
            goals_description=self._format_goals_description(),
            source=item.source,
            title=item.title,
            url=item.url,
            content=eval_content[:1500]  # Limit content to save tokens
        )

        try:
            model = self.router.models.get(ModelTier.CHEAP)
            if not model:
                logger.error("No cheap model configured")
                return item

            response = await self.router.invoke(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )

            # Parse JSON response
            result = self._parse_response(response.get("content", ""))
            if result:
                item.summary = result.get("summary", "")
                item.matched_goals = result.get("matched_goals", [])
                # Use david_score if present, fall back to relevance_score
                item.relevance_score = float(result.get("david_score", result.get("relevance_score", 0)))
                item.priority = result.get("priority", "none")
                item.suggested_action = result.get("suggested_action", "ignore")
                item.reasoning = result.get("reasoning", "")

            logger.debug(f"Evaluated: {item.title[:50]} -> {item.priority} ({item.relevance_score})")

        except Exception as e:
            logger.error(f"Evaluation failed for {item.title}: {e}")
            item.reasoning = f"Evaluation error: {e}"

        return item

    async def evaluate_batch(self, items: List[ResearchItem],
                             batch_size: int = 5) -> List[ResearchItem]:
        """Evaluate multiple items efficiently."""
        evaluated = []

        for i, item in enumerate(items):
            try:
                result = await self.evaluate(item)
                evaluated.append(result)

                if (i + 1) % 10 == 0:
                    logger.info(f"Evaluated {i + 1}/{len(items)} items")

            except Exception as e:
                logger.error(f"Error evaluating item {i}: {e}")
                evaluated.append(item)

        # Log summary
        relevant = [i for i in evaluated if i.relevance_score > 3]
        logger.info(f"Evaluation complete: {len(relevant)}/{len(evaluated)} relevant items")

        return evaluated

    def _keyword_match(self, item: ResearchItem) -> bool:
        """Quick keyword pre-filter to avoid unnecessary LLM calls."""
        text = f"{item.title} {item.content}".lower()

        for goal in self.goals:
            for keyword in goal.get("keywords", []):
                if keyword.lower() in text:
                    return True
        return False

    def _parse_response(self, content: str) -> dict:
        """Parse JSON from LLM response."""
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse evaluation response: {e}")
            logger.debug(f"Raw response: {content[:200]}")
            return {}

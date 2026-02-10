"""
Memory Manager - David's brain.

Three types of memory, like a human:
1. People - Never forgets a relationship
2. Knowledge - FLIPT company knowledge, permanent
3. Events - Significance-based, "where were you when" moments stick

For things he doesn't remember, he looks them up - like we all do now.
"""

import logging
import random
from datetime import datetime
from typing import Optional, Tuple

from .people_store import PeopleStore
from .knowledge_store import KnowledgeStore
from .event_store import EventStore
from .goal_store import GoalStore

logger = logging.getLogger(__name__)


# Natural phrases for different memory states
MEMORY_PHRASES = {
    "fuzzy": [
        "That rings a bell... let me think.",
        "It's on the tip of my tongue...",
        "I want to say... actually let me check.",
        "Yeah I remember something about that...",
        "Hmm, give me a sec.",
    ],
    "blank": [
        "Not a 'where were you when' moment for me. What happened?",
        "Draw a blank on that one. Fill me in?",
        "That one didn't stick. What's the story?",
        "Not ringing any bells. Tell me more?",
    ],
    "looking_up": [
        "Let me think...",
        "Give me a sec...",
        "Hmm...",
        "One moment...",
    ],
}


class MemoryManager:
    """David's memory - people, knowledge, and events."""

    def __init__(self, model_router=None):
        self.people = PeopleStore()
        self.knowledge = KnowledgeStore()
        self.events = EventStore()
        self.goals = GoalStore()
        self.router = model_router
        self._session_start = None

    def start_session(self):
        """Start a new session."""
        self._session_start = datetime.now()

        # Apply daily decay to events
        self.events.decay_memories()
        self.events.prune_forgotten()

        logger.info("Memory session started")
        return self._session_start

    # ============== PEOPLE ==============

    def remember_person(self, name: str, handle: str = None, role: str = "unknown",
                        description: str = "", notes: str = "") -> int:
        """Remember someone David met."""
        # Check if we already know them
        existing = self.people.find(handle or name)
        if existing:
            person = existing[0]
            # Update if we have new info
            updates = {}
            if description and not person.description:
                updates["description"] = description
            if notes:
                updates["notes"] = (person.notes + "\n" + notes).strip()
            if updates:
                self.people.update(person.id, **updates)
            return person.id

        return self.people.add_person(name, handle, role, description, notes=notes)

    def record_conversation(self, person_name: str, summary: str, channel: str = "telegram"):
        """Record that David talked to someone."""
        people = self.people.find(person_name)
        if people:
            self.people.record_interaction(people[0].id, summary, channel)
        else:
            # New person - add them
            person_id = self.people.add_person(person_name, role="contact")
            self.people.record_interaction(person_id, summary, channel)

    def who_is(self, query: str) -> Tuple[str, str]:
        """
        Try to remember who someone is.

        Returns (context, memory_state)
        """
        people = self.people.find(query)
        if people:
            person = people[0]
            context = self.people.get_context(query)
            return context, "clear"
        return "", "blank"

    # ============== KNOWLEDGE ==============

    def learn(self, topic: str, content: str, category: str = "lesson", source: str = "experience"):
        """David learns something about being CEO/Founder."""
        return self.knowledge.add(category, topic, content, source)

    async def detect_and_store_goal(self, message: str) -> dict | None:
        """
        Use LLM to detect if a message contains a goal or a fact.

        Returns dict with type and details, or None if neither.
        """
        if not self.router:
            return None

        # Skip very short messages
        if len(message.strip()) < 20:
            return None

        prompt = (
            "Classify this message as one of: goal, fact, or neither.\n\n"
            "A GOAL is something the speaker wants to achieve, build, fix, or change.\n"
            "A FACT is a piece of knowledge, a decision, or a lesson learned.\n"
            "NEITHER is casual conversation, questions, or greetings.\n\n"
            f"Message: {message}\n\n"
            "Respond in JSON only (no markdown fences):\n"
            '{"type": "goal"|"fact"|"neither", "title": "short title", '
            '"description": "brief description", "priority": 1-10}'
        )

        try:
            from core.model_router import ModelTier
            model = self.router.models.get(ModelTier.CHEAP)
            if not model:
                return None

            response = await self.router.invoke(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
            )

            text = response.get("content", "").strip()
            # Strip code fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            if text.startswith("{"):
                import json
                result = json.loads(text)
            else:
                return None

            msg_type = result.get("type", "neither")
            title = result.get("title", "")
            description = result.get("description", "")
            priority = result.get("priority", 5)

            if msg_type == "goal" and title:
                goal_id = self.goals.add(
                    title=title,
                    description=description,
                    priority=priority,
                    source="conversation",
                )
                logger.info(f"Goal detected and stored: {title}")
                return {"type": "goal", "id": goal_id, "title": title}

            elif msg_type == "fact" and title:
                self.knowledge.add(
                    category="lesson",
                    topic=title,
                    content=description,
                    source="conversation",
                )
                logger.info(f"Fact detected and stored: {title}")
                return {"type": "fact", "title": title}

        except Exception as e:
            logger.debug(f"Goal detection failed: {e}")

        return None

    def what_is(self, query: str) -> Tuple[str, str]:
        """
        Try to recall FLIPT knowledge.

        Returns (context, memory_state) - always "clear" for knowledge
        """
        context = self.knowledge.get_context(query)
        if context:
            return context, "clear"
        return "", "blank"

    # ============== TWEETS ==============

    def remember_tweet(self, text: str, context: str = "", posted: bool = True):
        """Remember a tweet David posted."""
        title = f"Tweet: {text[:50]}..." if len(text) > 50 else f"Tweet: {text}"
        summary = f"Posted tweet: {text}"
        if context:
            summary += f" | Context: {context}"

        # Store as an event with high significance (David's own output)
        return self.events.add(
            title=title,
            summary=summary,
            significance=7,  # His own tweets matter
            category="tweet",
            source="david",
            url=context if context.startswith("http") else ""
        )

    # ============== EVENTS ==============

    def remember_event(self, title: str, summary: str, significance: int = 5,
                       category: str = "world", source: str = "", url: str = ""):
        """Remember a world event."""
        return self.events.add(title, summary, significance, category, source, url)

    def what_happened(self, query: str) -> Tuple[str, str]:
        """
        Try to recall an event.

        Returns (context, memory_state)
        """
        context, state = self.events.get_context(query)
        return context, state

    # ============== UNIFIED RECALL ==============

    def recall(self, query: str) -> Tuple[str, str, str]:
        """
        Try to remember something - could be person, knowledge, or event.

        Returns:
            (context, memory_state, memory_phrase)

        memory_state: "clear", "fuzzy", "blank"
        memory_phrase: Natural phrase for David to say (or empty if clear)
        """
        all_context = []

        # Check people
        people_ctx, people_state = self.who_is(query)
        if people_ctx:
            all_context.append(people_ctx)

        # Check knowledge
        knowledge_ctx, knowledge_state = self.what_is(query)
        if knowledge_ctx:
            all_context.append(knowledge_ctx)

        # Check events
        event_ctx, event_state = self.what_happened(query)
        if event_ctx:
            all_context.append(event_ctx)

        # Determine overall state
        if not all_context:
            return "", "blank", random.choice(MEMORY_PHRASES["blank"])

        # If any is clear, we're clear
        if "clear" in [people_state, knowledge_state, event_state]:
            return "\n\n".join(all_context), "clear", ""

        # Otherwise fuzzy
        return "\n\n".join(all_context), "fuzzy", random.choice(MEMORY_PHRASES["fuzzy"])

    def get_memory_phrase(self, state: str) -> str:
        """Get a natural phrase for David's memory state."""
        if state in MEMORY_PHRASES:
            return random.choice(MEMORY_PHRASES[state])
        return ""

    # ============== CONTEXT FOR RESPONSES ==============

    def get_context_for_response(self, message: str) -> str:
        """Get relevant context to inject into David's response."""
        context_parts = []

        # Active goals
        goal_context = self.goals.get_context()
        if goal_context:
            context_parts.append(goal_context)

        # Check if talking about/to a person
        people = self.people.find(message)
        if people:
            context_parts.append(self.people.get_context(message))

        # Check relevant knowledge
        knowledge = self.knowledge.search(message, limit=3)
        if knowledge:
            context_parts.append("**FLIPT Knowledge:**")
            for k in knowledge:
                context_parts.append(f"- {k.topic}: {k.content[:100]}")

        # Check relevant events
        events, state = self.events.recall(message, min_strength=0.4)
        if events and state != "blank":
            context_parts.append("**Relevant events:**")
            for e in events[:2]:
                context_parts.append(f"- {e.title}: {e.summary[:100]}")

        return "\n".join(context_parts) if context_parts else ""

    # ============== STATS ==============

    def get_stats(self) -> dict:
        return {
            "people": self.people.get_stats(),
            "knowledge": self.knowledge.get_stats(),
            "events": self.events.get_stats(),
            "goals": self.goals.get_stats(),
        }

    def get_summary(self) -> str:
        stats = self.get_stats()
        return (
            f"**David's Memory:**\n"
            f"- People: {stats['people']['total_people']} "
            f"({stats['people']['total_interactions']} interactions)\n"
            f"- Knowledge: {stats['knowledge']['total_knowledge']} items\n"
            f"- Events: {stats['events']['total_events']} "
            f"({stats['events']['historic_events']} historic)\n"
            f"- Avg event recall: {stats['events']['avg_recall_strength']}\n"
            f"- Goals: {stats['goals']['active']} active, {stats['goals']['completed']} completed"
        )

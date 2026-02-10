"""
David's Memory System

Four stores, like a human brain:
- PeopleStore: Relationships (never fade)
- KnowledgeStore: FLIPT company knowledge (never fade)
- EventStore: World events (fade based on significance)
- GoalStore: Goals detected from conversations

MemoryManager orchestrates all four.
"""

from .memory_manager import MemoryManager
from .people_store import PeopleStore, Person
from .knowledge_store import KnowledgeStore, Knowledge
from .event_store import EventStore, Event
from .goal_store import GoalStore, Goal

__all__ = [
    "MemoryManager",
    "PeopleStore", "Person",
    "KnowledgeStore", "Knowledge",
    "EventStore", "Event",
    "GoalStore", "Goal",
]

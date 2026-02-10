"""
Claude Memory System — Persistent memory for Claude Code sessions.

Adapted from David Flip's EventStore decay system.
Memories have significance (1-10) and decay over time,
with git reconciliation via Gemini as a safety net.

Usage:
    python -m claude_memory brief       # Generate session brief
    python -m claude_memory add         # Add a memory
    python -m claude_memory decay       # Apply weekly decay
    python -m claude_memory reconcile   # Git vs memory check (Gemini)
    python -m claude_memory status      # Show memory stats
    python -m claude_memory seed        # Seed from Memory.md
"""

from claude_memory.memory_db import ClaudeMemoryDB

__all__ = ["ClaudeMemoryDB"]

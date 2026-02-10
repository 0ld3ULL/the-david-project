"""
Brief Generator — Produces a concise claude_brief.md for session startup.

Reads the memory database, applies decay if due, and generates a
200-300 line markdown file organized by category and significance.

This is what Claude Code reads at the start of every session instead
of wading through 1400+ lines of Memory.md.
"""

from datetime import datetime, timedelta
from pathlib import Path

from claude_memory.memory_db import ClaudeMemoryDB, Memory

BRIEF_PATH = Path("claude_brief.md")

# How many days between automatic decay applications
DECAY_INTERVAL_DAYS = 7


def generate_brief(db: ClaudeMemoryDB, output_path: Path = BRIEF_PATH) -> str:
    """
    Generate a session brief from the memory database.

    Steps:
    1. Check if decay is due (weekly) — apply if needed
    2. Prune forgotten items
    3. Export memories organized by category
    4. Write concise brief to file

    Returns:
        Path to the generated brief file
    """
    # --- Step 1: Auto-decay if due ---
    last_decay = db.get_last_meta("last_decay")
    if last_decay:
        last_dt = datetime.fromisoformat(last_decay)
        if datetime.now() - last_dt > timedelta(days=DECAY_INTERVAL_DAYS):
            db.decay()
            db.prune()
    else:
        # First run — apply initial decay
        db.decay()

    # --- Step 2: Gather memories ---
    stats = db.get_stats()

    # Get all non-blank memories (recall_strength >= 0.3)
    all_memories = db.export_all(min_strength=0.0)

    # Split by category
    categories = {}
    for mem in all_memories:
        if mem.category not in categories:
            categories[mem.category] = []
        categories[mem.category].append(mem)

    # --- Step 3: Build brief ---
    lines = []
    lines.append("# Claude Session Brief")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"*Memories: {stats['total']} total — "
                 f"{stats['clear']} clear, {stats['fuzzy']} fuzzy, "
                 f"{stats['fading']} fading*")
    lines.append(f"*Last decay: {stats['last_decay']}*")
    lines.append(f"*Last reconciliation: {stats['last_reconciliation']}*")
    lines.append("")

    # Category order: knowledge first, then current_state, decisions, sessions, recovered
    category_order = ["knowledge", "current_state", "decision", "recovered", "session"]
    category_labels = {
        "knowledge": "Permanent Knowledge (never fades)",
        "current_state": "Current State (manually updated)",
        "decision": "Decisions",
        "recovered": "Recovered from Git (reconciliation)",
        "session": "Session History",
    }

    for cat in category_order:
        memories = categories.get(cat, [])
        if not memories:
            continue

        label = category_labels.get(cat, cat.title())
        lines.append(f"## {label}")
        lines.append("")

        for mem in memories:
            # Skip blank memories in the brief (they're fading out)
            if mem.state == "blank" and cat not in ("knowledge", "current_state"):
                continue

            # Format based on state
            if mem.state == "clear":
                prefix = ""
            elif mem.state == "fuzzy":
                prefix = "[fuzzy] "
            else:
                prefix = "[fading] "

            sig_indicator = "*" * min(mem.significance, 5)  # Visual significance

            lines.append(f"### {prefix}{mem.title} {sig_indicator}")
            lines.append(mem.content)

            # Show tags if present
            if mem.tags:
                lines.append(f"*Tags: {', '.join(mem.tags)}*")

            lines.append("")

    # Handle any categories not in our order
    for cat, memories in categories.items():
        if cat in category_order:
            continue
        lines.append(f"## {cat.title()}")
        lines.append("")
        for mem in memories:
            if mem.state == "blank":
                continue
            lines.append(f"### {mem.title}")
            lines.append(mem.content)
            lines.append("")

    # --- Step 4: Footer with quick reference ---
    lines.append("---")
    lines.append("## Quick Reference")
    lines.append("")
    lines.append("*For full project history, see Memory.md*")
    lines.append("*For task list, see tasks/todo.md*")
    lines.append("*For lessons learned, see tasks/lessons.md*")
    lines.append("")
    lines.append("### Memory Commands")
    lines.append("```")
    lines.append("python -m claude_memory brief        # Regenerate this file")
    lines.append("python -m claude_memory status       # Memory stats")
    lines.append("python -m claude_memory add          # Add a memory interactively")
    lines.append("python -m claude_memory decay        # Apply decay manually")
    lines.append("python -m claude_memory reconcile    # Git vs memory check")
    lines.append("```")

    # --- Write ---
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")

    return str(output_path)

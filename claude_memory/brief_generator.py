"""
Brief Generator — Produces a concise claude_brief.md for session startup.

Reads the memory database, applies decay if due, and generates a
markdown file organized by category and significance.

This brief holds PERMANENT knowledge only — things that never change
or are always needed. Short-term memory comes from reading recent
session transcripts (48h full recall + 30-day session index).
"""

from datetime import datetime, timedelta
from pathlib import Path

from claude_memory.memory_db import ClaudeMemoryDB, DB_DIR

# Default brief goes to global location
BRIEF_PATH = DB_DIR / "brief.md"

# How many days between automatic decay applications
DECAY_INTERVAL_DAYS = 7


def generate_brief(db: ClaudeMemoryDB, output_path: Path = None, project_path: Path = None) -> str:
    """
    Generate a trimmed session brief from the memory database.

    Only includes PERMANENT knowledge and ACTIVE blockers.
    Short-term memory comes from session transcripts (48h recall + 30-day index).

    Args:
        db: Memory database instance
        output_path: Where to write the brief (default: ~/.claude-memory/brief.md)
        project_path: If provided, also writes claude_brief.md to this directory

    Returns:
        Path to the generated brief file
    """
    if output_path is None:
        output_path = BRIEF_PATH

    output_path.parent.mkdir(parents=True, exist_ok=True)

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

    # --- Step 2: Gather memories with aggressive filtering ---
    stats = db.get_stats()

    all_memories = db.export_all(min_strength=0.0)

    # ONLY include these categories — everything else is searchable on demand
    include_categories = {
        "knowledge": 9,       # Only foundational permanent knowledge (sig >= 9)
        "current_state": 8,   # Only active blockers (sig >= 8)
    }

    # Split by category and filter aggressively
    categories = {}
    for mem in all_memories:
        # Only include whitelisted categories
        if mem.category not in include_categories:
            continue

        # Apply significance threshold
        threshold = include_categories[mem.category]
        if mem.significance < threshold:
            continue

        # Skip blank/fading memories
        if mem.recall_strength < 0.3:
            continue

        if mem.category not in categories:
            categories[mem.category] = []
        categories[mem.category].append(mem)

    # --- Step 3: Build brief ---
    lines = []
    lines.append("# Claude Session Brief")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"*Memories: {stats['total']} total — "
                 f"showing only sig >= 9 knowledge + sig >= 8 blockers*")
    lines.append("*Short-term memory: loaded from session transcripts (48h) + session index (30 days)*")
    lines.append("")

    # Category order: knowledge first, then current_state
    category_order = ["knowledge", "current_state"]
    category_labels = {
        "knowledge": "Permanent Knowledge",
        "current_state": "Active Blockers & State",
    }

    for cat in category_order:
        memories = categories.get(cat, [])
        if not memories:
            continue

        label = category_labels.get(cat, cat.title())
        lines.append(f"## {label}")
        lines.append("")

        for mem in memories:
            # Format based on state
            if mem.state == "clear":
                prefix = ""
            elif mem.state == "fuzzy":
                prefix = "[fuzzy] "
            else:
                prefix = "[fading] "

            lines.append(f"### {prefix}{mem.title}")
            lines.append(mem.content)

            if mem.tags:
                lines.append(f"*Tags: {', '.join(mem.tags)}*")

            lines.append("")

    # --- Step 4: Footer ---
    lines.append("---")
    lines.append("## Memory Commands")
    lines.append("```")
    lines.append("python -m claude_memory brief          # Regenerate this file")
    lines.append("python -m claude_memory index          # Rebuild 30-day session index")
    lines.append("python -m claude_memory status         # Memory stats")
    lines.append('python -m claude_memory add <cat> <sig> "title" "content"')
    lines.append('python -m claude_memory search "query" # Search memories')
    lines.append("python -m claude_memory decay          # Apply decay manually")
    lines.append("```")

    # --- Write ---
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")

    # Also write to project directory if specified
    if project_path:
        project_brief = Path(project_path) / "claude_brief.md"
        project_brief.write_text(content, encoding="utf-8")

    return str(output_path)

"""
CLI entry point for Claude Memory System.

Usage:
    python -m claude_memory brief           # Generate session brief
    python -m claude_memory status          # Show memory stats
    python -m claude_memory add <cat> <sig> "title" "content"
    python -m claude_memory decay           # Apply weekly decay
    python -m claude_memory prune           # Remove forgotten items
    python -m claude_memory reconcile       # Git vs memory check (Gemini)
    python -m claude_memory seed            # Seed from foundational knowledge
    python -m claude_memory search "query"  # Search memories
    python -m claude_memory export          # Export all memories as text
"""

import sys
import os
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

from claude_memory.memory_db import ClaudeMemoryDB
from claude_memory.brief_generator import generate_brief


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]
    db = ClaudeMemoryDB()

    if command == "brief":
        path = generate_brief(db)
        stats = db.get_stats()
        print(f"Brief generated: {path}")
        print(f"  {stats['total']} memories ({stats['clear']} clear, "
              f"{stats['fuzzy']} fuzzy, {stats['fading']} fading)")

    elif command == "status":
        stats = db.get_stats()
        print("Claude Memory Status")
        print("=" * 40)
        print(f"Total memories:     {stats['total']}")
        print(f"  Clear (>0.7):     {stats['clear']}")
        print(f"  Fuzzy (0.4-0.7):  {stats['fuzzy']}")
        print(f"  Fading (<0.4):    {stats['fading']}")
        print(f"Avg recall:         {stats['avg_recall_strength']}")
        print(f"Last decay:         {stats['last_decay']}")
        print(f"Last reconciliation:{stats['last_reconciliation']}")
        print()
        print("By category:")
        for cat, count in stats.get("by_category", {}).items():
            print(f"  {cat}: {count}")

    elif command == "add":
        if len(sys.argv) < 6:
            print("Usage: python -m claude_memory add <category> <significance> \"title\" \"content\"")
            print("Categories: decision, current_state, knowledge, session")
            print("Significance: 1-10")
            return
        category = sys.argv[2]
        significance = int(sys.argv[3])
        title = sys.argv[4]
        content = sys.argv[5]
        tags = sys.argv[6].split(",") if len(sys.argv) > 6 else []

        mem_id = db.add(title, content, category, significance, tags, source="manual")
        print(f"Added memory #{mem_id}: [{category}] sig={significance} — {title}")

    elif command == "decay":
        stats = db.decay()
        pruned = db.prune()
        print(f"Decay applied. {pruned} memories pruned.")
        print(f"  Clear: {stats['clear']}, Fuzzy: {stats['fuzzy']}, Fading: {stats['fading']}")

    elif command == "prune":
        pruned = db.prune()
        print(f"Pruned {pruned} forgotten memories.")

    elif command == "reconcile":
        from claude_memory.reconcile import reconcile
        result = reconcile(db)
        print(f"\nReconciliation complete:")
        print(f"  Recovered: {len(result.get('recovered', []))}")
        print(f"  Gaps filled: {len(result.get('gaps', []))}")
        print(f"  Stale flagged: {len(result.get('stale', []))}")
        print(f"\nSummary: {result.get('summary', 'N/A')}")

        if result.get("stale"):
            print("\nStale memories (review manually):")
            for item in result["stale"]:
                print(f"  - {item['memory_title']}: {item['reason']}")

    elif command == "seed":
        from claude_memory.seed import seed_memories
        count = seed_memories(db)
        print(f"Seeded {count} memories.")

    elif command == "search":
        if len(sys.argv) < 3:
            print("Usage: python -m claude_memory search \"query\"")
            return
        query = " ".join(sys.argv[2:])
        results = db.recall(query, min_strength=0.0, limit=20)
        if not results:
            print(f"No memories found for: {query}")
            return
        print(f"Found {len(results)} memories for: {query}\n")
        for mem in results:
            print(f"[{mem.category}] {mem.title} (sig={mem.significance}, "
                  f"strength={mem.recall_strength:.2f}, state={mem.state})")
            print(f"  {mem.content[:150]}...")
            print()

    elif command == "export":
        text = db.export_for_reconciliation()
        print(text)

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()

"""
Load the distilled Focal ML course into Pixel's knowledge base.
Chunks the course by section and stores each with date-stamp metadata.
"""

import re
from pathlib import Path
from core.memory.knowledge_store import KnowledgeStore

COURSE_PATH = Path("data/pixel_focal_course.md")
KB_PATH = Path("data/pixel_knowledge.db")

def split_sections(text: str) -> list[dict]:
    """Split the course into sections by ## headers."""
    sections = []
    current_title = None
    current_lines = []

    for line in text.splitlines():
        if line.startswith("## ") and current_title:
            sections.append({
                "title": current_title,
                "content": "\n".join(current_lines).strip(),
            })
            current_title = line.lstrip("# ").strip()
            current_lines = [line]
        elif line.startswith("## "):
            current_title = line.lstrip("# ").strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    # Last section
    if current_title and current_lines:
        sections.append({
            "title": current_title,
            "content": "\n".join(current_lines).strip(),
        })

    return sections


def main():
    course_text = COURSE_PATH.read_text(encoding="utf-8")
    sections = split_sections(course_text)

    ks = KnowledgeStore(KB_PATH)

    # Date-stamp prefix for all entries
    date_note = "[Source: ~March 2025 YouTube tutorials. Verify against live site.]"

    loaded = 0
    for section in sections:
        title = section["title"]
        content = section["content"]

        # Skip metadata section (it's just the index)
        if title == "METADATA":
            continue

        # Skip tiny sections
        if len(content) < 100:
            continue

        topic = f"Focal ML Course: {title}"
        tagged_content = f"{date_note}\n\n{content}"

        # Store in knowledge base
        ks.add(
            topic=topic,
            content=tagged_content,
            category="focal_ml",
            source="youtube_tutorials_march_2025",
            tags=["focal-ml", "course", "tutorial", title.lower().replace(" ", "-")],
        )
        loaded += 1
        print(f"  Loaded: {topic} ({len(content):,} chars)")

    print(f"\nDone: {loaded} course sections loaded into {KB_PATH}")

    # Show total
    all_entries = ks.search("focal")
    print(f"Total Focal ML knowledge entries: {len(all_entries)}")


if __name__ == "__main__":
    main()

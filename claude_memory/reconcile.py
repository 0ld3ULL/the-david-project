"""
Git Reconciliation — Weekly safety net using Gemini's 1M context window.

Compares the full git repository against the memory database to:
1. Recover pruned memories that still exist in code
2. Flag gaps (code exists but was never documented in memory)
3. Mark stale memories (reference code that was deleted)

Uses Wall Mode's WallCollector adapted for Python files (not Unity)
and Gemini 2.5 Flash for the comparison.
"""

import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from claude_memory.memory_db import ClaudeMemoryDB

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# File extensions to scan (Python project, not Unity)
CODE_EXTENSIONS = {".py", ".yaml", ".yml", ".toml", ".md", ".html", ".js", ".css"}

# Directories to skip
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv",
    "data", ".claude", ".claude-worktrees", "dist", "build",
    "egg-info",
}

# Max chars per file (truncate large files)
MAX_FILE_CHARS = 5000


def collect_repo_context(root: Path = PROJECT_ROOT) -> str:
    """
    Collect the repository structure and key file contents.
    Adapted from WallCollector but for a Python project.
    """
    lines = []
    lines.append("=" * 80)
    lines.append(f"REPOSITORY: {root.name}")
    lines.append(f"Scanned: {datetime.now().isoformat()}")
    lines.append("=" * 80)
    lines.append("")

    # --- Git info ---
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-30"],
            cwd=str(root), capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            lines.append("## Recent Git Commits (last 30)")
            lines.append(result.stdout.strip())
            lines.append("")
    except Exception:
        pass

    # --- File tree ---
    lines.append("## File Tree")
    file_list = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip excluded directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        rel_dir = Path(dirpath).relative_to(root)

        for filename in sorted(filenames):
            file_path = Path(dirpath) / filename
            ext = file_path.suffix.lower()

            if ext not in CODE_EXTENSIONS:
                continue

            rel_path = str(rel_dir / filename).replace("\\", "/")
            size = file_path.stat().st_size
            file_list.append((rel_path, file_path, size))
            lines.append(f"  {rel_path} ({size:,} bytes)")

    lines.append(f"\nTotal: {len(file_list)} files")
    lines.append("")

    # --- File contents (prioritize .py files, then config, then templates) ---
    lines.append("=" * 80)
    lines.append("## File Contents")
    lines.append("=" * 80)

    total_chars = 0
    max_total = 700_000  # Leave room for memory export + prompt in 1M context

    for rel_path, file_path, size in file_list:
        if total_chars > max_total:
            lines.append(f"\n[TRUNCATED — reached {max_total:,} char budget]")
            break

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + "\n... [TRUNCATED]"

            lines.append("")
            lines.append("-" * 60)
            lines.append(f"FILE: {rel_path}")
            lines.append("-" * 60)
            lines.append(content)

            total_chars += len(content)
        except Exception as e:
            lines.append(f"\n[ERROR reading {rel_path}: {e}]")

    return "\n".join(lines)


def build_reconciliation_prompt(repo_context: str, memory_export: str) -> str:
    """Build the prompt for Gemini to do the reconciliation."""
    return f"""You are analyzing a software project's codebase against its developer's memory database.

The developer (Claude Code AI) has a memory system with significance-based decay. Memories fade over time unless they're important enough to persist. Your job is to find discrepancies.

INSTRUCTIONS:
1. Compare the REPOSITORY (code, files, structure, commit messages) against the MEMORY DATABASE
2. Identify these three types of issues:

TYPE A — RECOVERED: Things that exist in code but were PRUNED from memory (the code proves a decision was made, but the memory of that decision has faded). These should be re-added to memory.

TYPE B — GAPS: Things that exist in code but were NEVER in memory. New files, patterns, or decisions that should be documented.

TYPE C — STALE: Things in memory that reference code/files that no longer exist. These memories are outdated.

OUTPUT FORMAT (strict JSON):
{{
    "recovered": [
        {{
            "title": "short title",
            "content": "what this is and why it matters",
            "significance": 5,
            "tags": ["tag1", "tag2"],
            "evidence": "file or commit that proves this exists"
        }}
    ],
    "gaps": [
        {{
            "title": "short title",
            "content": "what this is and why it should be remembered",
            "significance": 5,
            "tags": ["tag1", "tag2"],
            "evidence": "file or pattern that shows this"
        }}
    ],
    "stale": [
        {{
            "memory_title": "title from memory database",
            "reason": "why this is stale"
        }}
    ],
    "summary": "1-2 sentence summary of the reconciliation"
}}

Only include items with significance >= 5. Don't flag trivial things.
Be concise in content — 1-2 sentences max per item.

=== REPOSITORY ===
{repo_context}

=== MEMORY DATABASE ===
{memory_export}

=== RECONCILIATION RESULT (JSON) ==="""


def reconcile(db: ClaudeMemoryDB, project_root: Path = PROJECT_ROOT) -> dict:
    """
    Run the full reconciliation: collect repo, export memory, send to Gemini.

    Returns:
        Dict with recovered, gaps, stale items and summary
    """
    # Import Gemini client (avoid circular imports)
    import sys
    sys.path.insert(0, str(project_root))
    from voice.gemini_client import GeminiClient

    logger.info("Starting git reconciliation...")

    # Step 1: Collect repo context
    logger.info("Collecting repository context...")
    repo_context = collect_repo_context(project_root)
    logger.info(f"Repo context: {len(repo_context):,} chars")

    # Step 2: Export memory
    logger.info("Exporting memory database...")
    memory_export = db.export_for_reconciliation()
    logger.info(f"Memory export: {len(memory_export):,} chars")

    # Step 3: Build prompt and send to Gemini
    prompt = build_reconciliation_prompt(repo_context, memory_export)
    logger.info(f"Total prompt: {len(prompt):,} chars (~{len(prompt)//4:,} tokens)")

    gemini = GeminiClient()

    # Use a custom prompt instead of the DEVA system prompt
    response = gemini.analyze(
        context="",  # Context is embedded in the prompt
        question=prompt,
        max_tokens=4000,
        temperature=0.2,
    )

    logger.info(f"Gemini response: {response.output_tokens} tokens")

    # Step 4: Parse response
    try:
        # Extract JSON from response (Gemini might wrap it in markdown)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]  # Remove first line
            text = text.rsplit("```", 1)[0]  # Remove last ```
        result = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Gemini response as JSON: {e}")
        logger.error(f"Raw response: {response.text[:500]}")
        result = {
            "recovered": [], "gaps": [], "stale": [],
            "summary": f"Parse error: {e}",
            "raw_response": response.text,
        }

    # Step 5: Apply results to memory DB
    recovered_count = 0
    gap_count = 0

    for item in result.get("recovered", []):
        db.add(
            title=item["title"],
            content=item["content"],
            category="recovered",
            significance=item.get("significance", 5),
            tags=item.get("tags", []),
            source="git_reconciliation",
        )
        recovered_count += 1
        logger.info(f"Recovered: {item['title']}")

    for item in result.get("gaps", []):
        db.add(
            title=item["title"],
            content=item["content"],
            category="decision",
            significance=item.get("significance", 5),
            tags=item.get("tags", []),
            source="git_reconciliation",
        )
        gap_count += 1
        logger.info(f"Gap filled: {item['title']}")

    # Mark reconciliation timestamp
    db.set_meta("last_reconciliation", datetime.now().isoformat())

    summary = result.get("summary", "")
    stale_count = len(result.get("stale", []))

    logger.info(
        f"Reconciliation complete: {recovered_count} recovered, "
        f"{gap_count} gaps filled, {stale_count} stale flagged"
    )

    return result

"""
Comic Pipeline — Test Suite.

Tests each stage independently, then end-to-end.

Usage:
    python test_comic_pipeline.py                    # Run all tests
    python test_comic_pipeline.py test_models         # Run specific test
    python test_comic_pipeline.py test_end_to_end     # Full pipeline test (costs ~$0.41)
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))


# ============================================================
# Test 1: Models
# ============================================================

def test_models():
    """Test dataclass creation and serialization."""
    from comic_pipeline.models import (
        Panel, ComicPage, ComicProject, PanelType, CameraHint,
    )

    # Create a panel
    panel = Panel(
        panel_number=1,
        image_prompt="A weathered fisherman mending nets on a wooden dock...",
        dialogue=[
            {"speaker": "Fisherman", "text": "This net has served me well.", "style": "normal"},
        ],
        narration="There was a village by the sea.",
        camera=CameraHint.WIDE_SHOT,
        panel_type=PanelType.WIDE,
        mood="contemplative",
    )

    assert panel.panel_number == 1
    assert len(panel.dialogue) == 1
    assert panel.camera == CameraHint.WIDE_SHOT
    assert panel.panel_type == PanelType.WIDE

    # Create a project
    project = ComicProject(
        title="The Fisherman's Free Net",
        theme_id="the_free_net",
        synopsis="A fisherman discovers his free net reports his catch.",
        panels=[panel],
    )

    assert project.panel_count == 1
    assert project.title == "The Fisherman's Free Net"

    # Serialize
    data = project.to_dict()
    assert data["panel_count"] == 1
    assert data["panels"][0]["narration"] == "There was a village by the sea."

    project.log("Test log entry")
    assert len(project.generation_log) == 1

    print("  PASS: Models create, serialize, and log correctly")


# ============================================================
# Test 2: Script Parser (requires API key)
# ============================================================

async def test_script_parser():
    """Test script generation (requires ANTHROPIC_API_KEY)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  SKIP: ANTHROPIC_API_KEY not set")
        return

    from comic_pipeline.script_parser import ScriptParser

    parser = ScriptParser()
    project = await parser.generate_script(
        theme=(
            "The Fisherman's Free Net — A fisherman in a coastal village is given "
            "a free net by a stranger from the kingdom. Best net he's ever used. "
            "Then he notices it counts every fish and reports his catch to someone "
            "he's never met."
        ),
        panel_count=6,
    )

    assert project.title, "Project should have a title"
    assert len(project.panels) >= 4, f"Expected 4+ panels, got {len(project.panels)}"
    assert project.panels[0].image_prompt, "Panel should have image prompt"

    print(f"  PASS: Script generated — '{project.title}', {len(project.panels)} panels")
    print(f"        Synopsis: {project.synopsis[:100]}")
    for p in project.panels:
        dialogue_preview = p.dialogue[0]["text"][:40] if p.dialogue else "(no dialogue)"
        print(f"        Panel {p.panel_number}: {p.camera.value} | {dialogue_preview}")


# ============================================================
# Test 3: Image Generator (requires FAL_API_KEY)
# ============================================================

async def test_image_generator():
    """Test image generation (requires FAL_API_KEY, costs ~$0.04)."""
    api_key = os.environ.get("FAL_API_KEY")
    if not api_key:
        print("  SKIP: FAL_API_KEY not set")
        return

    from comic_pipeline.models import ComicProject, Panel, CameraHint
    from comic_pipeline.image_generator import FluxImageGenerator

    project = ComicProject(
        title="Test",
        theme_id="test",
        panels=[
            Panel(
                panel_number=1,
                image_prompt=(
                    "Watercolor and ink illustration. A weathered fisherman with "
                    "grey beard, blue tunic, and leather boots stands on a wooden dock "
                    "at sunrise. He holds a simple hemp net. Behind him, a small "
                    "coastal village with thatched-roof cottages. Warm earth tones, "
                    "soft golden light, Studio Ghibli style."
                ),
                camera=CameraHint.WIDE_SHOT,
            ),
        ],
    )

    generator = FluxImageGenerator()
    with tempfile.TemporaryDirectory() as tmpdir:
        project = await generator.generate_panels(project, tmpdir)
        await generator.close()

        assert project.panels[0].image_path, "Panel should have image path"
        assert Path(project.panels[0].image_path).exists(), "Image file should exist"
        size = Path(project.panels[0].image_path).stat().st_size
        assert size > 10000, f"Image too small ({size} bytes)"

    print(f"  PASS: Image generated ({size:,} bytes)")


# ============================================================
# Test 4: Panel Assembler
# ============================================================

def test_panel_assembler():
    """Test comic page assembly (no API keys needed)."""
    from PIL import Image
    from comic_pipeline.models import ComicProject, Panel, CameraHint
    from comic_pipeline.panel_assembler import PanelAssembler

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy panel images
        panels = []
        for i in range(1, 5):
            img_path = os.path.join(tmpdir, f"panel_{i:02d}.png")
            img = Image.new("RGB", (1024, 1024), color=(100 + i * 30, 80, 60))
            img.save(img_path)

            panels.append(Panel(
                panel_number=i,
                image_prompt="test",
                image_path=img_path,
                dialogue=[
                    {"speaker": "Elder", "text": f"This is panel {i}.", "style": "normal"},
                ],
                narration=f"And so the story continued..." if i % 2 == 0 else "",
                camera=CameraHint.MEDIUM_SHOT,
            ))

        project = ComicProject(
            title="Assembly Test",
            theme_id="test",
            panels=panels,
        )

        assembler = PanelAssembler()

        # Assemble pages
        pages_dir = os.path.join(tmpdir, "pages")
        project = assembler.assemble_pages(project, pages_dir)
        assert len(project.pages) == 1, f"Expected 1 page, got {len(project.pages)}"
        assert Path(project.pages[0].image_path).exists(), "Page image should exist"

        # Generate PDF
        pdf_path = os.path.join(tmpdir, "test.pdf")
        assembler.generate_pdf(project, pdf_path)
        assert Path(pdf_path).exists(), "PDF should exist"
        assert Path(pdf_path).stat().st_size > 1000, "PDF should have content"

        # Export social panels
        social_dir = os.path.join(tmpdir, "social")
        exports = assembler.export_social_panels(project, social_dir)
        assert len(exports) == 4, f"Expected 4 social exports, got {len(exports)}"

    print(f"  PASS: Assembly works — 1 page, 1 PDF, 4 social exports")


# ============================================================
# Test 5: Motion Comic (requires FFmpeg)
# ============================================================

async def test_motion_comic():
    """Test motion comic video generation (requires FFmpeg, no API keys)."""
    from PIL import Image
    from comic_pipeline.models import ComicProject, Panel, CameraHint
    from comic_pipeline.motion_comic import MotionComicGenerator

    generator = MotionComicGenerator()

    # Check FFmpeg availability
    try:
        generator._find_ffmpeg()
    except RuntimeError:
        print("  SKIP: FFmpeg not found")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create dummy panel images
        panels = []
        for i in range(1, 4):
            img_path = os.path.join(tmpdir, f"panel_{i:02d}.png")
            img = Image.new("RGB", (1920, 1080), color=(100 + i * 40, 80, 60))
            img.save(img_path)

            panels.append(Panel(
                panel_number=i,
                image_prompt="test",
                image_path=img_path,
                audio_duration=3.0,  # 3 seconds per panel (no real audio)
                camera=CameraHint.MEDIUM_SHOT,
            ))

        project = ComicProject(title="Video Test", theme_id="test", panels=panels)

        video_path = os.path.join(tmpdir, "test_motion.mp4")
        await generator.create_motion_comic(
            project=project,
            output_path=video_path,
        )

        assert Path(video_path).exists(), "Video should exist"
        size = Path(video_path).stat().st_size
        assert size > 10000, f"Video too small ({size} bytes)"

    print(f"  PASS: Motion comic generated ({size:,} bytes)")


# ============================================================
# Test 6: End-to-End (requires all API keys, costs ~$0.41)
# ============================================================

async def test_end_to_end():
    """Full pipeline test — theme → script → panels → pages → PDF → video."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    fal_key = os.environ.get("FAL_API_KEY")
    if not api_key:
        print("  SKIP: ANTHROPIC_API_KEY not set")
        return
    if not fal_key:
        print("  SKIP: FAL_API_KEY not set")
        return

    from comic_pipeline import ComicParablePipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        pipeline = ComicParablePipeline(output_root=tmpdir)

        project = await pipeline.generate(
            theme=(
                "The Fisherman's Free Net — A fisherman in a coastal village is "
                "given a free net by a stranger from the kingdom. Best net he's "
                "ever used. Then he notices it counts every fish and reports his "
                "catch to someone he's never met."
            ),
            panel_count=6,
            skip_video=not bool(os.environ.get("ELEVENLABS_API_KEY")),
        )

        await pipeline.close()

        assert project.title, "Should have title"
        assert len(project.panels) >= 4, f"Expected 4+ panels"
        assert project.pdf_path, "Should have PDF"
        assert Path(project.pdf_path).exists(), "PDF should exist"
        assert len(project.panel_exports) > 0, "Should have social exports"

        print(f"  PASS: End-to-end complete!")
        print(f"        Title: {project.title}")
        print(f"        Panels: {len(project.panels)}")
        print(f"        Pages: {len(project.pages)}")
        print(f"        PDF: {project.pdf_path}")
        print(f"        Video: {project.video_path or '(skipped)'}")
        print(f"        Social exports: {len(project.panel_exports)}")
        print(f"        Total cost: ${project.total_cost:.4f}")


# ============================================================
# Test 7: Approval Queue format
# ============================================================

def test_approval_queue_format():
    """Test comic_distribute format in approval queue."""
    from core.approval_queue import ApprovalQueue

    queue = ApprovalQueue(db_path=":memory:")

    # Simulate a comic_distribute approval
    approval = {
        "action_type": "comic_distribute",
        "action_data": json.dumps({
            "title": "The Fisherman's Free Net",
            "panel_count": 8,
            "synopsis": "A fisherman discovers his free net reports his catch.",
            "pdf_path": "data/comics/test/test.pdf",
            "video_path": "data/comics/test/test.mp4",
            "total_cost": 0.41,
        }),
    }

    preview = queue.format_preview(approval)
    assert "Fisherman" in preview
    assert "8 panels" in preview
    assert "$0.41" in preview

    print(f"  PASS: Approval queue formats comic_distribute correctly")


# ============================================================
# Test 8: David Flip comic_script channel
# ============================================================

def test_comic_script_channel():
    """Test comic_script channel exists in David Flip personality."""
    from personality.david_flip import DavidFlipPersonality

    personality = DavidFlipPersonality()
    prompt = personality.get_system_prompt("comic_script")

    assert "COMIC SCRIPT RULES" in prompt
    assert "watercolor" in prompt.lower() or "Watercolor" in prompt
    assert "Studio Ghibli" in prompt

    print(f"  PASS: comic_script channel overlay works")


# ============================================================
# Runner
# ============================================================

def main():
    """Run tests."""
    specific = sys.argv[1] if len(sys.argv) > 1 else None

    tests = {
        "test_models": (test_models, False),
        "test_script_parser": (test_script_parser, True),
        "test_image_generator": (test_image_generator, True),
        "test_panel_assembler": (test_panel_assembler, False),
        "test_motion_comic": (test_motion_comic, True),
        "test_end_to_end": (test_end_to_end, True),
        "test_approval_queue_format": (test_approval_queue_format, False),
        "test_comic_script_channel": (test_comic_script_channel, False),
    }

    if specific:
        if specific not in tests:
            print(f"Unknown test: {specific}")
            print(f"Available: {', '.join(tests.keys())}")
            sys.exit(1)
        tests = {specific: tests[specific]}

    passed = 0
    failed = 0
    skipped = 0

    print("\nComic Pipeline Tests")
    print("=" * 50)

    for name, (func, is_async) in tests.items():
        print(f"\n{name}:")
        try:
            if is_async:
                asyncio.run(func())
            else:
                func()
            passed += 1
        except Exception as e:
            if "SKIP" in str(e):
                skipped += 1
            else:
                print(f"  FAIL: {e}")
                import traceback
                traceback.print_exc()
                failed += 1

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed, {skipped} skipped")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

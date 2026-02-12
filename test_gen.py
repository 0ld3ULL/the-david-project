"""Full pipeline test: script -> approval -> images -> pages/PDF -> video."""
import asyncio
import logging
import sys
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(name)s - %(message)s", stream=sys.stdout)


async def main():
    from comic_pipeline import ComicParablePipeline

    pipeline = ComicParablePipeline(
        output_root="data/comics",
    )

    try:
        # Step 1: Generate script only (Opus)
        print("\n" + "=" * 60)
        print("STEP 1: Generating story script (Opus)...")
        print("=" * 60)

        project = await pipeline.generate_script_only(
            theme="How social media platforms give you a voice, then control what you can say with it",
            panel_count=8,
        )

        # Show the story for review
        print("\n" + project.format_for_review())

        # Step 2: Approval (in a real system this would wait for user input)
        print("\n" + "=" * 60)
        print("STEP 2: Script approved — continuing to images + video...")
        print("=" * 60)

        project = await pipeline.generate_from_project(
            project=project,
            skip_video=False,
        )

        print("\n" + "=" * 60)
        print(f"TITLE: {project.title}")
        print(f"PANELS: {len(project.panels)}")
        word_count = len(project.parable_text.split()) if project.parable_text else 0
        print(f"WORD COUNT: {word_count}")
        print(f"OUTPUT DIR: {project.output_dir}")
        print(f"PDF: {project.pdf_path}")
        print(f"VIDEO: {project.video_path}")
        print(f"SOCIAL PANELS: {len(project.panel_exports)}")
        print(f"TOTAL COST: ${project.total_cost:.4f}")
        print("=" * 60)
        print()
        print("PARABLE TEXT:")
        print(project.parable_text)
        print()
        print("GENERATION LOG:")
        for entry in project.generation_log:
            print(f"  {entry}")

    finally:
        await pipeline.close()


asyncio.run(main())

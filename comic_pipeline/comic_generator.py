"""
Comic Pipeline — Main Orchestrator.

ComicParablePipeline ties all stages together:
  Theme → Script → Images → Judge → Pages/PDF → Motion Comic Video

One generation run → four content formats:
1. Individual panel images (for social posts / NFT)
2. Assembled comic pages (PNG)
3. Multi-page PDF (for download / print)
4. Motion comic video (MP4 with narration + music)
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from comic_pipeline.models import ComicProject
from comic_pipeline.script_parser import ScriptParser
from comic_pipeline.leonardo_generator import LeonardoImageGenerator
from comic_pipeline.image_judge import ImageJudge
from comic_pipeline.panel_assembler import PanelAssembler
from comic_pipeline.motion_comic import MotionComicGenerator

logger = logging.getLogger(__name__)

# Default output root
OUTPUT_ROOT = Path("data/comics")

# Default music volume (low — narration is primary)
DEFAULT_MUSIC_VOLUME = 0.06


class ComicParablePipeline:
    """
    End-to-end comic parable generator.

    Usage:
        pipeline = ComicParablePipeline()
        project = await pipeline.generate(
            theme="The Fisherman's Free Net — A fisherman was given a free net...",
        )
        # project.pdf_path, project.video_path, project.panel_exports are all set
    """

    def __init__(
        self,
        model_router=None,
        output_root: Optional[str] = None,
    ):
        self.script_parser = ScriptParser(model_router=model_router)
        self.image_generator = LeonardoImageGenerator()
        self.image_judge = ImageJudge(model_router=model_router)
        self.panel_assembler = PanelAssembler()
        self.motion_comic = MotionComicGenerator()
        self.output_root = Path(output_root) if output_root else OUTPUT_ROOT

    async def generate(
        self,
        theme: str,
        theme_id: str = "",
        panel_count: int = 8,
        reference_image_url: Optional[str] = None,
        music_path: Optional[str] = None,
        music_volume: float = DEFAULT_MUSIC_VOLUME,
        auto_music: bool = True,
        skip_video: bool = False,
        skip_judge: bool = False,
        personality_prompt: str = "",
        on_progress: Optional[callable] = None,
    ) -> ComicProject:
        """
        Generate a complete comic parable.

        Args:
            theme: Parable theme/description
            theme_id: Optional ID for the theme (auto-generated if empty)
            panel_count: Target number of panels (6-10, default 8)
            reference_image_url: Starting character reference image URL
            music_path: Background music for motion comic
            music_volume: Music volume level (default 0.06 — subtle)
            auto_music: Auto-select music from library if no music_path
            skip_video: If True, skip motion comic video generation
            skip_judge: If True, skip image quality verification
            personality_prompt: David Flip personality overlay for script generation
            on_progress: Optional callback(stage: str, details: dict)

        Returns:
            ComicProject with all outputs populated
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # === Stage 1: Generate Script ===
        self._progress(on_progress, "script", {"theme": theme})
        logger.info("=" * 60)
        logger.info(f"COMIC PIPELINE: {theme[:60]}")
        logger.info("=" * 60)

        project = await self.script_parser.generate_script(
            theme=theme,
            panel_count=panel_count,
            personality_prompt=personality_prompt,
        )

        # Set up output directory
        slug = project.theme_id or theme_id or "untitled"
        project_dir = self.output_root / f"{slug}_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)
        project.output_dir = str(project_dir)

        logger.info(f"Script: '{project.title}' — {len(project.panels)} panels")
        logger.info(f"Output: {project_dir}")

        # === Stage 2: Generate Panel Images ===
        self._progress(on_progress, "images", {"panel_count": len(project.panels)})
        logger.info("Generating panel images (Leonardo)...")

        images_dir = str(project_dir / "panels")
        project = await self.image_generator.generate_panels(
            project=project,
            output_dir=images_dir,
            reference_image_url=reference_image_url,
        )

        panels_ok = sum(1 for p in project.panels if p.image_path)
        logger.info(f"Images: {panels_ok}/{len(project.panels)} panels generated")

        if panels_ok == 0:
            logger.error("No panel images generated — aborting pipeline")
            project.log("ABORTED: No images generated")
            return project

        # === Stage 2.5: Image Quality Check ===
        if not skip_judge:
            self._progress(on_progress, "judge", {"panels": panels_ok})
            logger.info("Judging image quality...")

            project = await self.image_judge.judge_panels(
                project=project,
                max_retries=1,
                regenerator=self.image_generator,
            )

        # === Stage 3: Assemble Comic Pages + PDF ===
        self._progress(on_progress, "assembly", {"panels_ok": panels_ok})
        logger.info("Assembling comic pages...")

        pages_dir = str(project_dir / "pages")
        project = self.panel_assembler.assemble_pages(
            project=project,
            output_dir=pages_dir,
        )

        # Generate PDF
        pdf_path = str(project_dir / f"{slug}_comic.pdf")
        self.panel_assembler.generate_pdf(project, pdf_path)

        # Export individual social panels
        social_dir = str(project_dir / "social_panels")
        self.panel_assembler.export_social_panels(project, social_dir)

        # === Stage 4: Motion Comic Video ===
        if not skip_video:
            self._progress(on_progress, "video", {"panels": panels_ok})
            logger.info("Creating motion comic video...")

            # Generate narration audio
            audio_dir = str(project_dir / "audio")
            project = await self.motion_comic.generate_narration(
                project=project,
                output_dir=audio_dir,
            )

            # Auto-select music if requested
            if auto_music and not music_path:
                try:
                    from video_pipeline.music_library import MusicLibrary
                    library = MusicLibrary()
                    # Use first panel's mood for music selection
                    mood = project.panels[0].mood if project.panels else "contemplative"
                    music_path = library.get_track(mood)
                    if music_path:
                        logger.info(f"Auto-selected music: {music_path} ({mood})")
                except Exception as e:
                    logger.warning(f"Music auto-selection failed: {e}")

            # Generate motion comic
            video_path = str(project_dir / f"{slug}_motion_comic.mp4")
            await self.motion_comic.create_motion_comic(
                project=project,
                output_path=video_path,
                music_path=music_path,
                music_volume=music_volume,
            )

        # === Save summary ===
        summary_path = str(project_dir / "README.txt")
        self._save_summary(project, summary_path)

        # === Done ===
        self._progress(on_progress, "complete", project.to_dict())

        logger.info("=" * 60)
        logger.info("COMIC PIPELINE COMPLETE")
        logger.info(f"  Title: {project.title}")
        logger.info(f"  Panels: {panels_ok}")
        logger.info(f"  Pages: {len(project.pages)}")
        logger.info(f"  PDF: {project.pdf_path}")
        logger.info(f"  Video: {project.video_path}")
        logger.info(f"  Social exports: {len(project.panel_exports)}")
        logger.info(f"  Total cost: ${project.total_cost:.4f}")
        logger.info("=" * 60)

        return project

    async def generate_script_only(
        self,
        theme: str,
        panel_count: int = 8,
        personality_prompt: str = "",
    ) -> ComicProject:
        """Generate just the script (for preview / approval before spending on images)."""
        return await self.script_parser.generate_script(
            theme=theme,
            panel_count=panel_count,
            personality_prompt=personality_prompt,
        )

    async def generate_from_project(
        self,
        project: ComicProject,
        theme_id: str = "",
        reference_image_url: Optional[str] = None,
        music_path: Optional[str] = None,
        music_volume: float = DEFAULT_MUSIC_VOLUME,
        auto_music: bool = True,
        skip_video: bool = False,
        skip_judge: bool = False,
        on_progress: Optional[callable] = None,
    ) -> ComicProject:
        """
        Continue pipeline from an already-approved ComicProject (Stages 2-4).

        Use this after generate_script_only() + user approval:
            project = await pipeline.generate_script_only(theme)
            # ... user reviews project.story_text, project.panels ...
            project = await pipeline.generate_from_project(project)

        Args:
            project: Approved ComicProject with script/panels already set
            theme_id: Optional ID override
            reference_image_url: Starting character reference image URL
            music_path: Background music for motion comic
            music_volume: Music volume level (default 0.06)
            auto_music: Auto-select music from library if no music_path
            skip_video: If True, skip motion comic video generation
            skip_judge: If True, skip image quality verification
            on_progress: Optional callback(stage: str, details: dict)

        Returns:
            ComicProject with all outputs populated
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Set up output directory
        slug = theme_id or project.theme_id or "untitled"
        project_dir = self.output_root / f"{slug}_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)
        project.output_dir = str(project_dir)

        logger.info("=" * 60)
        logger.info(f"COMIC PIPELINE (from approved script): {project.title}")
        logger.info(f"  Panels: {len(project.panels)}")
        logger.info(f"  Output: {project_dir}")
        logger.info("=" * 60)

        # === Stage 2: Generate Panel Images ===
        self._progress(on_progress, "images", {"panel_count": len(project.panels)})
        logger.info("Generating panel images (Leonardo)...")

        images_dir = str(project_dir / "panels")
        project = await self.image_generator.generate_panels(
            project=project,
            output_dir=images_dir,
            reference_image_url=reference_image_url,
        )

        panels_ok = sum(1 for p in project.panels if p.image_path)
        logger.info(f"Images: {panels_ok}/{len(project.panels)} panels generated")

        if panels_ok == 0:
            logger.error("No panel images generated — aborting pipeline")
            project.log("ABORTED: No images generated")
            return project

        # === Stage 2.5: Image Quality Check ===
        if not skip_judge:
            self._progress(on_progress, "judge", {"panels": panels_ok})
            logger.info("Judging image quality...")

            project = await self.image_judge.judge_panels(
                project=project,
                max_retries=1,
                regenerator=self.image_generator,
            )

        # === Stage 3: Assemble Comic Pages + PDF ===
        self._progress(on_progress, "assembly", {"panels_ok": panels_ok})
        logger.info("Assembling comic pages...")

        pages_dir = str(project_dir / "pages")
        project = self.panel_assembler.assemble_pages(
            project=project,
            output_dir=pages_dir,
        )

        # Generate PDF
        pdf_path = str(project_dir / f"{slug}_comic.pdf")
        self.panel_assembler.generate_pdf(project, pdf_path)

        # Export individual social panels
        social_dir = str(project_dir / "social_panels")
        self.panel_assembler.export_social_panels(project, social_dir)

        # === Stage 4: Motion Comic Video ===
        if not skip_video:
            self._progress(on_progress, "video", {"panels": panels_ok})
            logger.info("Creating motion comic video...")

            # Generate narration audio
            audio_dir = str(project_dir / "audio")
            project = await self.motion_comic.generate_narration(
                project=project,
                output_dir=audio_dir,
            )

            # Auto-select music if requested
            if auto_music and not music_path:
                try:
                    from video_pipeline.music_library import MusicLibrary
                    library = MusicLibrary()
                    mood = project.panels[0].mood if project.panels else "contemplative"
                    music_path = library.get_track(mood)
                    if music_path:
                        logger.info(f"Auto-selected music: {music_path} ({mood})")
                except Exception as e:
                    logger.warning(f"Music auto-selection failed: {e}")

            # Generate motion comic
            video_path = str(project_dir / f"{slug}_motion_comic.mp4")
            await self.motion_comic.create_motion_comic(
                project=project,
                output_path=video_path,
                music_path=music_path,
                music_volume=music_volume,
            )

        # === Save summary ===
        summary_path = str(project_dir / "README.txt")
        self._save_summary(project, summary_path)

        # === Done ===
        self._progress(on_progress, "complete", project.to_dict())

        logger.info("=" * 60)
        logger.info("COMIC PIPELINE COMPLETE")
        logger.info(f"  Title: {project.title}")
        logger.info(f"  Panels: {panels_ok}")
        logger.info(f"  Pages: {len(project.pages)}")
        logger.info(f"  PDF: {project.pdf_path}")
        logger.info(f"  Video: {project.video_path}")
        logger.info(f"  Social exports: {len(project.panel_exports)}")
        logger.info(f"  Total cost: ${project.total_cost:.4f}")
        logger.info("=" * 60)

        return project

    async def close(self):
        """Clean up resources."""
        await self.image_generator.close()

    def _save_summary(self, project: ComicProject, path: str):
        """Save a human-readable summary of the comic."""
        lines = [
            f"COMIC PARABLE: {project.title}",
            f"{'=' * 50}",
            f"",
            f"Synopsis: {project.synopsis}",
            f"Panels: {len(project.panels)}",
            f"Pages: {len(project.pages)}",
            f"Total cost: ${project.total_cost:.4f}",
            f"",
            f"FILES IN THIS FOLDER:",
            f"  panels/          — Raw AI-generated panel images",
            f"  pages/           — Assembled comic pages (panels + speech bubbles)",
            f"  social_panels/   — Individual panels with captions (for social media)",
        ]
        if project.pdf_path:
            pdf_name = Path(project.pdf_path).name
            lines.append(f"  {pdf_name}  — Full comic PDF (printable)")
        if project.video_path:
            video_name = Path(project.video_path).name
            lines.append(f"  {video_name}  — Motion comic video")
        lines.append(f"")
        lines.append(f"PANELS:")
        for p in project.panels:
            lines.append(f"  Panel {p.panel_number}: [{p.camera.value}]")
            if p.narration:
                lines.append(f"    Narration: {p.narration}")
            for d in p.dialogue:
                lines.append(f"    {d['speaker']}: \"{d['text']}\"")
        lines.append(f"")

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            logger.warning(f"Failed to save summary: {e}")

    def _progress(self, callback, stage: str, details: dict):
        """Report progress if callback is set."""
        if callback:
            try:
                callback(stage, details)
            except Exception:
                pass

"""
Cinematic Video Pipeline - Fully automated video creation.

Creates atmospheric/cinematic videos like:
- Cyberpunk cityscapes with narration
- Abstract visuals with voiceover
- Story-driven visual narratives

Pipeline:
1. Claude generates script + scene descriptions
2. Leonardo generates scene images
3. Runway animates images into video
4. ElevenLabs generates voice narration
5. ElevenLabs video-to-music creates soundtrack (via browser automation)
6. FFmpeg assembles final video

Human only approves final output.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Scene:
    """A single scene in the video."""
    description: str  # Visual description for image generation
    motion_prompt: str  # Motion description for animation
    duration: int = 5  # Scene duration in seconds
    image_path: Optional[str] = None
    image_url: Optional[str] = None  # Leonardo hosted URL (Runway needs this)
    video_path: Optional[str] = None


@dataclass
class VideoProject:
    """A complete video project."""
    title: str
    voiceover_script: str
    scenes: List[Scene]
    mood: str = "dark"  # For music generation
    voice_path: Optional[str] = None
    music_path: Optional[str] = None
    final_video_path: Optional[str] = None


class CinematicVideoPipeline:
    """
    Orchestrates fully automated cinematic video creation.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("data/video_pipeline/projects")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Lazy-loaded API clients
        self._leonardo = None
        self._runway = None
        self._elevenlabs = None

    def _get_leonardo(self):
        if self._leonardo is None:
            from video_pipeline.leonardo_api import LeonardoAPI
            self._leonardo = LeonardoAPI()
        return self._leonardo

    def _get_runway(self):
        if self._runway is None:
            from video_pipeline.runway_api import RunwayAPI
            self._runway = RunwayAPI()
        return self._runway

    def _get_elevenlabs(self):
        if self._elevenlabs is None:
            from tools.elevenlabs_tool import ElevenLabsTool
            self._elevenlabs = ElevenLabsTool()
        return self._elevenlabs

    async def create_video(
        self,
        project: VideoProject,
        on_progress: Optional[Callable[[str, dict], None]] = None,
        use_browser_music: bool = False,
        music_prompt: Optional[str] = None,
    ) -> str:
        """
        Create a complete cinematic video.

        Args:
            project: VideoProject with script and scene descriptions
            on_progress: Callback for progress updates
            use_browser_music: Use ElevenLabs browser automation for music
            music_prompt: Style hint for music generation

        Returns:
            Path to final video file
        """
        project_dir = self.output_dir / project.title.replace(" ", "_").lower()
        project_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Starting video project: {project.title}")
        logger.info(f"Scenes: {len(project.scenes)}")
        logger.info(f"Script: {project.voiceover_script[:100]}...")

        try:
            # Stage 1: Generate scene images
            if on_progress:
                await on_progress("generating_images", {"total": len(project.scenes)})
            await self._generate_images(project, project_dir, on_progress)

            # Stage 2: Animate scenes
            if on_progress:
                await on_progress("animating_scenes", {"total": len(project.scenes)})
            await self._animate_scenes(project, project_dir, on_progress)

            # Stage 3: Generate voiceover
            if on_progress:
                await on_progress("generating_voice", {"script_length": len(project.voiceover_script)})
            await self._generate_voice(project, project_dir)

            # Stage 4: Assemble video (scenes + voice)
            if on_progress:
                await on_progress("assembling_video", {})
            assembled_path = await self._assemble_video(project, project_dir)

            # Stage 5: Generate music
            if use_browser_music:
                if on_progress:
                    await on_progress("generating_music", {"method": "browser_automation"})
                await self._generate_music_browser(project, assembled_path, music_prompt)
            else:
                # Use pre-selected music from library
                if on_progress:
                    await on_progress("selecting_music", {"method": "library"})
                self._select_music_from_library(project)

            # Stage 6: Final mix
            if on_progress:
                await on_progress("final_mix", {})
            final_path = await self._final_mix(project, project_dir)

            project.final_video_path = final_path
            logger.info(f"Video complete: {final_path}")

            if on_progress:
                await on_progress("complete", {"video_path": final_path})

            return final_path

        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            if on_progress:
                await on_progress("failed", {"error": str(e)})
            raise

    async def _generate_images(
        self,
        project: VideoProject,
        project_dir: Path,
        on_progress: Optional[Callable],
    ):
        """Generate images for all scenes."""
        leonardo = self._get_leonardo()

        for i, scene in enumerate(project.scenes):
            logger.info(f"Generating image {i+1}/{len(project.scenes)}: {scene.description[:50]}...")

            if on_progress:
                await on_progress("generating_image", {"scene": i + 1, "total": len(project.scenes)})

            result = await leonardo.generate_image(
                prompt=scene.description,
                negative_prompt="text, watermark, logo, blurry, low quality",
                style="CINEMATIC",
            )

            # Store hosted URL (Runway needs this) and download locally
            scene.image_url = result["image_url"]
            image_data = await leonardo.download_image(result["image_url"])
            image_path = project_dir / f"scene_{i+1:02d}.png"
            image_path.write_bytes(image_data)
            scene.image_path = str(image_path)

            logger.info(f"Image saved: {image_path}")

    async def _animate_scenes(
        self,
        project: VideoProject,
        project_dir: Path,
        on_progress: Optional[Callable],
    ):
        """Animate all scene images into videos."""
        runway = self._get_runway()

        for i, scene in enumerate(project.scenes):
            if not scene.image_url:
                raise RuntimeError(f"Scene {i+1} has no image URL")

            logger.info(f"Animating scene {i+1}/{len(project.scenes)}: {scene.motion_prompt[:50]}...")

            if on_progress:
                await on_progress("animating_scene", {"scene": i + 1, "total": len(project.scenes)})

            result = await runway.animate_image(
                image_url=scene.image_url,
                motion_prompt=scene.motion_prompt,
                duration=scene.duration,
            )

            # Download and save video
            video_data = await runway.download_video(result["video_url"])
            video_path = project_dir / f"scene_{i+1:02d}.mp4"
            video_path.write_bytes(video_data)
            scene.video_path = str(video_path)

            logger.info(f"Video saved: {video_path}")

    async def _generate_voice(self, project: VideoProject, project_dir: Path):
        """Generate voiceover narration."""
        elevenlabs = self._get_elevenlabs()

        logger.info("Generating voiceover...")

        audio_data = await elevenlabs.text_to_speech(
            text=project.voiceover_script,
            model="eleven_v3",
            stability=0.0,  # Creative mode
            style=0.85,  # High emotion
        )

        voice_path = project_dir / "voiceover.mp3"
        voice_path.write_bytes(audio_data)
        project.voice_path = str(voice_path)

        logger.info(f"Voiceover saved: {voice_path}")

    async def _assemble_video(self, project: VideoProject, project_dir: Path) -> str:
        """Assemble scene videos with voiceover."""
        # Create concat file for FFmpeg
        concat_path = project_dir / "concat.txt"
        with open(concat_path, "w") as f:
            for scene in project.scenes:
                if scene.video_path:
                    # Escape path for FFmpeg
                    escaped = scene.video_path.replace("\\", "/").replace("'", "'\\''")
                    f.write(f"file '{escaped}'\n")

        assembled_path = project_dir / "assembled.mp4"

        # Concatenate videos (async to avoid blocking event loop)
        await self._run_ffmpeg(
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_path),
            "-c", "copy",
            str(assembled_path),
        )

        # Add voiceover as sole audio track (Runway output has no audio)
        with_voice_path = project_dir / "with_voice.mp4"
        await self._run_ffmpeg(
            "ffmpeg", "-y",
            "-i", str(assembled_path),
            "-i", project.voice_path,
            "-map", "0:v",
            "-map", "1:a",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(with_voice_path),
        )

        logger.info(f"Assembled video: {with_voice_path}")
        return str(with_voice_path)

    async def _generate_music_browser(
        self,
        project: VideoProject,
        video_path: str,
        prompt: Optional[str] = None,
    ):
        """Generate music using ElevenLabs browser automation."""
        from video_pipeline.music_automation import generate_music_for_video

        music_prompt = prompt or f"{project.mood} cinematic ambient"

        logger.info(f"Generating music via browser: {music_prompt}")

        music_path = await generate_music_for_video(
            video_path=video_path,
            prompt=music_prompt,
            headless=False,  # Show browser for debugging
        )

        project.music_path = music_path
        logger.info(f"Music generated: {music_path}")

    def _select_music_from_library(self, project: VideoProject):
        """Select music from pre-curated library based on mood."""
        from video_pipeline.music_library import MusicLibrary

        track = MusicLibrary().get_track(project.mood)
        if track:
            project.music_path = track
            logger.info(f"Selected music from library: {track}")
        else:
            logger.warning("No suitable music found in library")

    async def _final_mix(self, project: VideoProject, project_dir: Path) -> str:
        """Mix everything together for final output."""
        final_path = project_dir / f"{project.title.replace(' ', '_')}_FINAL.mp4"

        # Get the video with voice
        video_with_voice = project_dir / "with_voice.mp4"

        if project.music_path:
            # Mix in music (async to avoid blocking event loop)
            await self._run_ffmpeg(
                "ffmpeg", "-y",
                "-i", str(video_with_voice),
                "-i", project.music_path,
                "-filter_complex",
                "[0:a]volume=1.0[voice];[1:a]volume=0.3,afade=t=out:st=8:d=2[music];[voice][music]amix=inputs=2:duration=first[out]",
                "-map", "0:v",
                "-map", "[out]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                str(final_path),
            )
        else:
            # Just copy video with voice
            import shutil
            shutil.copy(str(video_with_voice), str(final_path))

        logger.info(f"Final video: {final_path}")
        return str(final_path)

    async def _run_ffmpeg(self, *cmd: str):
        """Run FFmpeg asynchronously to avoid blocking the event loop."""
        logger.info(f"Running FFmpeg: {' '.join(cmd[:6])}...")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}): {stderr.decode()}")


async def generate_script(topic: str, style: str = "cyberpunk") -> dict:
    """
    Generate a video script using ModelRouter + David's video_script personality.

    Returns:
        dict with 'script', 'scene_description', 'motion_prompt', 'mood'
    """
    from core.model_router import ModelRouter
    from personality.david_flip import DavidFlipPersonality

    personality = DavidFlipPersonality()
    system_prompt = personality.get_system_prompt("video_script")

    router = ModelRouter()
    model = router.select_model("content")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": (
            f"Write a cinematic video script about: {topic}\n"
            f"Visual style: {style}\n\n"
            f"Return EXACTLY this format (no extra text):\n"
            f"SCRIPT: <your voiceover script>\n"
            f"SCENE: <visual description for AI image generation>\n"
            f"MOTION: <camera/motion description for animation>\n"
            f"MOOD: <one word mood for music selection>"
        )},
    ]

    result = await router.invoke(model, messages, max_tokens=1024)
    text = result.get("content", "")

    # Parse structured response
    script = ""
    scene_desc = f"Cinematic {style} scene, {topic}, atmospheric, moody lighting, film grain"
    motion = "Slow cinematic camera push forward, subtle movement, atmospheric"
    mood = "dark"

    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("SCRIPT:"):
            script = line[7:].strip()
        elif line.startswith("SCENE:"):
            scene_desc = line[6:].strip()
        elif line.startswith("MOTION:"):
            motion = line[7:].strip()
        elif line.startswith("MOOD:"):
            mood = line[5:].strip().lower()

    # If SCRIPT: was on its own line, grab everything after it until the next tag
    if not script:
        in_script = False
        script_lines = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("SCRIPT:"):
                in_script = True
                remainder = stripped[7:].strip()
                if remainder:
                    script_lines.append(remainder)
            elif stripped.startswith(("SCENE:", "MOTION:", "MOOD:")):
                in_script = False
            elif in_script:
                script_lines.append(stripped)
        script = " ".join(script_lines)

    # Final fallback if parsing failed completely
    if not script:
        script = text.strip()

    return {
        "script": script,
        "scene_description": scene_desc,
        "motion_prompt": motion,
        "mood": mood,
    }


async def create_video_from_topic(
    topic: str,
    style: str = "cyberpunk",
    on_progress: Optional[Callable] = None,
) -> str:
    """
    High-level function to create a video from just a topic.

    Uses Claude to generate script and scene descriptions.

    Args:
        topic: What the video should be about
        style: Visual style (cyberpunk, nature, abstract, etc.)
        on_progress: Progress callback

    Returns:
        Path to final video
    """
    generated = await generate_script(topic, style)

    project = VideoProject(
        title=f"david_flip_{topic.replace(' ', '_')}",
        voiceover_script=generated["script"],
        scenes=[
            Scene(
                description=generated["scene_description"],
                motion_prompt=generated["motion_prompt"],
            )
        ],
        mood=generated["mood"],
    )

    pipeline = CinematicVideoPipeline()
    return await pipeline.create_video(project, on_progress)

"""
Video Creator - Orchestrates the full video generation pipeline.

Flow:
1. Generate script (optional, can be provided)
2. Generate audio via ElevenLabs
3. Add silence padding (prevents Hedra cutting off at last word)
4. Generate lip-sync video via Hedra
5. Post-process with FFmpeg (fades, music mixing)
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Optional

import httpx

from video_pipeline.music_library import MusicLibrary, get_music_for_script

logger = logging.getLogger(__name__)

# Default character images
CHARACTER_IMAGES = {
    "direct": "https://playaverse.org/david-flip.png",       # Straight to camera
    "podcast": "https://playaverse.org/david-flip-podcast.png",  # Podcast style
}


class VideoCreator:
    """Orchestrates video creation: TTS -> Lip-sync -> Post-process."""

    def __init__(self):
        from tools.elevenlabs_tool import ElevenLabsTool
        from tools.hedra_tool import HedraTool

        self.elevenlabs = ElevenLabsTool()
        self.hedra = HedraTool()
        self._postprocessor = None
        self._ffmpeg_path: Optional[str] = None

    def _get_postprocessor(self):
        """Lazy-load postprocessor (requires FFmpeg)."""
        if self._postprocessor is None:
            try:
                from video_pipeline.postprocessor import VideoPostProcessor
                self._postprocessor = VideoPostProcessor()
            except Exception as e:
                logger.warning(f"Postprocessor not available: {e}")
                self._postprocessor = False  # Mark as unavailable
        return self._postprocessor if self._postprocessor else None

    def _get_ffmpeg(self) -> str:
        """Find FFmpeg executable."""
        if self._ffmpeg_path:
            return self._ffmpeg_path

        paths = [
            "ffmpeg",
            r"C:fmpeginfmpeg.exe",
            r"C:\Program Filesfmpeginfmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]

        for path in paths:
            try:
                result = subprocess.run(
                    [path, "-version"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    self._ffmpeg_path = path
                    return path
            except:
                continue

        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")

    async def create_video(
        self,
        script: str,
        character_image_url: Optional[str] = None,
        character_style: str = "direct",  # "direct" or "podcast"
        voice_id: Optional[str] = None,
        aspect_ratio: str = "9:16",
        output_path: Optional[str] = None,
        add_silence_padding: bool = True,
        apply_fades: bool = True,
        music_path: Optional[str] = None,
        music_volume: float = 0.3,
        auto_music: bool = True,  # Auto-select music based on script mood
        on_progress: Optional[Callable[[str, dict], None]] = None,
    ) -> dict:
        """
        Create a complete talking head video.

        Args:
            script: Text for the character to speak
            character_image_url: URL of the character image (overrides character_style)
            character_style: "direct" (camera) or "podcast" (side angle)
            voice_id: ElevenLabs voice ID (uses env default if not provided)
            aspect_ratio: Video aspect ratio (9:16, 16:9, 1:1)
            output_path: Where to save final video (uses temp if not provided)
            add_silence_padding: Add 2s silence to prevent Hedra cutoff
            apply_fades: Apply fade in/out effects (requires FFmpeg)
            music_path: Optional background music file
            music_volume: Background music volume (0.0-1.0)
            auto_music: If True and music_path is None, auto-select from library
            on_progress: Callback for progress updates

        Returns:
            dict with video_path, video_url, audio_path, generation_id
        """
        logger.info("=" * 50)
        logger.info("VIDEO CREATION STARTING")
        logger.info("=" * 50)
        logger.info(f"Script: {script[:100]}...")

        # Use default character image if not provided
        if not character_image_url:
            character_image_url = CHARACTER_IMAGES.get(character_style, CHARACTER_IMAGES["direct"])
        logger.info(f"Character style: {character_style}, Image: {character_image_url}")

        # Auto-select background music based on script mood
        if auto_music and not music_path:
            try:
                track, volume = get_music_for_script(script)
                if track:
                    music_path = track
                    music_volume = volume
                    logger.info(f"Auto-selected music: {track} (volume: {volume})")
                else:
                    logger.info("No music tracks available in library")
            except Exception as e:
                logger.warning(f"Music auto-selection failed: {e}")

        results = {}

        try:
            # Stage 1: Generate audio
            logger.info("Stage 1/4: Generating audio with ElevenLabs...")
            if on_progress:
                on_progress("generating_audio", {"script_length": len(script)})

            audio_data = await self.elevenlabs.text_to_speech(
                text=script,
                voice_id=voice_id,
            )
            logger.info(f"Audio generated: {len(audio_data)} bytes")

            # Stage 1.5: Add silence padding (prevents Hedra cutting off)
            if add_silence_padding:
                postprocessor = self._get_postprocessor()
                if postprocessor:
                    logger.info("Adding silence padding to audio...")
                    if on_progress:
                        on_progress("padding_audio", {})
                    audio_data = await postprocessor.add_silence_to_audio(audio_data)
                else:
                    logger.warning("Postprocessor unavailable - skipping silence padding")

            # Save audio to temp file
            audio_file = tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False, prefix="clawdbot_audio_"
            )
            audio_file.write(audio_data)
            audio_file.close()
            results["audio_path"] = audio_file.name
            logger.info(f"Audio saved: {audio_file.name} ({len(audio_data)} bytes)")

            # Stage 2: Generate lip-sync video
            logger.info("Stage 2/4: Generating lip-sync video with Hedra...")
            if on_progress:
                on_progress("generating_video", {"audio_size": len(audio_data)})

            hedra_result = await self.hedra.create_talking_head_video(
                character_image_url=character_image_url,
                audio_data=audio_data,
                aspect_ratio=aspect_ratio,
                on_progress=on_progress,
            )

            results["video_url"] = hedra_result["video_url"]
            results["generation_id"] = hedra_result["generation_id"]
            logger.info(f"Hedra video URL obtained")

            # Stage 3: Download video
            logger.info("Stage 3/4: Downloading video from Hedra...")
            if on_progress:
                on_progress("downloading", {"url": hedra_result["video_url"]})

            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.get(hedra_result["video_url"])
                if not response.is_success:
                    raise RuntimeError(f"Failed to download video: {response.status_code}")
                video_data = response.content

            # Save raw video
            raw_video_file = tempfile.NamedTemporaryFile(
                suffix=".mp4", delete=False, prefix="clawdbot_raw_"
            )
            raw_video_path = raw_video_file.name
            raw_video_file.close()
            with open(raw_video_path, "wb") as f:
                f.write(video_data)
            logger.info(f"Raw video saved: {raw_video_path} ({len(video_data)} bytes)")

            # Stage 4: Post-process (fades, music)
            video_path = raw_video_path
            if apply_fades or music_path:
                postprocessor = self._get_postprocessor()
                if postprocessor:
                    logger.info("Stage 4/4: Post-processing (fades, music)...")
                    if on_progress:
                        on_progress("postprocessing", {"fades": apply_fades, "music": bool(music_path)})

                    if output_path:
                        final_path = output_path
                    else:
                        final_file = tempfile.NamedTemporaryFile(
                            suffix=".mp4", delete=False, prefix="clawdbot_video_"
                        )
                        final_path = final_file.name
                        final_file.close()

                    video_path = await postprocessor.process_video(
                        video_path=raw_video_path,
                        output_path=final_path,
                        fade_in=apply_fades,
                        fade_out=apply_fades,
                        music_path=music_path,
                        music_volume=music_volume,
                    )

                    # Cleanup raw video
                    try:
                        os.unlink(raw_video_path)
                    except Exception:
                        pass
                else:
                    logger.warning("FFmpeg not available - skipping post-processing")
                    if output_path:
                        import shutil
                        shutil.move(raw_video_path, output_path)
                        video_path = output_path
            else:
                if output_path:
                    import shutil
                    shutil.move(raw_video_path, output_path)
                    video_path = output_path

            results["video_path"] = video_path
            logger.info(f"Final video: {video_path}")

            logger.info("=" * 50)
            logger.info("VIDEO CREATION COMPLETE")
            logger.info("=" * 50)

            if on_progress:
                on_progress("complete", results)

            return results

        except Exception as e:
            logger.error(f"Video creation failed: {e}")
            if on_progress:
                on_progress("failed", {"error": str(e)})
            raise

    def draft_video(
        self,
        script: str,
        character_image_url: str,
        voice_id: Optional[str] = None,
    ) -> dict:
        """Create a draft video generation for approval queue."""
        return {
            "action": "create_video",
            "script": script,
            "character_image_url": character_image_url,
            "voice_id": voice_id or os.environ.get("ELEVENLABS_VOICE_ID", ""),
        }

    async def execute(self, action_data: dict) -> dict:
        """Execute an approved video action."""
        action = action_data.get("action")

        if action == "create_video":
            try:
                result = await self.create_video(
                    script=action_data["script"],
                    character_image_url=action_data["character_image_url"],
                    voice_id=action_data.get("voice_id"),
                )
                return result
            except Exception as e:
                logger.error(f"Video creation failed: {e}")
                return {"error": str(e)}
        else:
            return {"error": f"Unknown action: {action}"}

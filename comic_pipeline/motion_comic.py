"""
Comic Pipeline — Motion Comic Generator.

Creates motion comic videos from comic panels:
1. ElevenLabs narration audio per panel (existing tool)
2. FFmpeg Ken Burns zoom/pan per panel (duration = audio length)
3. FFmpeg xfade transitions between panels (0.5s dissolve)
4. Background music from existing MusicLibrary
5. Final assembly: video + voice + music

Uses FFmpeg directly (no MoviePy) — follows existing postprocessor.py patterns.
"""

import asyncio
import logging
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from comic_pipeline.models import ComicProject, Panel

logger = logging.getLogger(__name__)

# Ken Burns effect parameters
KB_ZOOM_START = 1.0      # Start zoom level
KB_ZOOM_END = 1.15       # End zoom level (subtle 15% zoom in)
KB_PAN_PIXELS = 40       # Max pan offset in pixels

# Transition settings
TRANSITION_DURATION = 0.5   # Dissolve between panels (seconds)
MIN_PANEL_DURATION = 3.0    # Minimum seconds per panel (if no audio)
PADDING_AFTER_AUDIO = 0.8   # Extra seconds after narration ends

# Output video settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
VIDEO_CRF = 20  # Quality (lower = better, 18-23 typical)

# Auto-leveling: music peak must be at least this many dB below narration mean
MUSIC_HEADROOM_DB = 18


class MotionComicGenerator:
    """Creates motion comic videos with Ken Burns effects and narration."""

    def __init__(self):
        self._ffmpeg_path: Optional[str] = None
        self._ffprobe_path: Optional[str] = None

    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable (reuses postprocessor pattern)."""
        if self._ffmpeg_path:
            return self._ffmpeg_path

        import subprocess

        # Try imageio-ffmpeg bundled binary first (most reliable on Windows)
        try:
            import imageio_ffmpeg
            bundled = imageio_ffmpeg.get_ffmpeg_exe()
            if bundled:
                self._ffmpeg_path = bundled
                self._ffprobe_path = bundled.replace("ffmpeg", "ffprobe")
                # ffprobe may not exist in imageio bundle — check
                if not Path(self._ffprobe_path).exists():
                    self._ffprobe_path = bundled  # fallback, will use ffmpeg -i
                return bundled
        except ImportError:
            pass

        search_paths = [
            "ffmpeg",
            os.path.expanduser(
                r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"
            ),
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]

        for path in search_paths:
            try:
                result = subprocess.run(
                    [path, "-version"], capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    self._ffmpeg_path = path
                    # Derive ffprobe path
                    if "ffmpeg.exe" in path:
                        self._ffprobe_path = path.replace("ffmpeg.exe", "ffprobe.exe")
                    else:
                        self._ffprobe_path = path.replace("ffmpeg", "ffprobe")
                    return path
            except Exception:
                continue

        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")

    async def _get_media_duration(self, media_path: str) -> float:
        """Get audio/video duration using ffmpeg -i (works without ffprobe)."""
        ffmpeg = self._find_ffmpeg()
        proc = await asyncio.create_subprocess_exec(
            ffmpeg, "-i", media_path, "-hide_banner",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        # ffmpeg -i prints info to stderr, including "Duration: HH:MM:SS.ss"
        output = stderr.decode(errors="replace")
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", output)
        if not match:
            raise RuntimeError(f"Could not parse duration from: {media_path}")
        h, m, s, cs = match.groups()
        return int(h) * 3600 + int(m) * 60 + int(s) + int(cs) / 100

    async def generate_narration(
        self,
        project: ComicProject,
        output_dir: str,
    ) -> ComicProject:
        """
        Generate ElevenLabs narration audio for each panel.

        Only generates audio for panels that have narration text.
        Sets audio_path and audio_duration on each panel.

        Args:
            project: ComicProject with panels
            output_dir: Directory for audio files

        Returns:
            Updated project with audio_path/audio_duration set
        """
        from tools.elevenlabs_tool import ElevenLabsTool
        tts = ElevenLabsTool()

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        for panel in project.panels:
            # Build narration text: narration + dialogue
            narration_parts = []
            if panel.narration:
                narration_parts.append(panel.narration)
            for d in panel.dialogue:
                text = d.get("text", "")
                speaker = d.get("speaker", "")
                if text:
                    narration_parts.append(f"{speaker} says: {text}" if speaker else text)

            if not narration_parts:
                panel.audio_duration = MIN_PANEL_DURATION
                continue

            full_text = " — — ".join(narration_parts)  # Em-dash pauses between parts
            audio_path = str(Path(output_dir) / f"narration_{panel.panel_number:02d}.mp3")

            try:
                audio_data = await tts.text_to_speech(text=full_text)
                with open(audio_path, "wb") as f:
                    f.write(audio_data)

                panel.audio_path = audio_path
                panel.audio_duration = await self._get_media_duration(audio_path)
                panel.audio_duration += PADDING_AFTER_AUDIO  # Breathing room

                project.log(
                    f"Panel {panel.panel_number} narration: "
                    f"{panel.audio_duration:.1f}s ({len(audio_data)} bytes)"
                )
                logger.info(f"Panel {panel.panel_number} narration: {panel.audio_duration:.1f}s")

            except Exception as e:
                logger.error(f"Panel {panel.panel_number} TTS failed: {e}")
                panel.audio_duration = MIN_PANEL_DURATION
                project.log(f"Panel {panel.panel_number} TTS failed: {e}")

        # Estimate TTS cost (~$0.01 per 100 chars)
        total_chars = sum(
            len(p.narration) + sum(len(d.get("text", "")) for d in p.dialogue)
            for p in project.panels
        )
        tts_cost = total_chars * 0.0001  # Rough estimate
        project.total_cost += tts_cost

        return project

    async def create_motion_comic(
        self,
        project: ComicProject,
        output_path: str,
        music_path: Optional[str] = None,
        music_volume: float = 0.15,
    ) -> str:
        """
        Create the final motion comic video.

        Flow:
        1. Create Ken Burns clip for each panel (image → video segment)
        2. Concatenate with xfade transitions
        3. Build full narration audio track
        4. Mix narration + background music
        5. Combine video + audio

        Args:
            project: ComicProject with panels (need image_path, audio_path, audio_duration)
            output_path: Final video output path
            music_path: Optional background music file
            music_volume: Background music volume (0.0-1.0)

        Returns:
            Path to final motion comic video
        """
        ffmpeg = self._find_ffmpeg()
        panels = [p for p in project.panels if p.image_path]
        if not panels:
            raise ValueError("No panels with images to create motion comic")

        work_dir = tempfile.mkdtemp(prefix="comic_motion_")
        logger.info(f"Creating motion comic: {len(panels)} panels, work_dir={work_dir}")

        try:
            # Step 1: Create Ken Burns video clip for each panel
            panel_clips = []
            for panel in panels:
                duration = max(panel.audio_duration, MIN_PANEL_DURATION)
                clip_path = os.path.join(work_dir, f"clip_{panel.panel_number:02d}.mp4")
                await self._create_ken_burns_clip(
                    image_path=panel.image_path,
                    output_path=clip_path,
                    duration=duration,
                    panel_number=panel.panel_number,
                )
                panel_clips.append((clip_path, duration))

            # Step 2: Concatenate clips with xfade transitions
            video_only_path = os.path.join(work_dir, "video_only.mp4")
            await self._concat_with_transitions(panel_clips, video_only_path)

            # Step 3: Build full narration audio track
            narration_path = os.path.join(work_dir, "narration_full.mp3")
            await self._build_narration_track(panels, narration_path, panel_clips)

            # Step 4: Combine video + narration + music
            await self._final_mix(
                video_path=video_only_path,
                narration_path=narration_path,
                output_path=output_path,
                music_path=music_path,
                music_volume=music_volume,
            )

            project.video_path = output_path
            project.log(f"Motion comic generated: {output_path}")
            logger.info(f"Motion comic complete: {output_path}")

            return output_path

        finally:
            # Clean up work directory
            import shutil
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass

    async def _create_ken_burns_clip(
        self,
        image_path: str,
        output_path: str,
        duration: float,
        panel_number: int,
    ):
        """Create a video clip from a still image with Ken Burns effect."""
        ffmpeg = self._find_ffmpeg()

        # Alternate between zoom-in and zoom-out + pan direction per panel
        if panel_number % 2 == 0:
            # Even panels: zoom in
            zoom_expr = f"{KB_ZOOM_START}+({KB_ZOOM_END}-{KB_ZOOM_START})*on/({duration}*{VIDEO_FPS})"
            x_expr = f"(iw-iw/{KB_ZOOM_END})/2"
            y_expr = f"(ih-ih/{KB_ZOOM_END})/2"
        else:
            # Odd panels: zoom out (reverse)
            zoom_expr = f"{KB_ZOOM_END}-({KB_ZOOM_END}-{KB_ZOOM_START})*on/({duration}*{VIDEO_FPS})"
            x_expr = f"(iw-iw/{KB_ZOOM_START})/2"
            y_expr = f"(ih-ih/{KB_ZOOM_START})/2"

        # zoompan filter: creates Ken Burns from still image
        filter_str = (
            f"zoompan=z='{zoom_expr}'"
            f":x='{x_expr}'"
            f":y='{y_expr}'"
            f":d={int(duration * VIDEO_FPS)}"
            f":s={VIDEO_WIDTH}x{VIDEO_HEIGHT}"
            f":fps={VIDEO_FPS}"
        )

        cmd = [
            ffmpeg, "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", filter_str,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(VIDEO_CRF),
            "-pix_fmt", "yuv420p",
            "-an",  # No audio in individual clips
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode()[-500:]
            raise RuntimeError(f"Ken Burns clip failed for panel {panel_number}: {error}")

        logger.debug(f"Ken Burns clip created: {output_path} ({duration:.1f}s)")

    async def _concat_with_transitions(
        self,
        clips: list[tuple[str, float]],
        output_path: str,
    ):
        """Concatenate video clips with xfade dissolve transitions."""
        ffmpeg = self._find_ffmpeg()

        if len(clips) == 1:
            # Single clip — just copy
            import shutil
            shutil.copy2(clips[0][0], output_path)
            return

        # Build xfade filter chain
        # For N clips: N-1 xfade operations chained together
        inputs = []
        for clip_path, _ in clips:
            inputs.extend(["-i", clip_path])

        # Build filter_complex for xfade chain
        filter_parts = []
        current_offset = 0.0

        for i in range(len(clips) - 1):
            # Calculate offset: sum of durations up to clip i, minus transition overlap
            if i == 0:
                in_label = f"[{i}:v]"
            else:
                in_label = f"[v{i}]"

            next_label = f"[{i + 1}:v]"
            out_label = f"[v{i + 1}]" if i < len(clips) - 2 else "[vout]"

            # Offset = when the transition starts (end of current clip minus transition duration)
            current_offset += clips[i][1] - TRANSITION_DURATION

            filter_parts.append(
                f"{in_label}{next_label}xfade=transition=dissolve"
                f":duration={TRANSITION_DURATION}"
                f":offset={current_offset:.3f}{out_label}"
            )

        filter_complex = ";".join(filter_parts)

        cmd = [
            ffmpeg, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", str(VIDEO_CRF),
            "-pix_fmt", "yuv420p",
            "-an",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode()[-500:]
            raise RuntimeError(f"xfade concat failed: {error}")

        logger.info(f"Video concatenated with transitions: {output_path}")

    async def _build_narration_track(
        self,
        panels: list[Panel],
        output_path: str,
        clips: list[tuple[str, float]],
    ):
        """
        Build a single narration audio track with correct timing.

        Each panel's narration is placed at the correct offset to match
        the video timing (accounting for xfade overlaps).
        """
        ffmpeg = self._find_ffmpeg()

        # Calculate panel start times (accounting for xfade overlaps)
        start_times = []
        current_time = 0.0
        for i, (_, duration) in enumerate(clips):
            start_times.append(current_time)
            current_time += duration
            if i < len(clips) - 1:
                current_time -= TRANSITION_DURATION

        total_duration = current_time

        # Build filter: place each panel's audio at its start time
        inputs = []
        filter_parts = []
        input_idx = 0
        audio_labels = []

        # First input: silence for the full duration (base track)
        inputs.extend([
            "-f", "lavfi",
            "-t", str(total_duration),
            "-i", f"anullsrc=r=44100:cl=stereo",
        ])
        input_idx += 1

        for i, panel in enumerate(panels):
            if panel.audio_path and Path(panel.audio_path).exists():
                inputs.extend(["-i", panel.audio_path])
                # Delay this audio to its panel's start time
                delay_ms = int(start_times[i] * 1000)
                label = f"[a{input_idx}]"
                filter_parts.append(
                    f"[{input_idx}:a]adelay={delay_ms}|{delay_ms}{label}"
                )
                audio_labels.append(label)
                input_idx += 1

        if not audio_labels:
            # No narration audio — just output silence
            cmd = [
                ffmpeg, "-y",
                "-f", "lavfi",
                "-t", str(total_duration),
                "-i", "anullsrc=r=44100:cl=stereo",
                "-c:a", "libmp3lame", "-q:a", "2",
                output_path,
            ]
        else:
            # Mix all delayed audio tracks together
            all_labels = "[0:a]" + "".join(audio_labels)
            mix_count = 1 + len(audio_labels)
            filter_parts.append(
                f"{all_labels}amix=inputs={mix_count}:duration=first:dropout_transition=0[aout]"
            )
            filter_complex = ";".join(filter_parts)

            cmd = [
                ffmpeg, "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[aout]",
                "-c:a", "libmp3lame", "-q:a", "2",
                output_path,
            ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode()[-500:]
            raise RuntimeError(f"Narration track assembly failed: {error}")

        logger.info(f"Narration track built: {output_path} ({total_duration:.1f}s)")

    async def _measure_volume(self, audio_path: str) -> tuple[float, float]:
        """
        Measure mean and max volume of an audio file using ffmpeg volumedetect.

        Returns:
            (mean_volume_db, max_volume_db) — both as negative floats (dB).
            e.g. (-20.5, -5.2)

        Raises:
            RuntimeError: if volumedetect output cannot be parsed.
        """
        ffmpeg = self._find_ffmpeg()

        cmd = [
            ffmpeg, "-i", audio_path,
            "-af", "volumedetect",
            "-f", "null",
            "-",  # discard output, we only need stderr stats
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        output = stderr.decode(errors="replace")

        mean_match = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", output)
        max_match = re.search(r"max_volume:\s*([-\d.]+)\s*dB", output)

        if not mean_match or not max_match:
            raise RuntimeError(
                f"Could not parse volumedetect output for {audio_path}. "
                f"stderr tail: {output[-300:]}"
            )

        mean_db = float(mean_match.group(1))
        max_db = float(max_match.group(1))
        return mean_db, max_db

    async def _auto_level_music(
        self,
        narration_path: str,
        music_path: str,
    ) -> float:
        """
        Calculate a volume multiplier for background music so that
        its peak is at least MUSIC_HEADROOM_DB below the narration mean.

        Algorithm:
            1. Measure narration mean_volume (dB) — this is our reference.
            2. Measure music max_volume (dB) — the loudest moment in the music.
            3. Target music peak = narration_mean - MUSIC_HEADROOM_DB
            4. Required adjustment (dB) = target_peak - music_max
            5. Convert dB adjustment to linear multiplier: 10^(adj/20)

        Returns:
            A linear volume multiplier (e.g. 0.08). Values >1.0 are clamped to 1.0
            (we never boost music, only attenuate).
        """
        try:
            narr_mean, narr_max = await self._measure_volume(narration_path)
            music_mean, music_max = await self._measure_volume(music_path)

            # Target: music peak should sit at (narration mean - headroom)
            target_music_peak = narr_mean - MUSIC_HEADROOM_DB
            adjustment_db = target_music_peak - music_max
            multiplier = math.pow(10.0, adjustment_db / 20.0)

            # Never boost music above unity
            multiplier = min(multiplier, 1.0)

            logger.info(
                f"Auto-level music: narration mean={narr_mean:.1f}dB, "
                f"music max={music_max:.1f}dB, "
                f"target music peak={target_music_peak:.1f}dB, "
                f"adjustment={adjustment_db:.1f}dB, "
                f"multiplier={multiplier:.4f}"
            )

            return multiplier

        except Exception as e:
            logger.warning(
                f"Auto-level failed, falling back to default: {e}"
            )
            # If measurement fails, return a safe conservative default
            return 0.10

    async def _final_mix(
        self,
        video_path: str,
        narration_path: str,
        output_path: str,
        music_path: Optional[str] = None,
        music_volume: float = 0.15,
    ):
        """Combine video + narration + optional background music."""
        ffmpeg = self._find_ffmpeg()

        cmd = [ffmpeg, "-y", "-i", video_path, "-i", narration_path]

        if music_path and Path(music_path).exists():
            cmd.extend(["-stream_loop", "-1", "-i", music_path])

            # Get video duration for music trim
            video_duration = await self._get_media_duration(video_path)

            # Auto-level: calculate ideal music volume, then cap with user param
            auto_volume = await self._auto_level_music(narration_path, music_path)
            effective_volume = min(auto_volume, music_volume)
            logger.info(
                f"Music volume: auto={auto_volume:.4f}, "
                f"cap={music_volume:.4f}, "
                f"effective={effective_volume:.4f}"
            )

            # Mix narration + music
            filter_complex = (
                f"[1:a]volume=1.0[voice];"
                f"[2:a]volume={effective_volume},atrim=duration={video_duration},"
                f"afade=type=in:duration=2,afade=type=out:start_time={video_duration - 2}:duration=2[music];"
                f"[voice][music]amix=inputs=2:duration=first[aout]"
            )

            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "0:v",
                "-map", "[aout]",
            ])
        else:
            # Just narration, no music
            cmd.extend([
                "-map", "0:v",
                "-map", "1:a",
            ])

        cmd.extend([
            "-c:v", "copy",  # Video already encoded, just copy
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path,
        ])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error = stderr.decode()[-500:]
            raise RuntimeError(f"Final mix failed: {error}")

        logger.info(f"Final motion comic: {output_path}")

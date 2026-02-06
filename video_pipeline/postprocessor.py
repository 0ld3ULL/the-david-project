"""
Video Post-Processor - FFmpeg-based video processing.

Features:
1. Fade in/out (video and audio)
2. Background music mixing
3. Silence padding for clean endings

Requires FFmpeg to be installed.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Fade settings (from FRONTMAN)
FADE_IN_DURATION = 0.5  # seconds
FADE_OUT_DURATION = 1.0  # seconds
AUDIO_FADE_OUT_DURATION = 1.0  # Audio fades with video

# Silence padding - added to audio BEFORE Hedra to prevent cutoff
SILENCE_PADDING_SECONDS = 2.0  # 2s padding: 1s clean + 1s for fade


class VideoPostProcessor:
    """FFmpeg-based video post-processor."""

    def __init__(self):
        self._ffmpeg_path: Optional[str] = None

    def _find_ffmpeg(self) -> str:
        """Find FFmpeg executable."""
        if self._ffmpeg_path:
            return self._ffmpeg_path

        # Common FFmpeg locations on Windows
        search_paths = [
            "ffmpeg",
            # Winget installation
            os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin\ffmpeg.exe"),
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            os.path.expanduser(r"~\ffmpeg\bin\ffmpeg.exe"),
            # CapCut includes FFmpeg
            os.path.expanduser(r"~\AppData\Local\CapCut\Apps\7.7.0.3143\ffmpeg.exe"),
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
        ]

        for path in search_paths:
            try:
                result = subprocess.run(
                    [path, "-version"],
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    self._ffmpeg_path = path
                    logger.info(f"Found FFmpeg at: {path}")
                    return path
            except Exception:
                continue

        raise RuntimeError(
            "FFmpeg not found. Please install FFmpeg:\n"
            "1. Download from: https://ffmpeg.org/download.html\n"
            "2. Or use winget: winget install FFmpeg\n"
            "3. Or use choco: choco install ffmpeg"
        )

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration using ffprobe."""
        ffmpeg = self._find_ffmpeg()
        # ffprobe is in the same directory as ffmpeg
        if "ffmpeg.exe" in ffmpeg:
            ffprobe = ffmpeg.replace("ffmpeg.exe", "ffprobe.exe")
        else:
            ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")

        result = subprocess.run(
            [
                ffprobe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        return float(result.stdout.strip())

    async def add_silence_to_audio(
        self,
        audio_data: bytes,
        silence_seconds: float = SILENCE_PADDING_SECONDS,
    ) -> bytes:
        """
        Add silence padding to the end of audio.
        This prevents Hedra from cutting off at the last word.

        Args:
            audio_data: Input audio bytes (MP3)
            silence_seconds: Seconds of silence to add

        Returns:
            Audio bytes with silence appended
        """
        ffmpeg = self._find_ffmpeg()

        # Write input to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(audio_data)
            input_path = f.name

        output_path = input_path.replace(".mp3", "_padded.mp3")

        try:
            # Generate silence and concatenate
            # Using anullsrc to generate silence, then concat
            cmd = [
                ffmpeg,
                "-y",
                "-i", input_path,
                "-f", "lavfi",
                "-t", str(silence_seconds),
                "-i", "anullsrc=r=44100:cl=stereo",
                "-filter_complex", "[0:a][1:a]concat=n=2:v=0:a=1[out]",
                "-map", "[out]",
                "-codec:a", "libmp3lame",
                "-q:a", "2",
                output_path,
            ]

            logger.info(f"Adding {silence_seconds}s silence padding to audio...")

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"FFmpeg silence padding failed: {stderr.decode()}")
                # Return original if padding fails
                return audio_data

            # Read padded audio
            with open(output_path, "rb") as f:
                padded_audio = f.read()

            logger.info(f"Audio padded: {len(audio_data)} -> {len(padded_audio)} bytes")
            return padded_audio

        finally:
            # Cleanup temp files
            for p in [input_path, output_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass

    async def process_video(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        fade_in: bool = True,
        fade_out: bool = True,
        music_path: Optional[str] = None,
        music_volume: float = 0.3,  # 30% volume for background
        voice_volume: float = 1.0,  # 100% voice
    ) -> str:
        """
        Post-process video with fades and optional music.

        Args:
            video_path: Input video file
            output_path: Output path (auto-generated if not provided)
            fade_in: Apply fade-in at start
            fade_out: Apply fade-out at end
            music_path: Optional background music file
            music_volume: Music volume (0.0-1.0)
            voice_volume: Voice volume (0.0-2.0)

        Returns:
            Path to processed video
        """
        ffmpeg = self._find_ffmpeg()
        duration = self._get_video_duration(video_path)

        if not output_path:
            output_path = video_path.replace(".mp4", "_processed.mp4")

        logger.info(f"Post-processing video: {video_path}")
        logger.info(f"Duration: {duration:.1f}s, fade_in={fade_in}, fade_out={fade_out}")

        # Build filter complex
        video_filters = []
        audio_filters = []

        # Video fades
        if fade_in:
            video_filters.append(f"fade=type=in:duration={FADE_IN_DURATION}")
        if fade_out:
            fade_start = max(0, duration - FADE_OUT_DURATION)
            video_filters.append(f"fade=type=out:start_time={fade_start:.2f}:duration={FADE_OUT_DURATION}")

        # Audio fades
        if fade_in:
            audio_filters.append(f"afade=type=in:duration={FADE_IN_DURATION}")
        if fade_out:
            fade_start = max(0, duration - AUDIO_FADE_OUT_DURATION)
            audio_filters.append(f"afade=type=out:start_time={fade_start:.2f}:duration={AUDIO_FADE_OUT_DURATION}")

        # Build command
        cmd = [ffmpeg, "-y", "-i", video_path]

        filter_complex_parts = []

        if music_path and os.path.exists(music_path):
            # Add music input
            cmd.extend(["-stream_loop", "-1", "-i", music_path])

            # Build complex filter for mixing
            # [0:v] = video, [0:a] = voice, [1:a] = music
            vf = ",".join(video_filters) if video_filters else "null"
            filter_complex_parts.append(f"[0:v]{vf}[vout]")

            # Voice audio processing
            voice_af = f"volume={voice_volume}"
            if audio_filters:
                voice_af += "," + ",".join(audio_filters)
            filter_complex_parts.append(f"[0:a]{voice_af}[voice]")

            # Music processing (loop, trim to video length, set volume)
            filter_complex_parts.append(f"[1:a]volume={music_volume},atrim=duration={duration}[music]")

            # Mix voice and music
            filter_complex_parts.append("[voice][music]amix=inputs=2:duration=first[aout]")

            cmd.extend([
                "-filter_complex", ";".join(filter_complex_parts),
                "-map", "[vout]",
                "-map", "[aout]",
            ])
        else:
            # No music - simple processing
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            if audio_filters:
                af = f"volume={voice_volume}," + ",".join(audio_filters)
                cmd.extend(["-af", af])

        # Output settings
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            output_path,
        ])

        logger.info(f"Running FFmpeg: {' '.join(cmd[:10])}...")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode()[-500:] if stderr else "Unknown error"
            raise RuntimeError(f"FFmpeg processing failed: {error_msg}")

        logger.info(f"Video processed: {output_path}")
        return output_path


# Convenience function for quick processing
async def add_fades_and_music(
    video_path: str,
    output_path: Optional[str] = None,
    music_path: Optional[str] = None,
    music_volume: float = 0.3,
) -> str:
    """Quick function to add fades and optional music to a video."""
    processor = VideoPostProcessor()
    return await processor.process_video(
        video_path=video_path,
        output_path=output_path,
        music_path=music_path,
        music_volume=music_volume,
    )

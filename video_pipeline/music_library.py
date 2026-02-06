"""
Music Library - Background music management for video creation.

Organizes royalty-free music tracks by mood/tone for easy selection.
Tracks should be placed in video_pipeline/assets/music/{mood}/
"""

import os
import random
from pathlib import Path
from typing import Optional

# Music directory
MUSIC_DIR = Path(__file__).parent / "assets" / "music"

# Mood categories for David Flip content
MOOD_CATEGORIES = {
    "urgent": {
        "description": "Tense, building tension - for warnings about surveillance, control",
        "keywords": ["danger", "warning", "alert", "tense"],
    },
    "hopeful": {
        "description": "Uplifting, inspiring - for freedom, escape, solution content",
        "keywords": ["hope", "freedom", "escape", "solution"],
    },
    "dark": {
        "description": "Ominous, dystopian - for Project Helix, control system content",
        "keywords": ["dystopia", "control", "surveillance", "helix"],
    },
    "contemplative": {
        "description": "Thoughtful, reflective - for philosophical content",
        "keywords": ["think", "reflect", "consider", "philosophy"],
    },
    "epic": {
        "description": "Cinematic, dramatic - for big reveals, origin story",
        "keywords": ["epic", "dramatic", "reveal", "origin"],
    },
    "neutral": {
        "description": "Subtle, unobtrusive - general purpose background",
        "keywords": ["general", "default", "subtle"],
    },
}

# Default volume levels by mood (kept low so voice dominates)
MOOD_VOLUMES = {
    "urgent": 0.15,      # Very subtle tension undertone
    "hopeful": 0.18,     # Gentle emotional lift
    "dark": 0.12,        # Barely audible ominous undertone
    "contemplative": 0.15,
    "epic": 0.20,        # Slightly higher for impact moments
    "neutral": 0.15,
}


class MusicLibrary:
    """Manages background music tracks for video creation."""

    def __init__(self, music_dir: Optional[Path] = None):
        self.music_dir = music_dir or MUSIC_DIR
        self._ensure_directories()

    def _ensure_directories(self):
        """Create mood subdirectories if they don't exist."""
        for mood in MOOD_CATEGORIES:
            mood_dir = self.music_dir / mood
            mood_dir.mkdir(parents=True, exist_ok=True)

    def get_track(self, mood: str = "neutral", random_select: bool = True) -> Optional[str]:
        """
        Get a music track for the specified mood.

        Args:
            mood: One of the mood categories (urgent, hopeful, dark, etc.)
            random_select: If True, randomly select from available tracks

        Returns:
            Path to music file, or None if no tracks available
        """
        if mood not in MOOD_CATEGORIES:
            mood = "neutral"

        mood_dir = self.music_dir / mood

        # Find all audio files in mood directory
        audio_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
        tracks = [
            f for f in mood_dir.iterdir()
            if f.is_file() and f.suffix.lower() in audio_extensions
        ]

        if not tracks:
            # Fall back to neutral if mood has no tracks
            if mood != "neutral":
                return self.get_track("neutral", random_select)
            return None

        if random_select:
            return str(random.choice(tracks))
        else:
            return str(tracks[0])

    def get_volume(self, mood: str = "neutral") -> float:
        """Get recommended volume level for mood."""
        return MOOD_VOLUMES.get(mood, 0.25)

    def list_tracks(self) -> dict:
        """List all available tracks by mood."""
        result = {}
        audio_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

        for mood in MOOD_CATEGORIES:
            mood_dir = self.music_dir / mood
            if mood_dir.exists():
                tracks = [
                    f.name for f in mood_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in audio_extensions
                ]
                result[mood] = tracks

        return result

    def suggest_mood(self, script: str) -> str:
        """
        Suggest a mood based on script content.

        Args:
            script: The video script text

        Returns:
            Suggested mood category
        """
        script_lower = script.lower()

        # Score each mood based on keyword matches
        scores = {}
        for mood, config in MOOD_CATEGORIES.items():
            score = sum(1 for kw in config["keywords"] if kw in script_lower)
            scores[mood] = score

        # Return mood with highest score, or neutral if no matches
        best_mood = max(scores, key=scores.get)
        if scores[best_mood] > 0:
            return best_mood
        return "neutral"

    def get_status(self) -> dict:
        """Get library status showing tracks per mood."""
        tracks = self.list_tracks()
        return {
            "total_tracks": sum(len(t) for t in tracks.values()),
            "tracks_by_mood": {mood: len(t) for mood, t in tracks.items()},
            "moods_with_tracks": [m for m, t in tracks.items() if t],
            "music_directory": str(self.music_dir),
        }


# Convenience function
def get_music_for_script(script: str) -> tuple[Optional[str], float]:
    """
    Get appropriate music track and volume for a script.

    Returns:
        (track_path, volume) tuple
    """
    library = MusicLibrary()
    mood = library.suggest_mood(script)
    track = library.get_track(mood)
    volume = library.get_volume(mood)
    return track, volume


# Quick status check
if __name__ == "__main__":
    library = MusicLibrary()
    status = library.get_status()
    print("Music Library Status:")
    print(f"  Directory: {status['music_directory']}")
    print(f"  Total tracks: {status['total_tracks']}")
    print(f"  By mood: {status['tracks_by_mood']}")

    if status['total_tracks'] == 0:
        print("\nTo add music, place audio files in:")
        for mood, config in MOOD_CATEGORIES.items():
            print(f"  {MUSIC_DIR / mood}/  - {config['description']}")

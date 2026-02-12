"""
Comic Pipeline — Data models.

Dataclasses for the full comic generation pipeline:
Panel → ComicPage → ComicProject.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PanelType(Enum):
    WIDE = "wide"            # Full-width panel (establishing shots)
    STANDARD = "standard"    # Normal grid panel
    TALL = "tall"            # Vertical emphasis panel
    SPLASH = "splash"        # Full-page dramatic panel


class CameraHint(Enum):
    WIDE_SHOT = "wide_shot"           # Establishes location
    MEDIUM_SHOT = "medium_shot"       # Character interaction
    CLOSE_UP = "close_up"             # Emotion, detail
    EXTREME_CLOSE_UP = "extreme_close_up"  # Eyes, hands, objects
    BIRDS_EYE = "birds_eye"           # Overhead view
    LOW_ANGLE = "low_angle"           # Power, menace
    OVER_SHOULDER = "over_shoulder"   # Conversation framing


@dataclass
class Panel:
    """A single comic panel."""
    panel_number: int
    image_prompt: str          # Detailed prompt for Flux Kontext
    dialogue: list[dict] = field(default_factory=list)
    # Each dict: {"speaker": "name", "text": "...", "style": "normal|whisper|shout|thought"}
    narration: str = ""        # Caption box text (David's narration voice)
    camera: CameraHint = CameraHint.MEDIUM_SHOT
    panel_type: PanelType = PanelType.STANDARD
    mood: str = "contemplative"  # For music/pacing hints
    image_path: Optional[str] = None      # Filled after generation
    audio_path: Optional[str] = None      # Filled after TTS narration
    audio_duration: float = 0.0           # Seconds, set after TTS
    assembled_path: Optional[str] = None  # Panel with bubbles/captions


@dataclass
class ComicPage:
    """A page of assembled panels (2x2 grid default)."""
    page_number: int
    panels: list[Panel] = field(default_factory=list)
    image_path: Optional[str] = None  # Assembled page image


@dataclass
class ComicProject:
    """Full comic project — one parable, all outputs."""
    title: str
    theme_id: str                         # Links to david_flip.py theme
    synopsis: str = ""
    art_style: str = (
        "Watercolor and ink outlines, warm earth tones, "
        "Studio Ghibli meets indie graphic novel. "
        "Handcrafted feel, expressive characters, "
        "soft lighting with dramatic shadows for tension."
    )
    panels: list[Panel] = field(default_factory=list)
    pages: list[ComicPage] = field(default_factory=list)

    # Output paths (filled during generation)
    output_dir: str = ""
    pdf_path: Optional[str] = None
    video_path: Optional[str] = None
    panel_exports: list[str] = field(default_factory=list)  # Individual panels for social/NFT

    # Metadata
    total_cost: float = 0.0
    generation_log: list[str] = field(default_factory=list)

    def log(self, message: str):
        """Append to generation log."""
        self.generation_log.append(message)

    @property
    def panel_count(self) -> int:
        return len(self.panels)

    def to_dict(self) -> dict:
        """Serialize for approval queue / JSON storage."""
        return {
            "title": self.title,
            "theme_id": self.theme_id,
            "synopsis": self.synopsis,
            "panel_count": self.panel_count,
            "output_dir": self.output_dir,
            "pdf_path": self.pdf_path,
            "video_path": self.video_path,
            "panel_exports": self.panel_exports,
            "total_cost": self.total_cost,
            "panels": [
                {
                    "panel_number": p.panel_number,
                    "narration": p.narration,
                    "dialogue": p.dialogue,
                    "image_path": p.image_path,
                    "audio_path": p.audio_path,
                    "audio_duration": p.audio_duration,
                }
                for p in self.panels
            ],
        }

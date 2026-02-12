"""
Comic Pipeline — Data models.

Dataclasses for the full comic generation pipeline:
Panel → ComicPage → ComicProject.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# ============================================================
# Art Styles — David's visual identities
# ============================================================

class ArtStyle(Enum):
    """Available art styles for comic/video generation."""

    SCRATCH = "scratch"      # Parables — timeless, dark, atmospheric
    GRAFFITI = "graffiti"    # Non-parables — urgent, modern, street energy


ART_STYLES = {
    ArtStyle.SCRATCH: {
        "name": "Scratch Art / Woodcut",
        "use": "Parables (village metaphors, timeless stories)",
        "prompt": (
            "Scratch art illustration style, traditional woodcut engraving aesthetic, "
            "high-contrast black background with etched white and warm sepia linework, "
            "fine scratch lines revealing light from darkness, dense cross-hatching, "
            "hand-carved linocut appearance, dramatic chiaroscuro lighting, "
            "moody and atmospheric, vintage printmaking style, "
            "subtle distressed paper texture, limited color palette (black, ivory, warm sepia), "
            "bold carved outlines, detailed but graphic composition, "
            "cinematic framing, strong silhouettes, "
            "no modern elements, no smooth gradients, no digital painting look, "
            "no soft airbrush shading."
        ),
        "negative": (
            "no watercolor, no flat vector style, no 3D render, no CGI, no anime, "
            "no glossy lighting, no photorealism, no smooth digital shading, "
            "no bright saturated colors, no modern clothing, no blur, "
            "no soft focus, no lens flare."
        ),
        "accent": (
            "Muted metallic gold accent used sparingly on the system's gift object ONLY, "
            "glowing subtly against the dark engraved background, "
            "still rendered in scratch-line texture (not smooth or glossy)."
        ),
    },
    ArtStyle.GRAFFITI: {
        "name": "Graffiti / Street Mural",
        "use": "Non-parables (commentary, opinion, quick takes, modern topics)",
        "prompt": (
            "Graffiti street art mural style, bold spray paint textures, layered stencils, "
            "thick black outlines, vibrant high-contrast colors, rough concrete wall background, "
            "visible paint drips and splatters, expressive brush strokes, urban mural aesthetic, "
            "large graphic shapes, slightly exaggerated proportions, strong silhouettes, "
            "dynamic composition, gritty texture, raw street energy, poster-like impact, "
            "high saturation but slightly weathered finish, stencil layering effect, "
            "hand-painted typography space (leave top area clean for optional text). "
            "Lighting natural but bold, shadows simplified, background slightly distressed "
            "with cracked wall texture and overspray edges. Characters rendered in bold shapes "
            "rather than fine detail. Emphasis on contrast and immediacy."
        ),
        "negative": (
            "no watercolor, no digital painting look, no CGI, no photoreal rendering, "
            "no anime, no exaggerated cartoon proportions, no text bubbles, no captions, "
            "no logos, no blurry faces, no extra fingers, no warped hands."
        ),
        "accent": "",
    },
}


def get_art_style(style: ArtStyle = ArtStyle.SCRATCH) -> dict:
    """Get art style config by enum."""
    return ART_STYLES[style]


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
    art_style_key: str = "scratch"  # "scratch" for parables, "graffiti" for non-parables
    art_style: str = ART_STYLES[ArtStyle.SCRATCH]["prompt"]
    art_style_negative: str = ART_STYLES[ArtStyle.SCRATCH]["negative"]
    art_style_accent: str = ART_STYLES[ArtStyle.SCRATCH]["accent"]
    parable_text: str = ""  # Full prose parable (250-400 words)
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

    def format_for_review(self) -> str:
        """Format the script for human review/approval before image generation."""
        lines = [
            f"STORY: {self.title}",
            f"{'=' * 50}",
            "",
        ]
        if self.synopsis:
            lines.append(f"Synopsis: {self.synopsis}")
            lines.append("")
        if self.parable_text:
            lines.append("FULL TEXT:")
            lines.append(self.parable_text)
            lines.append("")
        lines.append(f"PANELS ({len(self.panels)}):")
        lines.append("-" * 40)
        for p in self.panels:
            lines.append(f"Panel {p.panel_number} [{p.camera.value}]:")
            if p.narration:
                lines.append(f"  Narration: {p.narration}")
            for d in p.dialogue:
                lines.append(f"  {d['speaker']}: \"{d['text']}\"")
            lines.append(f"  Image: {p.image_prompt[:120]}...")
            lines.append("")
        lines.append(f"Art style: {self.art_style_key}")
        lines.append(f"Estimated cost: ~${len(self.panels) * 0.04 + 0.10:.2f}")
        return "\n".join(lines)

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

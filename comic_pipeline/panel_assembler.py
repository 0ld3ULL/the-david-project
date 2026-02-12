"""
Comic Pipeline — Panel Assembler.

Assembles generated panel images into comic book pages:
- Speech bubbles with tails
- Narration caption boxes
- Panel borders and gutters
- Multi-page PDF output
- Individual panel exports with captions (for social/NFT)

Uses Pillow for all image manipulation.
"""

import logging
import math
import os
import textwrap
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from comic_pipeline.models import ComicPage, ComicProject, Panel

logger = logging.getLogger(__name__)

# Layout constants
PAGE_WIDTH = 2480       # A4 at 300 DPI (portrait)
PAGE_HEIGHT = 3508
PANEL_GUTTER = 40       # Space between panels
PAGE_MARGIN = 80        # Page edge margin
BORDER_WIDTH = 4        # Panel border thickness
BORDER_COLOR = (30, 30, 30)
BACKGROUND_COLOR = (245, 240, 230)  # Warm off-white (parchment feel)

# Speech bubble styling
BUBBLE_FILL = (255, 255, 255, 230)
BUBBLE_OUTLINE = (30, 30, 30)
BUBBLE_OUTLINE_WIDTH = 3
BUBBLE_PADDING = 16
BUBBLE_RADIUS = 20
BUBBLE_TAIL_SIZE = 20

# Caption box styling (David's narration)
CAPTION_FILL = (40, 35, 30, 220)
CAPTION_TEXT_COLOR = (245, 240, 230)
CAPTION_PADDING = 12

# Font paths — look for bundled fonts, fall back to system defaults
FONTS_DIR = Path(__file__).parent / "assets" / "fonts"

# Social panel export
SOCIAL_WIDTH = 1080
SOCIAL_HEIGHT = 1080


class PanelAssembler:
    """Assembles comic panels into pages and exports."""

    def __init__(self):
        self._bubble_font: Optional[ImageFont.FreeTypeFont] = None
        self._caption_font: Optional[ImageFont.FreeTypeFont] = None
        self._narration_font: Optional[ImageFont.FreeTypeFont] = None

    def _load_font(self, preferred_name: str, size: int) -> ImageFont.FreeTypeFont:
        """Load a font, trying bundled → system → default."""
        # Try bundled fonts first
        for ext in (".ttf", ".otf"):
            bundled = FONTS_DIR / f"{preferred_name}{ext}"
            if bundled.exists():
                return ImageFont.truetype(str(bundled), size)

        # Try common system font paths
        system_fonts = {
            "Bangers": [
                "Bangers-Regular.ttf",
                "Bangers.ttf",
            ],
            "PatrickHand": [
                "PatrickHand-Regular.ttf",
                "PatrickHand.ttf",
            ],
        }

        # Windows font directories
        font_dirs = [
            Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts",
            Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
            Path("/usr/share/fonts"),
            Path("/usr/share/fonts/truetype"),
            Path.home() / ".local" / "share" / "fonts",
        ]

        for font_name in system_fonts.get(preferred_name, [preferred_name + ".ttf"]):
            for font_dir in font_dirs:
                font_path = font_dir / font_name
                if font_path.exists():
                    return ImageFont.truetype(str(font_path), size)

        # Fallback: use Pillow's default (ugly but functional)
        logger.warning(f"Font '{preferred_name}' not found — using default. "
                       f"Place .ttf files in {FONTS_DIR} for better results.")
        try:
            # Try Arial as universal fallback
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default()

    @property
    def bubble_font(self) -> ImageFont.FreeTypeFont:
        if self._bubble_font is None:
            self._bubble_font = self._load_font("Bangers", 28)
        return self._bubble_font

    @property
    def caption_font(self) -> ImageFont.FreeTypeFont:
        if self._caption_font is None:
            self._caption_font = self._load_font("PatrickHand", 24)
        return self._caption_font

    @property
    def narration_font(self) -> ImageFont.FreeTypeFont:
        if self._narration_font is None:
            self._narration_font = self._load_font("PatrickHand", 22)
        return self._narration_font

    def assemble_pages(
        self,
        project: ComicProject,
        output_dir: str,
        panels_per_page: int = 4,
        grid_cols: int = 2,
    ) -> ComicProject:
        """
        Assemble panels into comic book pages.

        Args:
            project: ComicProject with generated panel images
            output_dir: Directory for output files
            panels_per_page: Panels per page (default 4 for 2x2 grid)
            grid_cols: Columns in grid layout

        Returns:
            Updated ComicProject with pages and assembled_path set
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Filter panels that have images
        panels_with_images = [p for p in project.panels if p.image_path]
        if not panels_with_images:
            logger.warning("No panels have images — skipping assembly")
            return project

        # Group panels into pages
        page_groups = []
        for i in range(0, len(panels_with_images), panels_per_page):
            page_groups.append(panels_with_images[i:i + panels_per_page])

        # Assemble each page
        project.pages = []
        for page_num, page_panels in enumerate(page_groups, 1):
            page = ComicPage(page_number=page_num, panels=page_panels)
            page_path = str(Path(output_dir) / f"page_{page_num:02d}.png")

            self._render_page(page_panels, page_path, grid_cols)
            page.image_path = page_path
            project.pages.append(page)
            project.log(f"Page {page_num} assembled: {page_path}")
            logger.info(f"Page {page_num}/{len(page_groups)} assembled: {page_path}")

        return project

    def _render_page(
        self,
        panels: list[Panel],
        output_path: str,
        grid_cols: int = 2,
    ):
        """Render a single comic book page."""
        page = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), BACKGROUND_COLOR)
        draw = ImageDraw.Draw(page)

        grid_rows = math.ceil(len(panels) / grid_cols)

        # Calculate panel dimensions
        available_w = PAGE_WIDTH - 2 * PAGE_MARGIN - (grid_cols - 1) * PANEL_GUTTER
        available_h = PAGE_HEIGHT - 2 * PAGE_MARGIN - (grid_rows - 1) * PANEL_GUTTER
        panel_w = available_w // grid_cols
        panel_h = available_h // grid_rows

        for i, panel in enumerate(panels):
            col = i % grid_cols
            row = i // grid_cols

            x = PAGE_MARGIN + col * (panel_w + PANEL_GUTTER)
            y = PAGE_MARGIN + row * (panel_h + PANEL_GUTTER)

            # Draw panel border
            draw.rectangle(
                [x - BORDER_WIDTH, y - BORDER_WIDTH,
                 x + panel_w + BORDER_WIDTH, y + panel_h + BORDER_WIDTH],
                fill=BORDER_COLOR,
            )

            # Load and resize panel image
            if panel.image_path and Path(panel.image_path).exists():
                panel_img = Image.open(panel.image_path)
                panel_img = self._fit_image(panel_img, panel_w, panel_h)
                page.paste(panel_img, (x, y))
            else:
                # Placeholder for missing images
                draw.rectangle([x, y, x + panel_w, y + panel_h], fill=(200, 195, 185))
                draw.text(
                    (x + panel_w // 2, y + panel_h // 2),
                    f"Panel {panel.panel_number}",
                    fill=(100, 95, 85),
                    font=self.bubble_font,
                    anchor="mm",
                )

            # Draw speech bubbles
            bubble_y_offset = y + BUBBLE_PADDING
            for dialogue in panel.dialogue:
                text = dialogue.get("text", "")
                style = dialogue.get("style", "normal")
                if text:
                    bubble_y_offset = self._draw_speech_bubble(
                        draw, page, text, style,
                        x + BUBBLE_PADDING,
                        bubble_y_offset,
                        max_width=panel_w - 2 * BUBBLE_PADDING,
                    )

            # Draw narration caption box (bottom of panel)
            if panel.narration:
                self._draw_caption_box(
                    draw, panel.narration,
                    x, y + panel_h - 80,
                    width=panel_w,
                )

        page.save(output_path, quality=95)

    def _fit_image(self, img: Image.Image, target_w: int, target_h: int) -> Image.Image:
        """Resize and crop image to fit target dimensions (cover mode)."""
        # Calculate scale to cover the target
        scale_w = target_w / img.width
        scale_h = target_h / img.height
        scale = max(scale_w, scale_h)

        new_w = int(img.width * scale)
        new_h = int(img.height * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Center crop
        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        img = img.crop((left, top, left + target_w, top + target_h))
        return img

    def _draw_speech_bubble(
        self,
        draw: ImageDraw.ImageDraw,
        page: Image.Image,
        text: str,
        style: str,
        x: int,
        y: int,
        max_width: int,
    ) -> int:
        """
        Draw a speech bubble with text. Returns y position after bubble.

        style: normal, whisper, shout, thought
        """
        # Wrap text
        wrapped = textwrap.fill(text, width=max_width // 14)  # Rough chars per line
        font = self.bubble_font

        # Measure text
        bbox = draw.textbbox((0, 0), wrapped, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Bubble dimensions
        bw = text_w + 2 * BUBBLE_PADDING
        bh = text_h + 2 * BUBBLE_PADDING

        # Clamp to panel width
        if bw > max_width:
            bw = max_width
            # Re-wrap for narrower width
            wrapped = textwrap.fill(text, width=(bw - 2 * BUBBLE_PADDING) // 14)
            bbox = draw.textbbox((0, 0), wrapped, font=font)
            text_h = bbox[3] - bbox[1]
            bh = text_h + 2 * BUBBLE_PADDING

        # Draw bubble on overlay for transparency
        overlay = Image.new("RGBA", page.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        # Bubble shape varies by style
        outline = BUBBLE_OUTLINE
        fill = BUBBLE_FILL
        outline_width = BUBBLE_OUTLINE_WIDTH

        if style == "shout":
            outline_width = 5
        elif style == "whisper":
            outline = (150, 150, 150)
        elif style == "thought":
            # Thought bubbles use dashed appearance (approximate with lighter outline)
            outline = (120, 120, 120)

        # Draw rounded rectangle
        overlay_draw.rounded_rectangle(
            [x, y, x + bw, y + bh],
            radius=BUBBLE_RADIUS,
            fill=fill,
            outline=outline,
            width=outline_width,
        )

        # Draw tail (triangle pointing down-left)
        tail_x = x + bw // 4
        tail_y = y + bh
        overlay_draw.polygon(
            [
                (tail_x, tail_y - 2),
                (tail_x + BUBBLE_TAIL_SIZE, tail_y - 2),
                (tail_x - 5, tail_y + BUBBLE_TAIL_SIZE),
            ],
            fill=BUBBLE_FILL,
            outline=outline,
            width=outline_width,
        )
        # Cover the tail-bubble seam
        overlay_draw.rectangle(
            [tail_x - 1, tail_y - outline_width - 1,
             tail_x + BUBBLE_TAIL_SIZE + 1, tail_y + 1],
            fill=BUBBLE_FILL,
        )

        # Composite overlay onto page
        page.paste(Image.alpha_composite(
            page.convert("RGBA"), overlay
        ).convert("RGB"), (0, 0))

        # Draw text
        # Re-get draw since page was modified
        draw = ImageDraw.Draw(page)
        text_color = (30, 30, 30)
        if style == "whisper":
            text_color = (100, 100, 100)

        draw.text(
            (x + BUBBLE_PADDING, y + BUBBLE_PADDING),
            wrapped,
            fill=text_color,
            font=font,
        )

        return y + bh + BUBBLE_TAIL_SIZE + 8

    def _draw_caption_box(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        width: int,
    ):
        """Draw a narration caption box (David's voice)."""
        wrapped = textwrap.fill(text, width=width // 12)
        font = self.caption_font

        bbox = draw.textbbox((0, 0), wrapped, font=font)
        text_h = bbox[3] - bbox[1]
        box_h = text_h + 2 * CAPTION_PADDING

        # Semi-transparent dark box
        draw.rectangle(
            [x, y, x + width, y + box_h],
            fill=(40, 35, 30),
        )

        # Narration text
        draw.text(
            (x + CAPTION_PADDING, y + CAPTION_PADDING),
            wrapped,
            fill=CAPTION_TEXT_COLOR,
            font=self.caption_font,
        )

    def generate_pdf(
        self,
        project: ComicProject,
        output_path: str,
    ) -> str:
        """
        Generate a multi-page PDF from assembled pages.

        Args:
            project: ComicProject with assembled pages
            output_path: Output PDF path

        Returns:
            Path to generated PDF
        """
        pages_with_images = [p for p in project.pages if p.image_path]
        if not pages_with_images:
            raise ValueError("No assembled pages to create PDF from")

        # Load all page images
        images = []
        for page in pages_with_images:
            img = Image.open(page.image_path).convert("RGB")
            images.append(img)

        # Save as multi-page PDF
        first_image = images[0]
        if len(images) > 1:
            first_image.save(
                output_path,
                save_all=True,
                append_images=images[1:],
                resolution=300,
            )
        else:
            first_image.save(output_path, resolution=300)

        project.pdf_path = output_path
        project.log(f"PDF generated: {output_path} ({len(images)} pages)")
        logger.info(f"PDF generated: {output_path}")

        return output_path

    def export_social_panels(
        self,
        project: ComicProject,
        output_dir: str,
    ) -> list[str]:
        """
        Export individual panels with captions for social media / NFT.

        Each panel gets a clean 1080x1080 export with:
        - The panel image (cropped to square)
        - Narration text at the bottom
        - David Flip branding

        Returns:
            List of exported file paths
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        exports = []

        for panel in project.panels:
            if not panel.image_path or not Path(panel.image_path).exists():
                continue

            output_path = str(Path(output_dir) / f"social_panel_{panel.panel_number:02d}.png")

            # Create square canvas
            canvas = Image.new("RGB", (SOCIAL_WIDTH, SOCIAL_HEIGHT), BACKGROUND_COLOR)
            draw = ImageDraw.Draw(canvas)

            # Load and fit panel image
            panel_img = Image.open(panel.image_path)
            if panel.narration:
                # Leave room for caption at bottom
                img_height = SOCIAL_HEIGHT - 120
            else:
                img_height = SOCIAL_HEIGHT

            fitted = self._fit_image(panel_img, SOCIAL_WIDTH, img_height)
            canvas.paste(fitted, (0, 0))

            # Add narration caption at bottom
            if panel.narration:
                self._draw_caption_box(
                    draw, panel.narration,
                    x=0, y=SOCIAL_HEIGHT - 120,
                    width=SOCIAL_WIDTH,
                )

            canvas.save(output_path, quality=95)
            exports.append(output_path)

        project.panel_exports = exports
        project.log(f"Social panels exported: {len(exports)} files")
        logger.info(f"Exported {len(exports)} social panels to {output_dir}")

        return exports

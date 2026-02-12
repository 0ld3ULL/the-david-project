"""
Comic Pipeline — Leonardo Image Generator.

Generates comic panel images using Leonardo.ai API.
Text-to-image only (no reference chaining) — each panel is generated
independently from its prompt for maximum scene variety.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

import httpx

from comic_pipeline.models import ComicProject, Panel

logger = logging.getLogger(__name__)

LEONARDO_BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"

# Cost per image (Leonardo)
COST_PER_IMAGE = 0.02  # Rough estimate — varies by model

# Default image dimensions (square for comic panels)
PANEL_WIDTH = 1024
PANEL_HEIGHT = 1024


class LeonardoImageGenerator:
    """Generates comic panel images via Leonardo.ai."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LEONARDO_API_KEY", "")
        if not self.api_key:
            logger.warning("LEONARDO_API_KEY not set — image generation will fail")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def close(self):
        """No persistent client to close."""
        pass

    async def generate_panels(
        self,
        project: ComicProject,
        output_dir: str,
        reference_image_url: Optional[str] = None,
    ) -> ComicProject:
        """
        Generate images for all panels in a project.

        Each panel is generated independently via text-to-image.
        No reference chaining — scene variety is prioritised over
        character consistency. The detailed prompts handle consistency.

        Args:
            project: ComicProject with panels that have image_prompts
            output_dir: Directory to save generated images
            reference_image_url: Ignored (kept for API compatibility)

        Returns:
            Updated ComicProject with image_path set on each panel
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        for i, panel in enumerate(project.panels):
            logger.info(
                f"Generating panel {panel.panel_number}/{len(project.panels)}: "
                f"{panel.image_prompt[:60]}..."
            )

            output_path = str(
                Path(output_dir) / f"panel_{panel.panel_number:02d}.png"
            )

            # Build the full prompt with negative prompt
            full_prompt = panel.image_prompt
            negative = project.art_style_negative or ""

            try:
                image_url = await self._generate_single(
                    prompt=full_prompt,
                    negative_prompt=negative,
                    output_path=output_path,
                )
                panel.image_path = output_path
                project.total_cost += COST_PER_IMAGE
                project.log(
                    f"Panel {panel.panel_number} image generated: {output_path}"
                )

            except Exception as e:
                logger.error(f"Panel {panel.panel_number} generation failed: {e}")
                project.log(f"Panel {panel.panel_number} FAILED: {e}")

        return project

    async def _generate_single(
        self,
        prompt: str,
        negative_prompt: str = "",
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate a single image via Leonardo.ai.

        Submit → poll → download.

        Returns:
            URL of the generated image.
        """
        async with httpx.AsyncClient(timeout=300) as client:
            # Submit generation
            payload = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": PANEL_WIDTH,
                "height": PANEL_HEIGHT,
                "modelId": "6b645e3a-d64f-4341-a6d8-7a3690fbf042",  # Leonardo Phoenix
                "num_images": 1,
                "presetStyle": "NONE",  # Let our prompt control the style entirely
                "public": False,
                "alchemy": True,  # Better quality
            }

            response = await client.post(
                f"{LEONARDO_BASE_URL}/generations",
                headers=self._headers(),
                json=payload,
            )

            if not response.is_success:
                raise RuntimeError(
                    f"Leonardo submit failed ({response.status_code}): "
                    f"{response.text[:500]}"
                )

            data = response.json()
            generation_id = data["sdGenerationJob"]["generationId"]
            logger.info(f"Leonardo generation started: {generation_id}")

            # Poll for completion
            image_url = await self._poll_result(client, generation_id)

            # Download and save
            if output_path:
                await self._download_image(client, image_url, output_path)

            return image_url

    async def _poll_result(
        self,
        client: httpx.AsyncClient,
        generation_id: str,
        max_wait: int = 300,
    ) -> str:
        """Poll Leonardo for generation result."""
        elapsed = 0
        interval = 5

        while elapsed < max_wait:
            await asyncio.sleep(interval)
            elapsed += interval

            response = await client.get(
                f"{LEONARDO_BASE_URL}/generations/{generation_id}",
                headers=self._headers(),
            )

            if not response.is_success:
                logger.warning(
                    f"Leonardo poll failed: {response.status_code}"
                )
                continue

            gen_data = response.json()
            gen_info = gen_data.get("generations_by_pk", {})
            status = gen_info.get("status", "")

            if status == "COMPLETE":
                images = gen_info.get("generated_images", [])
                if not images:
                    raise RuntimeError("Leonardo returned no images")
                url = images[0].get("url", "")
                if not url:
                    raise RuntimeError("Leonardo image has no URL")
                logger.info(f"Leonardo generation complete ({elapsed}s)")
                return url

            elif status == "FAILED":
                raise RuntimeError("Leonardo generation failed")

            logger.info(f"Leonardo status: {status} ({elapsed}s)")

        raise RuntimeError(f"Leonardo timed out after {max_wait}s")

    async def _download_image(
        self, client: httpx.AsyncClient, url: str, output_path: str
    ):
        """Download image to local file."""
        response = await client.get(url)
        if not response.is_success:
            raise RuntimeError(
                f"Image download failed ({response.status_code})"
            )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)

        logger.info(
            f"Image saved: {output_path} ({len(response.content)} bytes)"
        )

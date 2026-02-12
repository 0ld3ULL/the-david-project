"""
Comic Pipeline — Image Generator.

Generates comic panel images using Flux Kontext Pro via fal.ai REST API.
Uses queue-based async flow: submit → poll → fetch.

Sequential generation: Panel 1's output is used as character reference
for Panel 2+, maintaining visual consistency across panels.
"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from comic_pipeline.models import ComicProject, Panel

logger = logging.getLogger(__name__)

FAL_API_BASE = "https://queue.fal.run"
FLUX_KONTEXT_IMG2IMG = "fal-ai/flux-pro/kontext"
FLUX_KONTEXT_TXT2IMG = "fal-ai/flux-pro/kontext/text-to-image"

# Cost per image (Flux Kontext Pro via fal.ai)
COST_PER_IMAGE = 0.04

# Default image dimensions for comic panels
PANEL_WIDTH = 1024
PANEL_HEIGHT = 1024


class FluxImageGenerator:
    """Generates comic panel images via Flux Kontext Pro on fal.ai."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("FAL_API_KEY", "")
        if not self.api_key:
            logger.warning("FAL_API_KEY not set — image generation will fail")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(300.0, connect=30.0),
                headers={
                    "Authorization": f"Key {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def generate_panels(
        self,
        project: ComicProject,
        output_dir: str,
        reference_image_url: Optional[str] = None,
    ) -> ComicProject:
        """
        Generate images for all panels in a project.

        Sequential generation: each panel uses the previous panel's image
        as a character reference for Flux Kontext, maintaining consistency.

        Args:
            project: ComicProject with panels that have image_prompts
            output_dir: Directory to save generated images
            reference_image_url: Optional initial character reference image URL

        Returns:
            Updated ComicProject with image_path set on each panel
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        prev_image_url = reference_image_url

        for i, panel in enumerate(project.panels):
            logger.info(f"Generating panel {panel.panel_number}/{len(project.panels)}: "
                        f"{panel.image_prompt[:60]}...")

            output_path = str(Path(output_dir) / f"panel_{panel.panel_number:02d}.png")

            try:
                image_url = await self._generate_single(
                    prompt=panel.image_prompt,
                    reference_image_url=prev_image_url,
                    output_path=output_path,
                )
                panel.image_path = output_path
                prev_image_url = image_url  # Use as reference for next panel
                project.total_cost += COST_PER_IMAGE
                project.log(f"Panel {panel.panel_number} image generated: {output_path}")

            except Exception as e:
                logger.error(f"Panel {panel.panel_number} generation failed: {e}")
                project.log(f"Panel {panel.panel_number} FAILED: {e}")
                # Continue with remaining panels — don't abort entire run

        return project

    async def _generate_single(
        self,
        prompt: str,
        reference_image_url: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Generate a single image via Flux Kontext Pro.

        Uses fal.ai queue API: submit → poll → fetch result.

        Args:
            prompt: Image generation prompt
            reference_image_url: URL of reference image for character consistency
            output_path: Local path to save the image

        Returns:
            URL of the generated image (for use as reference in next panel)
        """
        client = await self._get_client()

        # Build request payload
        payload = {
            "prompt": prompt,
            "num_images": 1,
            "guidance_scale": 3.5,
            "safety_tolerance": "2",
            "output_format": "png",
        }

        # Choose endpoint: text-to-image (no reference) vs image-to-image (with reference)
        if reference_image_url:
            payload["image_url"] = reference_image_url
            model = FLUX_KONTEXT_IMG2IMG
            logger.info("Using Kontext image-to-image (with reference)")
        else:
            model = FLUX_KONTEXT_TXT2IMG
            logger.info("Using Kontext text-to-image (no reference)")

        # Submit to queue
        submit_url = f"{FAL_API_BASE}/{model}"
        response = await client.post(submit_url, json=payload)

        if response.status_code != 200:
            raise RuntimeError(
                f"fal.ai submit failed ({response.status_code}): {response.text[:500]}"
            )

        result_data = response.json()

        # Queue-based: check if we got a request_id for polling
        if "request_id" in result_data and "images" not in result_data:
            result_data = await self._poll_result(
                request_id=result_data["request_id"],
                model=model,
                status_url=result_data.get("status_url", ""),
                response_url=result_data.get("response_url", ""),
            )
        # Direct result (sometimes fal returns immediately for fast models)

        # Extract image URL from result
        images = result_data.get("images", [])
        if not images:
            raise RuntimeError(f"No images in fal.ai response: {result_data}")

        image_url = images[0].get("url", "")
        if not image_url:
            raise RuntimeError(f"No image URL in response: {images[0]}")

        # Download and save locally
        if output_path:
            await self._download_image(image_url, output_path)

        return image_url

    async def _poll_result(
        self,
        request_id: str,
        model: str,
        status_url: str = "",
        response_url: str = "",
        max_wait: int = 300,
    ) -> dict:
        """Poll fal.ai queue for result."""
        client = await self._get_client()

        # Use URLs from submit response, or construct fallbacks
        if not status_url:
            status_url = f"{FAL_API_BASE}/{model}/requests/{request_id}/status"
        if not response_url:
            response_url = f"{FAL_API_BASE}/{model}/requests/{request_id}"

        logger.info(f"Polling fal.ai: {status_url}")

        elapsed = 0
        interval = 2  # Start polling every 2 seconds

        while elapsed < max_wait:
            await asyncio.sleep(interval)
            elapsed += interval

            response = await client.get(status_url)
            if response.status_code != 200:
                logger.warning(f"Poll status check failed: {response.status_code} - {response.text[:200]}")
                # Try the response_url directly (some fal endpoints skip status)
                if elapsed > 10:
                    result_response = await client.get(response_url)
                    if result_response.status_code == 200:
                        data = result_response.json()
                        if "images" in data:
                            return data
                continue

            status = response.json()
            state = status.get("status", "")

            if state == "COMPLETED":
                # Fetch full result
                result_response = await client.get(response_url)
                if result_response.status_code == 200:
                    return result_response.json()
                raise RuntimeError(f"Failed to fetch result: {result_response.status_code}")

            elif state in ("FAILED", "CANCELLED"):
                error = status.get("error", "Unknown error")
                raise RuntimeError(f"fal.ai generation failed: {error}")

            # Still in queue or processing — keep polling
            logger.info(f"fal.ai status: {state} ({elapsed}s elapsed)")

            # Back off polling interval gradually
            if elapsed > 30:
                interval = 5
            if elapsed > 120:
                interval = 10

        raise RuntimeError(f"fal.ai generation timed out after {max_wait}s")

    async def _download_image(self, url: str, output_path: str):
        """Download an image from URL to local file."""
        client = await self._get_client()
        response = await client.get(url)

        if response.status_code != 200:
            raise RuntimeError(f"Image download failed ({response.status_code})")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Image saved: {output_path} ({len(response.content)} bytes)")

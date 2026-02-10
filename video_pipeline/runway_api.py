"""
Runway Gen-3 API integration for video animation.
"""

import asyncio
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

RUNWAY_BASE_URL = "https://api.dev.runwayml.com/v1"


class RunwayAPI:
    """Runway Gen-3 video generation API client."""

    def __init__(self):
        self._api_key: Optional[str] = None

    def _get_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        key = os.environ.get("RUNWAY_API_KEY", "")
        if not key:
            raise RuntimeError("RUNWAY_API_KEY not configured in .env")
        self._api_key = key
        return key

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06",
        }

    async def animate_image(
        self,
        image_url: str,
        motion_prompt: str = "Slow cinematic camera movement",
        duration: int = 5,  # 5 or 10 seconds
        model: str = "gen3a_turbo",
    ) -> dict:
        """
        Animate a still image into video using Runway Gen-3.

        Args:
            image_url: URL of the source image
            motion_prompt: Description of desired motion
            duration: Video duration (5 or 10 seconds)
            model: gen3a_turbo (fast) or gen3a (quality)

        Returns:
            dict with task_id and video URL
        """
        logger.info(f"Runway: Animating image - {motion_prompt[:50]}...")

        async with httpx.AsyncClient(timeout=300) as client:
            # Start generation
            response = await client.post(
                f"{RUNWAY_BASE_URL}/image_to_video",
                headers=self._headers(),
                json={
                    "model": model,
                    "promptImage": image_url,
                    "promptText": motion_prompt,
                    "duration": duration,
                    "watermark": False,
                },
            )

            if not response.is_success:
                raise RuntimeError(f"Runway generation failed: {response.text}")

            data = response.json()
            task_id = data["id"]
            logger.info(f"Runway: Task started - {task_id}")

            # Poll for completion
            for _ in range(120):  # 10 minutes max
                await asyncio.sleep(5)

                response = await client.get(
                    f"{RUNWAY_BASE_URL}/tasks/{task_id}",
                    headers=self._headers(),
                )

                if not response.is_success:
                    continue

                task_data = response.json()
                status = task_data.get("status")

                if status == "SUCCEEDED":
                    video_url = task_data.get("output", [None])[0]
                    logger.info(f"Runway: Animation complete")
                    return {
                        "task_id": task_id,
                        "video_url": video_url,
                    }
                elif status == "FAILED":
                    error = task_data.get("failure", "Unknown error")
                    raise RuntimeError(f"Runway animation failed: {error}")

            raise RuntimeError("Runway animation timed out")

    async def download_video(self, url: str) -> bytes:
        """Download a video from URL."""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url)
            if not response.is_success:
                raise RuntimeError(f"Failed to download video: {response.status_code}")
            return response.content

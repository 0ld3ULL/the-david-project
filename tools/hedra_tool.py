"""
Hedra API integration for AI lip-sync video generation.
Ported from FRONTMAN TypeScript implementation.

Workflow:
1. Upload character image → get image asset ID
2. Upload audio file → get audio asset ID
3. Create video generation job
4. Poll for completion (5-15 minutes)
5. Return final video URL
"""

import asyncio
import base64
import logging
import os
import random
from typing import Callable, Optional

import httpx

logger = logging.getLogger(__name__)

HEDRA_BASE_URL = "https://api.hedra.com/web-app/public"
CHARACTER_3_MODEL_ID = "d1dd37a3-e39a-4854-a298-6510289f9cf2"

# Timeouts
UPLOAD_TIMEOUT = 120  # 2 minutes
GENERATION_TIMEOUT = 20 * 60  # 20 minutes
POLL_INTERVAL = 10  # 10 seconds
DOWNLOAD_TIMEOUT = 300  # 5 minutes

# Retries
MAX_UPLOAD_RETRIES = 3
MAX_API_RETRIES = 5


def get_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
    """Exponential backoff with jitter."""
    exponential_delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.random()
    return exponential_delay + jitter


class HedraError(Exception):
    """Hedra API error with user-friendly message."""
    pass


class HedraTool:
    """Hedra lip-sync video generation tool."""

    def __init__(self):
        self._api_key: Optional[str] = None

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        if self._api_key:
            return self._api_key

        key = os.environ.get("HEDRA_API_KEY", "")
        if not key:
            raise RuntimeError("HEDRA_API_KEY not configured in .env")
        self._api_key = key
        return key

    def _headers(self) -> dict:
        """Get standard headers for API requests."""
        return {"X-API-Key": self._get_api_key()}

    async def _execute_with_retry(
        self,
        operation: Callable,
        operation_name: str,
        max_attempts: int = MAX_API_RETRIES,
    ):
        """Execute operation with retry and exponential backoff."""
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"[Hedra] {operation_name} - attempt {attempt}/{max_attempts}")
                return await operation()
            except Exception as e:
                last_error = e
                logger.error(f"[Hedra] {operation_name} failed (attempt {attempt}): {e}")

                if attempt == max_attempts:
                    break

                # Don't retry auth errors
                error_msg = str(e).lower()
                if "401" in error_msg or "unauthorized" in error_msg:
                    raise HedraError("Hedra API key is invalid or expired. Please check your API key.")
                if "403" in error_msg or "forbidden" in error_msg:
                    raise HedraError("Hedra API access denied. Check your API key permissions or credits.")
                if any(x in error_msg for x in ["credit", "quota", "limit", "insufficient", "402"]):
                    raise HedraError("You are out of Hedra credits. Please add more at hedra.com")

                delay = get_backoff_delay(attempt)
                logger.info(f"[Hedra] Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        raise last_error or HedraError(f"{operation_name} failed after {max_attempts} attempts")

    async def upload_image(self, image_url: str) -> str:
        """
        Upload an image to Hedra.

        Args:
            image_url: URL of the character image

        Returns:
            Asset ID for the uploaded image
        """
        async def _upload():
            async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
                # Fetch image
                logger.info(f"[Hedra] Fetching image from: {image_url[:50]}...")
                img_response = await client.get(image_url)
                if not img_response.is_success:
                    raise HedraError(f"Failed to fetch image: {img_response.status_code}")

                image_data = img_response.content
                logger.info(f"[Hedra] Image fetched: {len(image_data) // 1024}KB")

                # Create asset placeholder
                logger.info("[Hedra] Creating image asset placeholder...")
                create_response = await client.post(
                    f"{HEDRA_BASE_URL}/assets",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={"name": f"character-{int(asyncio.get_event_loop().time() * 1000)}", "type": "image"},
                )

                if not create_response.is_success:
                    error = create_response.text
                    if create_response.status_code == 401:
                        raise HedraError("Hedra API key is invalid or expired.")
                    raise HedraError(f"Asset creation failed ({create_response.status_code}): {error}")

                asset_id = create_response.json()["id"]
                logger.info(f"[Hedra] Asset placeholder created: {asset_id}")

                # Upload file
                logger.info("[Hedra] Uploading image file...")
                files = {"file": ("character.png", image_data, "image/png")}
                upload_response = await client.post(
                    f"{HEDRA_BASE_URL}/assets/{asset_id}/upload",
                    headers=self._headers(),
                    files=files,
                )

                if not upload_response.is_success:
                    raise HedraError(f"Image upload failed: {upload_response.text}")

                result_id = upload_response.json()["id"]
                logger.info(f"[Hedra] Image uploaded: {result_id}")
                return result_id

        return await self._execute_with_retry(_upload, "Image upload", MAX_UPLOAD_RETRIES)

    async def upload_audio(self, audio_data: bytes, filename: str = "audio.mp3") -> str:
        """
        Upload audio to Hedra.

        Args:
            audio_data: Audio file bytes
            filename: Name for the uploaded file

        Returns:
            Asset ID for the uploaded audio
        """
        async def _upload():
            async with httpx.AsyncClient(timeout=UPLOAD_TIMEOUT) as client:
                logger.info(f"[Hedra] Uploading audio: {len(audio_data) // 1024}KB")

                # Create asset placeholder
                create_response = await client.post(
                    f"{HEDRA_BASE_URL}/assets",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={"name": f"audio-{int(asyncio.get_event_loop().time() * 1000)}", "type": "audio"},
                )

                if not create_response.is_success:
                    raise HedraError(f"Audio asset creation failed: {create_response.text}")

                asset_id = create_response.json()["id"]
                logger.info(f"[Hedra] Audio asset placeholder: {asset_id}")

                # Upload file
                files = {"file": (filename, audio_data, "audio/mpeg")}
                upload_response = await client.post(
                    f"{HEDRA_BASE_URL}/assets/{asset_id}/upload",
                    headers=self._headers(),
                    files=files,
                )

                if not upload_response.is_success:
                    raise HedraError(f"Audio upload failed: {upload_response.text}")

                result_id = upload_response.json()["id"]
                logger.info(f"[Hedra] Audio uploaded: {result_id}")
                return result_id

        return await self._execute_with_retry(_upload, "Audio upload", MAX_UPLOAD_RETRIES)

    async def upload_audio_from_url(self, audio_url: str) -> str:
        """Upload audio from a URL."""
        async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT) as client:
            response = await client.get(audio_url)
            if not response.is_success:
                raise HedraError(f"Failed to fetch audio: {response.status_code}")
            return await self.upload_audio(response.content)

    async def upload_audio_from_base64(self, base64_data: str) -> str:
        """Upload audio from base64 data."""
        if base64_data.startswith("data:"):
            # Extract base64 from data URL
            base64_data = base64_data.split(",", 1)[1]
        audio_bytes = base64.b64decode(base64_data)
        return await self.upload_audio(audio_bytes)

    async def start_generation(
        self,
        image_asset_id: str,
        audio_asset_id: str,
        aspect_ratio: str = "9:16",
        resolution: str = "720p",
        prompt: str = "Person speaking with subtle minimal head movement, calm steady gaze, looking directly at camera",
    ) -> str:
        """
        Start a video generation job.

        Returns:
            Generation ID for polling
        """
        async def _generate():
            async with httpx.AsyncClient(timeout=60) as client:
                logger.info("[Hedra] Starting video generation...")
                logger.info(f"[Hedra] - Image asset: {image_asset_id}")
                logger.info(f"[Hedra] - Audio asset: {audio_asset_id}")
                logger.info(f"[Hedra] - Aspect ratio: {aspect_ratio}")

                response = await client.post(
                    f"{HEDRA_BASE_URL}/generations",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={
                        "type": "video",
                        "ai_model_id": CHARACTER_3_MODEL_ID,
                        "start_keyframe_id": image_asset_id,
                        "audio_id": audio_asset_id,
                        "generated_video_inputs": {
                            "text_prompt": prompt,
                            "resolution": resolution,
                            "aspect_ratio": aspect_ratio,
                        },
                    },
                )

                if not response.is_success:
                    error = response.text.lower()
                    if response.status_code == 401:
                        raise HedraError("Hedra API key is invalid or expired.")
                    if response.status_code == 402 or "credit" in error:
                        raise HedraError("You are out of Hedra credits.")
                    raise HedraError(f"Generation failed ({response.status_code}): {response.text}")

                gen_id = response.json()["id"]
                logger.info(f"[Hedra] Generation started: {gen_id}")
                return gen_id

        return await self._execute_with_retry(_generate, "Start generation", MAX_API_RETRIES)

    async def get_generation_status(self, generation_id: str) -> dict:
        """Check generation status."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{HEDRA_BASE_URL}/generations/{generation_id}/status",
                headers=self._headers(),
            )
            if not response.is_success:
                raise HedraError(f"Status check failed: {response.text}")
            return response.json()

    async def wait_for_completion(
        self,
        generation_id: str,
        poll_interval: float = POLL_INTERVAL,
        timeout: float = GENERATION_TIMEOUT,
        on_progress: Optional[Callable[[dict], None]] = None,
    ) -> str:
        """
        Poll for video completion.

        Returns:
            URL of the completed video
        """
        start_time = asyncio.get_event_loop().time()
        poll_count = 0

        logger.info(f"[Hedra] Waiting for completion (timeout: {timeout // 60} minutes)...")

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            poll_count += 1
            elapsed = int(asyncio.get_event_loop().time() - start_time)

            try:
                status = await self.get_generation_status(generation_id)
                logger.info(f"[Hedra] Poll #{poll_count} ({elapsed}s) - Status: {status.get('status')}")

                if on_progress:
                    on_progress(status)

                if status.get("status") == "complete" and status.get("url"):
                    logger.info(f"[Hedra] Video completed after {elapsed}s!")
                    return status["url"]

                if status.get("status") == "error":
                    raise HedraError(f"Generation failed: {status.get('error_message', 'Unknown error')}")

            except HedraError:
                raise
            except Exception as e:
                logger.warning(f"[Hedra] Poll error (will retry): {e}")

            # Wait with jitter
            await asyncio.sleep(poll_interval + random.random())

        raise HedraError(f"Video generation timed out after {timeout // 60} minutes")

    async def get_credits(self) -> dict:
        """Get Hedra credits info."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{HEDRA_BASE_URL}/billing/credits",
                headers=self._headers(),
            )
            if not response.is_success:
                raise HedraError(f"Failed to get credits: {response.text}")

            data = response.json()
            return {
                "remaining": data.get("remaining", 0),
                "expiring": data.get("expiring", 0),
                "used": data.get("used", 0),
            }

    async def create_talking_head_video(
        self,
        character_image_url: str,
        audio_data: bytes,
        aspect_ratio: str = "9:16",
        resolution: str = "720p",
        on_progress: Optional[Callable[[str, dict], None]] = None,
    ) -> dict:
        """
        Full video generation workflow.

        Args:
            character_image_url: URL of character image
            audio_data: Audio bytes (MP3)
            aspect_ratio: Video aspect ratio
            resolution: Video resolution
            on_progress: Callback for progress updates

        Returns:
            {"generation_id": str, "video_url": str}
        """
        logger.info("[Hedra] ========================================")
        logger.info("[Hedra] Starting video generation pipeline")
        logger.info("[Hedra] ========================================")

        try:
            # 1. Upload image
            logger.info("[Hedra] Stage 1/4: Uploading character image...")
            if on_progress:
                on_progress("uploading_image", {})
            image_asset_id = await self.upload_image(character_image_url)

            # 2. Upload audio
            logger.info("[Hedra] Stage 2/4: Uploading audio...")
            if on_progress:
                on_progress("uploading_audio", {})
            audio_asset_id = await self.upload_audio(audio_data)

            # 3. Start generation
            logger.info("[Hedra] Stage 3/4: Starting Hedra video generation...")
            if on_progress:
                on_progress("generating", {})
            generation_id = await self.start_generation(
                image_asset_id, audio_asset_id, aspect_ratio, resolution
            )

            # 4. Wait for completion
            logger.info("[Hedra] Stage 4/4: Waiting for video completion...")
            video_url = await self.wait_for_completion(
                generation_id,
                on_progress=lambda s: on_progress("processing", s) if on_progress else None,
            )

            logger.info("[Hedra] ========================================")
            logger.info("[Hedra] Video generation completed!")
            logger.info("[Hedra] ========================================")

            if on_progress:
                on_progress("completed", {"video_url": video_url})

            return {"generation_id": generation_id, "video_url": video_url}

        except Exception as e:
            logger.error(f"[Hedra] Video generation FAILED: {e}")
            if on_progress:
                on_progress("failed", {"error": str(e)})
            raise

    # --- Draft methods for approval queue ---

    def draft_video(
        self,
        script: str,
        character_image_url: str,
        voice_id: Optional[str] = None,
    ) -> dict:
        """Create a draft video generation for approval queue."""
        return {
            "action": "generate_video",
            "script": script,
            "character_image_url": character_image_url,
            "voice_id": voice_id or os.environ.get("ELEVENLABS_VOICE_ID", ""),
        }

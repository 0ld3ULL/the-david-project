"""
ElevenLabs API integration for voice synthesis.
Ported from FRONTMAN TypeScript implementation.
"""

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Available models
ELEVENLABS_MODELS = {
    "eleven_v3": "V3 (English) - Best quality, emotion tags support",
    "eleven_multilingual_v2": "V2 Multilingual - Multiple languages",
    "eleven_turbo_v2_5": "Turbo V2.5 - Fast, low latency",
    "eleven_flash_v2_5": "Flash V2.5 - Fastest",
}


def parse_error(status: int, error_body: str) -> str:
    """Parse ElevenLabs API error and return user-friendly message."""
    try:
        import json
        parsed = json.loads(error_body)
        detail = parsed.get("detail", {})
        if isinstance(detail, dict):
            detail = detail.get("message", str(detail))
        elif not detail:
            detail = parsed.get("message") or parsed.get("error")
    except:
        detail = error_body

    messages = {
        401: "Invalid ElevenLabs API key. Please check your API key.",
        402: "ElevenLabs account has insufficient credits. Please add credits at elevenlabs.io.",
        403: "Access denied. Your ElevenLabs API key may not have permission for this feature.",
        429: "ElevenLabs rate limit exceeded. Please wait and try again.",
        422: f"ElevenLabs error: {detail}" if detail else "Invalid request to ElevenLabs.",
    }

    if status in messages:
        return messages[status]
    if status >= 500:
        return "ElevenLabs service is temporarily unavailable. Please try again."
    return f"ElevenLabs error ({status}): {detail or error_body}"


class ElevenLabsTool:
    """ElevenLabs text-to-speech tool."""

    def __init__(self):
        self._api_key: Optional[str] = None

    def _get_api_key(self) -> str:
        """Get API key from environment."""
        if self._api_key:
            return self._api_key

        key = os.environ.get("ELEVENLABS_API_KEY", "")
        if not key:
            raise RuntimeError("ELEVENLABS_API_KEY not configured in .env")
        self._api_key = key
        return key

    def _headers(self) -> dict:
        """Get standard headers for API requests."""
        return {
            "Accept": "application/json",
            "xi-api-key": self._get_api_key(),
        }

    async def validate_api_key(self) -> dict:
        """Validate API key and return usage info."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{ELEVENLABS_BASE_URL}/user",
                headers=self._headers(),
            )

            if not response.is_success:
                raise RuntimeError(parse_error(response.status_code, response.text))

            data = response.json()
            sub = data.get("subscription", {})

            return {
                "tier": sub.get("tier", "unknown"),
                "characters_used": sub.get("character_count", 0),
                "character_limit": sub.get("character_limit", 0),
                "characters_remaining": max(0, sub.get("character_limit", 0) - sub.get("character_count", 0)),
            }

    async def get_voices(self) -> list[dict]:
        """Fetch user's personal voices."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{ELEVENLABS_BASE_URL}/voices",
                headers=self._headers(),
            )

            if not response.is_success:
                raise RuntimeError(parse_error(response.status_code, response.text))

            data = response.json()
            return data.get("voices", [])

    async def get_voice(self, voice_id: str) -> Optional[dict]:
        """Get a specific voice by ID."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{ELEVENLABS_BASE_URL}/voices/{voice_id}",
                headers=self._headers(),
            )

            if response.status_code == 404:
                return None
            if not response.is_success:
                raise RuntimeError(parse_error(response.status_code, response.text))

            return response.json()

    async def text_to_speech(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model: str = "eleven_v3",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.5,
        use_speaker_boost: bool = True,
    ) -> bytes:
        """
        Generate speech from text.

        Args:
            text: The text to convert to speech
            voice_id: ElevenLabs voice ID (uses ELEVENLABS_VOICE_ID from env if not provided)
            model: TTS model to use (eleven_v3, eleven_multilingual_v2, etc.)
            stability: Voice stability (0.0-1.0)
            similarity_boost: Voice clarity (0.0-1.0)
            style: Expressiveness (0.0-1.0, higher = more emotional)
            use_speaker_boost: Enable speaker boost for clarity

        Returns:
            Audio data as bytes (MP3 format)
        """
        if not voice_id:
            voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "")
            if not voice_id:
                raise RuntimeError("No voice_id provided and ELEVENLABS_VOICE_ID not set in .env")

        logger.info(f"Generating speech: {len(text)} chars, voice={voice_id}, model={model}")

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self._get_api_key(),
                },
                json={
                    "text": text,
                    "model_id": model,
                    "voice_settings": {
                        "stability": stability,
                        "similarity_boost": similarity_boost,
                        "style": style,
                        "use_speaker_boost": use_speaker_boost,
                    },
                },
            )

            if not response.is_success:
                raise RuntimeError(parse_error(response.status_code, response.text))

            audio_data = response.content
            logger.info(f"Audio generated: {len(audio_data)} bytes")
            return audio_data

    # --- Draft methods for approval queue ---

    def draft_audio(self, text: str, voice_id: Optional[str] = None) -> dict:
        """Create a draft audio generation for approval queue."""
        return {
            "action": "generate_audio",
            "text": text,
            "voice_id": voice_id or os.environ.get("ELEVENLABS_VOICE_ID", ""),
        }

    async def execute(self, action_data: dict) -> dict:
        """Execute an approved audio action."""
        action = action_data.get("action")

        if action == "generate_audio":
            try:
                audio = await self.text_to_speech(
                    text=action_data["text"],
                    voice_id=action_data.get("voice_id"),
                )
                # Save to temp file and return path
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(audio)
                    return {"audio_path": f.name, "size_bytes": len(audio)}
            except Exception as e:
                logger.error(f"Audio generation failed: {e}")
                return {"error": str(e)}
        else:
            return {"error": f"Unknown action: {action}"}

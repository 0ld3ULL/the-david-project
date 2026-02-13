"""
Pixel Quality Reviewer — Video quality assessment via Gemini.

Uses Gemini 2.0 Flash to watch produced videos natively (audio + visual)
and score them across multiple quality dimensions. This replaces the
frame-extraction approach — Gemini can watch entire videos.

Scoring dimensions (each 1-10):
- Visual quality: resolution, clarity, artifacts
- Motion: smoothness, naturalness, consistency
- Character consistency: face/body coherence across scenes
- Audio sync: voice matches lip movement, timing
- Script adherence: video matches the intended script/prompt

Overall score = weighted average. Threshold: 7.0 for delivery.

Requires: GOOGLE_API_KEY in .env
"""

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class QualityScore:
    """Quality assessment for a produced video."""
    visual_quality: float = 0.0       # Resolution, clarity, artifacts
    motion: float = 0.0               # Smoothness, naturalness
    consistency: float = 0.0          # Character/scene coherence
    audio_sync: float = 0.0           # Voice-lip sync, timing
    script_adherence: float = 0.0     # Matches intended content
    overall: float = 0.0              # Weighted average
    issues: list[str] = field(default_factory=list)
    recommendation: str = ""          # "approve" / "regenerate" / "adjust"
    regeneration_notes: str = ""      # What to change if regenerating
    reviewed_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# Weights for overall score calculation
SCORE_WEIGHTS = {
    "visual_quality": 0.20,
    "motion": 0.25,
    "consistency": 0.20,
    "audio_sync": 0.15,
    "script_adherence": 0.20,
}

# Minimum overall score for delivery
DELIVERY_THRESHOLD = 7.0

# Minimum score for portfolio inclusion
PORTFOLIO_THRESHOLD = 8.0


class PixelReviewer:
    """
    Quality review engine using Gemini 2.0 Flash video analysis.

    Gemini can watch entire videos natively (both audio and visual tracks),
    making it ideal for comprehensive quality assessment without frame extraction.
    """

    def __init__(self, knowledge_store=None):
        self.knowledge_store = knowledge_store
        self._google_key = os.environ.get("GOOGLE_API_KEY")
        if not self._google_key:
            logger.warning("GOOGLE_API_KEY not set — video review will be unavailable")

    async def review_video(
        self,
        video_path: str | Path,
        script: str = "",
        context: dict = None,
    ) -> QualityScore:
        """
        Review a video using Gemini's native video analysis.

        Args:
            video_path: Path to the video file
            script: The intended script/prompt for adherence checking
            context: Additional context (model used, settings, etc.)

        Returns:
            QualityScore with all dimensions scored and recommendation
        """
        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"Video not found: {video_path}")
            return QualityScore(
                recommendation="regenerate",
                regeneration_notes="Video file not found",
                reviewed_at=datetime.now().isoformat(),
            )

        if not self._google_key:
            logger.error("Cannot review video — GOOGLE_API_KEY not set")
            return QualityScore(
                recommendation="adjust",
                regeneration_notes="Video review unavailable — no API key",
                reviewed_at=datetime.now().isoformat(),
            )

        try:
            score = await self._analyze_with_gemini(video_path, script, context or {})
            score.reviewed_at = datetime.now().isoformat()

            # Log the review
            logger.info(
                f"Quality review: {score.overall:.1f}/10 — {score.recommendation} "
                f"[V:{score.visual_quality:.0f} M:{score.motion:.0f} "
                f"C:{score.consistency:.0f} A:{score.audio_sync:.0f} "
                f"S:{score.script_adherence:.0f}]"
            )

            # Store review in knowledge base if available
            if self.knowledge_store:
                self.knowledge_store.add(
                    category="lesson",
                    topic=f"Video quality review: {video_path.name}",
                    content=(
                        f"Overall: {score.overall:.1f}/10. "
                        f"Issues: {'; '.join(score.issues) if score.issues else 'none'}. "
                        f"Recommendation: {score.recommendation}"
                    ),
                    source="gemini_review",
                    confidence=0.9,
                    tags=["quality_review", "video", score.recommendation],
                )

            return score

        except Exception as e:
            logger.error(f"Video review failed: {e}")
            return QualityScore(
                recommendation="adjust",
                regeneration_notes=f"Review failed: {e}",
                reviewed_at=datetime.now().isoformat(),
            )

    async def _analyze_with_gemini(
        self,
        video_path: Path,
        script: str,
        context: dict,
    ) -> QualityScore:
        """
        Upload video to Gemini and get quality analysis.

        Uses the Google AI Studio Files API to upload the video,
        then asks Gemini to analyze it with a structured scoring prompt.
        """
        import httpx
        import time

        # Step 1: Upload video to Google AI Files API
        file_uri = await self._upload_video(video_path)

        # Step 2: Send analysis request with video reference
        prompt = self._build_review_prompt(script, context)

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

        payload = {
            "contents": [{
                "parts": [
                    {"file_data": {"mime_type": "video/mp4", "file_uri": file_uri}},
                    {"text": prompt},
                ]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2000,
            },
        }

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(
                url,
                json=payload,
                params={"key": self._google_key},
            )

            if response.status_code != 200:
                raise Exception(f"Gemini API error {response.status_code}: {response.text}")

            result = response.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"]

        # Step 3: Parse the structured response
        return self._parse_review_response(text)

    async def _upload_video(self, video_path: Path) -> str:
        """
        Upload video to Google AI Files API for Gemini analysis.

        Returns the file URI to reference in the generate request.
        """
        import httpx

        file_size = video_path.stat().st_size
        mime_type = "video/mp4"

        # Start resumable upload
        async with httpx.AsyncClient(timeout=120) as client:
            # Initiate upload
            init_response = await client.post(
                "https://generativelanguage.googleapis.com/upload/v1beta/files",
                params={"key": self._google_key},
                headers={
                    "X-Goog-Upload-Protocol": "resumable",
                    "X-Goog-Upload-Command": "start",
                    "X-Goog-Upload-Header-Content-Length": str(file_size),
                    "X-Goog-Upload-Header-Content-Type": mime_type,
                    "Content-Type": "application/json",
                },
                json={"file": {"display_name": video_path.name}},
            )

            if init_response.status_code != 200:
                raise Exception(f"Upload init failed: {init_response.status_code}")

            upload_url = init_response.headers.get("X-Goog-Upload-URL")
            if not upload_url:
                raise Exception("No upload URL in response")

            # Upload file content
            with open(video_path, "rb") as f:
                video_data = f.read()

            upload_response = await client.put(
                upload_url,
                content=video_data,
                headers={
                    "X-Goog-Upload-Command": "upload, finalize",
                    "X-Goog-Upload-Offset": "0",
                    "Content-Length": str(file_size),
                },
            )

            if upload_response.status_code != 200:
                raise Exception(f"Upload failed: {upload_response.status_code}")

            file_info = upload_response.json()
            file_uri = file_info["file"]["uri"]
            file_name = file_info["file"]["name"]

        # Wait for file processing
        await self._wait_for_file_active(file_name)

        logger.info(f"Video uploaded: {file_uri}")
        return file_uri

    async def _wait_for_file_active(self, file_name: str, timeout: int = 120):
        """Wait for uploaded file to become ACTIVE (processed by Google)."""
        import httpx
        import asyncio

        start = datetime.now()
        async with httpx.AsyncClient(timeout=30) as client:
            while (datetime.now() - start).total_seconds() < timeout:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/{file_name}",
                    params={"key": self._google_key},
                )

                if response.status_code == 200:
                    state = response.json().get("state", "")
                    if state == "ACTIVE":
                        return
                    elif state == "FAILED":
                        raise Exception("File processing failed")

                await asyncio.sleep(5)

        raise Exception(f"File not active after {timeout}s")

    def _build_review_prompt(self, script: str, context: dict) -> str:
        """Build the structured review prompt for Gemini."""
        model_used = context.get("model", "unknown")
        duration = context.get("duration", "unknown")

        prompt = """You are a professional video quality reviewer. Watch this video carefully and score it on these dimensions (each 1-10):

1. VISUAL QUALITY (1-10): Resolution, clarity, absence of artifacts, color accuracy
2. MOTION (1-10): Smoothness of movement, naturalness, no jitter or warping
3. CONSISTENCY (1-10): Character faces/bodies stay coherent across scenes, no morphing
4. AUDIO SYNC (1-10): Voice matches lip movement, sound timing is correct, audio quality
5. SCRIPT ADHERENCE (1-10): Video content matches the intended script/prompt"""

        if script:
            prompt += f"\n\nINTENDED SCRIPT:\n{script}"

        prompt += f"""

CONTEXT:
- Video model: {model_used}
- Target duration: {duration}

Respond in EXACTLY this JSON format (no other text):
{{
    "visual_quality": <number>,
    "motion": <number>,
    "consistency": <number>,
    "audio_sync": <number>,
    "script_adherence": <number>,
    "issues": ["issue 1", "issue 2"],
    "recommendation": "approve" or "regenerate" or "adjust",
    "regeneration_notes": "what to change if regenerating"
}}

Score honestly. A score of 5 means average/acceptable. 7+ means good. 9+ means excellent.
If there's no audio track, score audio_sync as 5 (neutral) and note it in issues."""

        return prompt

    def _parse_review_response(self, text: str) -> QualityScore:
        """Parse Gemini's JSON response into a QualityScore."""
        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                text = text[start:end]

            data = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{[^}]+\}', text, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse review response: {text[:200]}")
                    return QualityScore(
                        recommendation="adjust",
                        regeneration_notes="Failed to parse quality review",
                    )
            else:
                return QualityScore(
                    recommendation="adjust",
                    regeneration_notes="No structured review in response",
                )

        score = QualityScore(
            visual_quality=float(data.get("visual_quality", 5)),
            motion=float(data.get("motion", 5)),
            consistency=float(data.get("consistency", 5)),
            audio_sync=float(data.get("audio_sync", 5)),
            script_adherence=float(data.get("script_adherence", 5)),
            issues=data.get("issues", []),
            recommendation=data.get("recommendation", "adjust"),
            regeneration_notes=data.get("regeneration_notes", ""),
        )

        # Calculate weighted overall score
        score.overall = (
            score.visual_quality * SCORE_WEIGHTS["visual_quality"]
            + score.motion * SCORE_WEIGHTS["motion"]
            + score.consistency * SCORE_WEIGHTS["consistency"]
            + score.audio_sync * SCORE_WEIGHTS["audio_sync"]
            + score.script_adherence * SCORE_WEIGHTS["script_adherence"]
        )

        # Override recommendation based on score thresholds
        if score.overall < DELIVERY_THRESHOLD and score.recommendation == "approve":
            score.recommendation = "regenerate"
            score.regeneration_notes = (
                f"Overall score {score.overall:.1f} below delivery threshold {DELIVERY_THRESHOLD}. "
                + score.regeneration_notes
            )

        return score

    def should_add_to_portfolio(self, score: QualityScore) -> bool:
        """Check if a video is good enough for the portfolio."""
        return score.overall >= PORTFOLIO_THRESHOLD

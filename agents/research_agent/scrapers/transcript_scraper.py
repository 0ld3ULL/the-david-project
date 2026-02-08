"""
Transcript Scraper - Fetches full video transcripts from YouTube and TikTok.

YouTube: Uses youtube-transcript-api (free, no API key) + RSS feeds for channel monitoring.
TikTok: Uses Supadata API (free tier) if SUPADATA_API_KEY is set.

This complements the existing YouTubeScraper which only gets titles/descriptions.
The transcript scraper gets the actual spoken content for deep analysis.
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import List, Optional
from xml.etree import ElementTree

import httpx
import yaml

from ..knowledge_store import ResearchItem

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/research_goals.yaml"

# Cache file for resolved channel IDs
CHANNEL_CACHE_PATH = "data/youtube_channel_cache.json"


class TranscriptScraper:
    """Fetches full video transcripts from YouTube channels and TikTok accounts."""

    name = "transcript"

    def __init__(self):
        self.config = self._load_config()
        self.client = httpx.AsyncClient(timeout=30.0)
        self.channel_cache = self._load_channel_cache()
        self.delay = self.config.get("delay_between_fetches", 5)
        self.max_length = self.config.get("max_transcript_length", 15000)

        # Supadata API for TikTok (optional)
        self.supadata_key = os.environ.get("SUPADATA_API_KEY", "")
        if self.supadata_key:
            logger.info("Supadata API key found - TikTok transcripts enabled")

    def _load_config(self) -> dict:
        """Load transcript scraper configuration."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("sources", {}).get("transcripts", {})
        except Exception as e:
            logger.error(f"Failed to load transcript config: {e}")
            return {}

    def _load_channel_cache(self) -> dict:
        """Load cached YouTube channel handle → ID mappings."""
        try:
            if os.path.exists(CHANNEL_CACHE_PATH):
                with open(CHANNEL_CACHE_PATH, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_channel_cache(self):
        """Save channel ID cache to disk."""
        try:
            os.makedirs(os.path.dirname(CHANNEL_CACHE_PATH), exist_ok=True)
            with open(CHANNEL_CACHE_PATH, "w") as f:
                json.dump(self.channel_cache, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save channel cache: {e}")

    async def scrape(self) -> List[ResearchItem]:
        """Scrape transcripts from all configured sources."""
        items = []

        # YouTube transcripts
        youtube_channels = self.config.get("youtube_channels", [])
        for channel in youtube_channels:
            try:
                channel_items = await self._scrape_youtube_channel(channel)
                items.extend(channel_items)
            except Exception as e:
                logger.error(f"Error scraping transcripts for {channel}: {e}")

        # TikTok transcripts (if Supadata API key available)
        if self.supadata_key:
            tiktok_accounts = self.config.get("tiktok_accounts", [])
            for account in tiktok_accounts:
                try:
                    tiktok_items = await self._scrape_tiktok_account(account)
                    items.extend(tiktok_items)
                except Exception as e:
                    logger.error(f"Error scraping TikTok transcripts for {account}: {e}")

        logger.info(f"Transcript scraper found {len(items)} items")
        return items

    # ==================== YOUTUBE ====================

    async def _scrape_youtube_channel(self, channel_handle: str) -> List[ResearchItem]:
        """Get transcripts from recent videos on a YouTube channel."""
        items = []
        handle = channel_handle.lstrip("@")

        # Get channel ID (needed for RSS feed)
        channel_id = await self._resolve_channel_id(handle)
        if not channel_id:
            logger.warning(f"Could not resolve channel ID for @{handle}")
            return items

        # Get recent video IDs from RSS feed (free, no API key)
        video_entries = await self._get_channel_videos_via_rss(channel_id, handle)

        # Fetch transcript for each new video
        for video_id, title, published in video_entries:
            try:
                transcript_text = await self._fetch_youtube_transcript(video_id)
                if transcript_text:
                    # Truncate if too long
                    if len(transcript_text) > self.max_length:
                        transcript_text = transcript_text[:self.max_length] + "\n\n[TRANSCRIPT TRUNCATED]"

                    items.append(ResearchItem(
                        source="transcript",
                        source_id=f"transcript:yt:{video_id}",
                        url=f"https://www.youtube.com/watch?v={video_id}",
                        title=f"[TRANSCRIPT] [@{handle}] {title}",
                        content=transcript_text,
                        published_at=published
                    ))

                # Throttle to avoid YouTube blocking
                await asyncio.sleep(self.delay)

            except Exception as e:
                logger.warning(f"Failed to get transcript for {video_id}: {e}")

        return items

    async def _resolve_channel_id(self, handle: str) -> Optional[str]:
        """Resolve a YouTube @handle to a channel ID. Uses cache."""
        import re

        # Check cache first
        if handle in self.channel_cache:
            return self.channel_cache[handle]

        # Scrape the channel page to find the ID
        try:
            url = f"https://www.youtube.com/@{handle}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36"
            }
            response = await self.client.get(url, follow_redirects=True, headers=headers)
            if response.status_code == 200:
                text = response.text
                # Try multiple patterns - YouTube embeds channel ID in various ways
                patterns = [
                    r'"channelId"\s*:\s*"(UC[a-zA-Z0-9_-]+)"',
                    r'"externalId"\s*:\s*"(UC[a-zA-Z0-9_-]+)"',
                    r'"browse_id"\s*:\s*"(UC[a-zA-Z0-9_-]+)"',
                    r'channel/(UC[a-zA-Z0-9_-]{22})',
                    r'\\x22channelId\\x22:\\x22(UC[a-zA-Z0-9_-]+)\\x22',
                ]
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        channel_id = match.group(1)
                        self.channel_cache[handle] = channel_id
                        self._save_channel_cache()
                        logger.info(f"Resolved @{handle} -> {channel_id}")
                        return channel_id

                logger.warning(f"Could not find channel ID in page for @{handle}")
        except Exception as e:
            logger.warning(f"Failed to resolve @{handle}: {e}")

        return None

    async def _get_channel_videos_via_rss(
        self, channel_id: str, handle: str, max_age_days: int = 7
    ) -> List[tuple]:
        """
        Get recent videos from a channel's RSS feed.
        Returns list of (video_id, title, published_datetime) tuples.
        Free, no API key, no quota limits.
        """
        videos = []
        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        try:
            response = await self.client.get(rss_url)
            if response.status_code != 200:
                logger.warning(f"RSS feed returned {response.status_code} for @{handle}")
                return videos

            # Parse Atom feed
            root = ElementTree.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

            cutoff = datetime.utcnow() - timedelta(days=max_age_days)

            for entry in root.findall("atom:entry", ns):
                video_id_el = entry.find("yt:videoId", ns)
                title_el = entry.find("atom:title", ns)
                published_el = entry.find("atom:published", ns)

                if video_id_el is None or title_el is None:
                    continue

                video_id = video_id_el.text
                title = title_el.text
                published = None

                if published_el is not None and published_el.text:
                    try:
                        published = datetime.fromisoformat(
                            published_el.text.replace("Z", "+00:00")
                        )
                        # Skip old videos
                        if published.replace(tzinfo=None) < cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass

                videos.append((video_id, title, published))

        except Exception as e:
            logger.error(f"Error fetching RSS for @{handle}: {e}")

        logger.debug(f"RSS: @{handle} has {len(videos)} recent videos")
        return videos

    async def _fetch_youtube_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch transcript for a YouTube video using youtube-transcript-api.
        Returns plain text of the transcript, or None if unavailable.
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            # Run in thread to avoid blocking async loop (library is sync)
            loop = asyncio.get_event_loop()
            api = YouTubeTranscriptApi()
            transcript = await loop.run_in_executor(
                None, lambda: api.fetch(video_id, languages=["en"])
            )

            # Combine all segments into plain text
            full_text = " ".join(
                snippet.text for snippet in transcript
            )

            return full_text.strip() if full_text else None

        except ImportError:
            logger.error("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")
            return None
        except Exception as e:
            # Common: TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
            logger.debug(f"No transcript for {video_id}: {e}")
            return None

    # ==================== TIKTOK ====================

    async def _scrape_tiktok_account(self, account: str) -> List[ResearchItem]:
        """
        Get transcripts from recent TikTok videos using Supadata API.
        Requires SUPADATA_API_KEY environment variable.
        """
        items = []
        handle = account.lstrip("@")

        # Supadata API endpoint
        # See: https://supadata.ai/tiktok-transcript-api
        try:
            # First get recent videos for this account
            # Note: Supadata requires video URLs, not account handles
            # For now, we'd need video URLs from another source or use their search
            # This is a placeholder for when TikTok account monitoring is added
            logger.debug(f"TikTok scraping for @{handle} - not yet implemented (need video URLs)")

        except Exception as e:
            logger.error(f"TikTok scraping error for @{handle}: {e}")

        return items

    async def _fetch_tiktok_transcript(self, video_url: str) -> Optional[str]:
        """Fetch transcript for a TikTok video via Supadata API."""
        if not self.supadata_key:
            return None

        try:
            response = await self.client.get(
                "https://api.supadata.ai/v1/tiktok/transcript",
                params={"url": video_url},
                headers={"x-api-key": self.supadata_key}
            )

            if response.status_code == 200:
                data = response.json()
                # Supadata returns transcript segments
                segments = data.get("transcript", [])
                if segments:
                    return " ".join(seg.get("text", "") for seg in segments)

        except Exception as e:
            logger.warning(f"Supadata error for {video_url}: {e}")

        return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

"""
Firecrawl Scraper - Full website crawling for deep content extraction.

Uses the Firecrawl API v1 to crawl target websites and extract
page content for research analysis.
Frequency: DAILY tier.
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from typing import List

import httpx
import yaml

from ..knowledge_store import ResearchItem

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/research_goals.yaml"
FIRECRAWL_API = "https://api.firecrawl.dev/v1"


class FirecrawlScraper:
    """Crawls target websites via Firecrawl API for deep content extraction."""

    name = "firecrawl"
    frequency = "daily"

    def __init__(self):
        self.config = self._load_config()
        self.api_key = os.getenv("FIRECRAWL_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=60.0)
        self.max_pages = self.config.get("max_pages_per_site", 10)

    def _load_config(self) -> dict:
        """Load Firecrawl configuration."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("sources", {}).get("firecrawl", {})
        except Exception as e:
            logger.error(f"Failed to load Firecrawl config: {e}")
            return {}

    async def scrape(self) -> List[ResearchItem]:
        """Crawl all configured target URLs."""
        if not self.config.get("enabled", True):
            return []

        if not self.api_key:
            logger.warning("FIRECRAWL_API_KEY not set, skipping Firecrawl scraper")
            return []

        targets = self.config.get("target_urls", [])
        if not targets:
            logger.warning("No Firecrawl target URLs configured")
            return []

        items = []

        for target in targets:
            url = target.get("url", "")
            label = target.get("label", "")
            goal = target.get("goal", "")
            if not url:
                continue

            try:
                pages = await self._crawl_site(url)
                for page in pages:
                    page_url = page.get("url", url)
                    page_title = page.get("title", "Untitled")
                    page_content = page.get("content", "")

                    # Cap content at 5000 characters
                    if len(page_content) > 5000:
                        page_content = page_content[:5000]

                    url_hash = hashlib.sha256(page_url.encode()).hexdigest()[:12]
                    items.append(ResearchItem(
                        source="firecrawl",
                        source_id=f"firecrawl:{url_hash}",
                        url=page_url,
                        title=f"[Firecrawl] {label}: {page_title}",
                        content=page_content,
                        published_at=datetime.utcnow(),
                    ))
            except Exception as e:
                logger.error(f"Error crawling '{label}' ({url}): {e}")

        logger.info(f"Firecrawl scraper produced {len(items)} items from {len(targets)} sites")
        return items

    async def _crawl_site(self, url: str) -> List[dict]:
        """Crawl a single site: submit job, poll for completion, return pages."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # 1. Submit crawl job
        payload = {
            "url": url,
            "limit": self.max_pages,
        }

        response = await self.client.post(
            f"{FIRECRAWL_API}/crawl", json=payload, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        job_id = data.get("id")
        if not job_id:
            logger.warning(f"No job ID returned for crawl of {url}")
            return []

        logger.info(f"Firecrawl job {job_id} started for {url}")

        # 2. Poll for completion (every 10s, timeout 300s)
        poll_url = f"{FIRECRAWL_API}/crawl/{job_id}"
        max_polls = 30  # 30 * 10s = 300s
        for i in range(max_polls):
            await asyncio.sleep(10)

            poll_response = await self.client.get(poll_url, headers=headers)
            poll_response.raise_for_status()
            poll_data = poll_response.json()

            status = poll_data.get("status", "")
            if status == "completed":
                return self._extract_pages(poll_data)
            elif status in ("failed", "cancelled"):
                logger.warning(f"Firecrawl job {job_id} {status} for {url}")
                return []

            logger.debug(f"Firecrawl job {job_id} status: {status} (poll {i + 1}/{max_polls})")

        logger.warning(f"Firecrawl job {job_id} timed out after 300s for {url}")
        return []

    def _extract_pages(self, data: dict) -> List[dict]:
        """Extract page data from a completed crawl response."""
        pages = []
        raw_data = data.get("data", [])

        for page in raw_data:
            metadata = page.get("metadata", {})
            content = page.get("markdown", "") or page.get("content", "")
            page_url = metadata.get("sourceURL", "") or page.get("url", "")
            title = metadata.get("title", "") or page.get("title", "Untitled")

            if content:
                pages.append({
                    "url": page_url,
                    "title": title,
                    "content": content,
                })

        return pages

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

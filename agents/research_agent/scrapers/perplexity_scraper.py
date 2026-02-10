"""
Perplexity Sonar Pro Scraper - AI-powered web search via OpenRouter.

Uses the OpenRouter API with perplexity/sonar-pro model to run
research queries defined in config/research_goals.yaml.
Frequency: WARM tier.
"""

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
OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "perplexity/sonar-pro"


class PerplexityScraper:
    """Scrapes the web via Perplexity Sonar Pro through OpenRouter."""

    name = "perplexity"
    frequency = "warm"

    def __init__(self):
        self.config = self._load_config()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=120.0)

    def _load_config(self) -> dict:
        """Load Perplexity configuration."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("sources", {}).get("perplexity", {})
        except Exception as e:
            logger.error(f"Failed to load Perplexity config: {e}")
            return {}

    async def scrape(self) -> List[ResearchItem]:
        """Run all configured search queries through Perplexity Sonar Pro."""
        if not self.config.get("enabled", True):
            return []

        if not self.api_key:
            logger.warning("OPENROUTER_API_KEY not set, skipping Perplexity scraper")
            return []

        queries = self.config.get("queries", [])
        if not queries:
            logger.warning("No Perplexity queries configured")
            return []

        items = []

        for entry in queries:
            query = entry.get("query", "")
            goal = entry.get("goal", "")
            if not query:
                continue

            try:
                response_text = await self._run_query(query)
                if response_text:
                    query_hash = hashlib.sha256(query.encode()).hexdigest()[:12]
                    items.append(ResearchItem(
                        source="perplexity",
                        source_id=f"perplexity:{query_hash}",
                        url="",
                        title=f"[Perplexity] {query}",
                        content=response_text,
                        published_at=datetime.utcnow(),
                    ))
            except Exception as e:
                logger.error(f"Error running Perplexity query '{query[:60]}': {e}")

        logger.info(f"Perplexity scraper produced {len(items)} items from {len(queries)} queries")
        return items

    async def _run_query(self, query: str) -> str:
        """Send a single query to Perplexity Sonar Pro via OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": MODEL,
            "messages": [
                {"role": "user", "content": query},
            ],
        }

        response = await self.client.post(OPENROUTER_API, json=payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")

        logger.warning(f"No choices in Perplexity response for query: {query[:60]}")
        return ""

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

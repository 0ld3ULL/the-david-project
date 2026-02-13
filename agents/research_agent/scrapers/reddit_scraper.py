"""
Reddit Scraper - Monitors subreddits for relevant discussions.

Uses Reddit's public JSON API (no auth needed for reading).
"""

import logging
from datetime import datetime
from typing import List

import httpx
import yaml

from ..knowledge_store import ResearchItem

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/research_goals.yaml"


class RedditScraper:
    """Scrapes Reddit for posts and discussions."""

    name = "reddit"

    def __init__(self):
        self.subreddits = self._load_subreddits()
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "DavidFlipResearchAgent/1.0 (Research bot for AI agent project)"
            }
        )

    def _load_subreddits(self) -> List[str]:
        """Load subreddit configuration."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("sources", {}).get("reddit", {}).get("subreddits", [])
        except Exception as e:
            logger.error(f"Failed to load Reddit config: {e}")
            return []

    async def scrape(self) -> List[ResearchItem]:
        """Scrape all configured subreddits."""
        items = []

        for subreddit in self.subreddits:
            try:
                posts = await self._get_hot_posts(subreddit)
                items.extend(posts)
            except Exception as e:
                logger.error(f"Error scraping r/{subreddit}: {e}")

        logger.info(f"Reddit scraper found {len(items)} items from {len(self.subreddits)} subreddits")
        return items

    async def _get_hot_posts(self, subreddit: str, limit: int = 10) -> List[ResearchItem]:
        """Get hot posts from a subreddit."""
        items = []
        url = f"https://old.reddit.com/r/{subreddit}/hot.json"

        try:
            response = await self.client.get(url, params={
                "limit": limit,
                "raw_json": 1
            })

            if response.status_code == 403:
                logger.warning(f"r/{subreddit} is private or banned")
                return items

            if response.status_code == 404:
                logger.warning(f"r/{subreddit} not found")
                return items

            response.raise_for_status()
            data = response.json()

            posts = data.get("data", {}).get("children", [])

            for post in posts:
                post_data = post.get("data", {})

                # Skip stickied posts (usually mod announcements)
                if post_data.get("stickied"):
                    continue

                title = post_data.get("title", "")
                selftext = post_data.get("selftext", "")
                url = post_data.get("url", "")
                permalink = post_data.get("permalink", "")
                post_id = post_data.get("id", "")
                created_utc = post_data.get("created_utc", 0)
                score = post_data.get("score", 0)
                num_comments = post_data.get("num_comments", 0)

                # Build content
                content = selftext if selftext else f"Link post: {url}"
                content = f"{content}\n\nScore: {score} | Comments: {num_comments}"

                # Only include posts with some engagement
                if score < 10:
                    continue

                items.append(ResearchItem(
                    source="reddit",
                    source_id=f"r/{subreddit}:{post_id}",
                    url=f"https://reddit.com{permalink}",
                    title=f"[r/{subreddit}] {title}",
                    content=content[:2000],
                    published_at=datetime.utcfromtimestamp(created_utc) if created_utc else None
                ))

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error getting r/{subreddit}: {e}")
        except Exception as e:
            logger.error(f"Error getting r/{subreddit}: {e}")

        return items

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

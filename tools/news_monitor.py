"""
News Monitor - Automated topic monitoring for David.

Monitors:
- Crypto news (regulation, market moves, adoption)
- Surveillance/control systems (CBDCs, digital IDs, social credit)
- Money printing / Fed policy
- WEF / Agenda 2030 announcements

Uses RSS feeds and web search to surface relevant stories.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """A news item for David to potentially comment on."""
    title: str
    url: str
    source: str
    published: Optional[datetime]
    summary: str
    category: str  # crypto, regulation, surveillance, debasement, wef
    relevance_score: float = 0.0


# RSS feeds by category
RSS_FEEDS = {
    "crypto": [
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Decrypt", "https://decrypt.co/feed"),
        ("The Block", "https://www.theblock.co/rss.xml"),
    ],
    "regulation": [
        ("CoinDesk Policy", "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml&_gl=policy"),
    ],
    "surveillance": [
        ("EFF", "https://www.eff.org/rss/updates.xml"),
        ("Privacy International", "https://privacyinternational.org/rss.xml"),
    ],
}

# Keywords that indicate high relevance to David's mission
RELEVANCE_KEYWORDS = {
    "high": [
        "cbdc", "central bank digital", "digital dollar", "digital euro", "digital yuan",
        "digital id", "digital identity", "vaccine passport", "health pass",
        "social credit", "surveillance", "programmable money",
        "clarity act", "crypto regulation", "sec crypto", "gensler",
        "wef", "world economic forum", "agenda 2030", "great reset",
        "15 minute city", "smart city",
        "money printing", "fed balance sheet", "quantitative easing",
        "bitcoin etf", "crypto ban", "stablecoin regulation",
        "financial surveillance", "transaction monitoring",
        "decentralization", "self custody", "not your keys",
    ],
    "medium": [
        "bitcoin", "ethereum", "cryptocurrency", "blockchain",
        "inflation", "federal reserve", "interest rate",
        "privacy", "tracking", "biometric",
        "regulation", "compliance", "kyc", "aml",
        "blackrock", "institutional", "adoption",
    ],
}


class NewsMonitor:
    """Monitor news sources for David-relevant content."""

    def __init__(self):
        self.brave_api_key = os.environ.get("BRAVE_API_KEY", "")
        self._seen_urls = set()  # Avoid duplicates

    async def fetch_rss_feed(self, name: str, url: str, category: str) -> list[NewsItem]:
        """Fetch and parse an RSS feed."""
        items = []
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url, follow_redirects=True)
                if response.status_code != 200:
                    logger.warning(f"RSS feed {name} returned {response.status_code}")
                    return items

                root = ElementTree.fromstring(response.content)

                # Handle both RSS and Atom feeds
                for item in root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                    title = item.findtext("title") or item.findtext("{http://www.w3.org/2005/Atom}title") or ""
                    link = item.findtext("link") or ""
                    if not link:
                        link_elem = item.find("{http://www.w3.org/2005/Atom}link")
                        if link_elem is not None:
                            link = link_elem.get("href", "")

                    description = (
                        item.findtext("description") or
                        item.findtext("{http://www.w3.org/2005/Atom}summary") or
                        ""
                    )
                    # Clean HTML from description
                    description = re.sub(r'<[^>]+>', '', description)[:500]

                    pub_date = item.findtext("pubDate") or item.findtext("{http://www.w3.org/2005/Atom}published")
                    published = None
                    if pub_date:
                        try:
                            # Try common date formats
                            for fmt in [
                                "%a, %d %b %Y %H:%M:%S %z",
                                "%a, %d %b %Y %H:%M:%S %Z",
                                "%Y-%m-%dT%H:%M:%S%z",
                                "%Y-%m-%dT%H:%M:%SZ",
                            ]:
                                try:
                                    published = datetime.strptime(pub_date.strip(), fmt)
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            pass

                    if title and link and link not in self._seen_urls:
                        self._seen_urls.add(link)
                        news_item = NewsItem(
                            title=title.strip(),
                            url=link,
                            source=name,
                            published=published,
                            summary=description.strip(),
                            category=category,
                        )
                        news_item.relevance_score = self._calculate_relevance(news_item)
                        items.append(news_item)

        except Exception as e:
            logger.error(f"Error fetching RSS feed {name}: {e}")

        return items

    def _calculate_relevance(self, item: NewsItem) -> float:
        """Calculate relevance score based on keywords."""
        text = f"{item.title} {item.summary}".lower()
        score = 0.0

        for keyword in RELEVANCE_KEYWORDS["high"]:
            if keyword in text:
                score += 2.0

        for keyword in RELEVANCE_KEYWORDS["medium"]:
            if keyword in text:
                score += 0.5

        return min(score, 10.0)  # Cap at 10

    async def fetch_all_feeds(self) -> list[NewsItem]:
        """Fetch all RSS feeds concurrently."""
        tasks = []
        for category, feeds in RSS_FEEDS.items():
            for name, url in feeds:
                tasks.append(self.fetch_rss_feed(name, url, category))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)

        # Sort by relevance, then by date
        all_items.sort(key=lambda x: (x.relevance_score, x.published or datetime.min), reverse=True)

        return all_items

    async def search_brave(self, query: str, count: int = 10) -> list[NewsItem]:
        """Search Brave for recent news on a topic."""
        if not self.brave_api_key:
            return []

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/news/search",
                    headers={"X-Subscription-Token": self.brave_api_key},
                    params={
                        "q": query,
                        "count": count,
                        "freshness": "pw",  # Past week
                    },
                )

                if response.status_code != 200:
                    logger.warning(f"Brave search returned {response.status_code}")
                    return []

                data = response.json()
                items = []

                for result in data.get("results", []):
                    url = result.get("url", "")
                    if url not in self._seen_urls:
                        self._seen_urls.add(url)
                        item = NewsItem(
                            title=result.get("title", ""),
                            url=url,
                            source="Brave Search",
                            published=None,
                            summary=result.get("description", "")[:500],
                            category="search",
                        )
                        item.relevance_score = self._calculate_relevance(item)
                        items.append(item)

                return items

        except Exception as e:
            logger.error(f"Brave search error: {e}")
            return []

    async def get_daily_digest(self, max_items: int = 10) -> list[NewsItem]:
        """
        Get a daily digest of relevant news.
        Filters for items from the last 24 hours with high relevance.
        """
        all_items = await self.fetch_all_feeds()

        # Filter for recent and relevant
        cutoff = datetime.now() - timedelta(hours=24)
        recent_relevant = [
            item for item in all_items
            if item.relevance_score >= 1.0
            and (item.published is None or item.published.replace(tzinfo=None) > cutoff)
        ]

        return recent_relevant[:max_items]

    async def search_david_topics(self) -> list[NewsItem]:
        """Search for news on David's key topics."""
        searches = [
            "CBDC central bank digital currency",
            "crypto regulation Clarity Act",
            "digital ID surveillance",
            "Federal Reserve balance sheet",
            "Bitcoin institutional adoption",
        ]

        all_items = []
        for query in searches:
            items = await self.search_brave(query, count=5)
            all_items.extend(items)

        # Dedupe and sort
        seen = set()
        unique = []
        for item in all_items:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)

        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        return unique[:15]

    def format_digest_for_telegram(self, items: list[NewsItem]) -> str:
        """Format news digest for Telegram."""
        if not items:
            return "No relevant news found in the last 24 hours."

        lines = [f"**David's News Digest** ({len(items)} items)\n"]

        for i, item in enumerate(items[:10], 1):
            relevance = "" if item.relevance_score < 2 else ""
            source = item.source[:15]
            title = item.title[:80] + ("..." if len(item.title) > 80 else "")
            lines.append(f"{i}. [{source}] {title} {relevance}")
            lines.append(f"   `/davidnews {i}`\n")

        lines.append("\nReply with number to have David comment.")

        return "\n".join(lines)

    def generate_david_prompt(self, item: NewsItem) -> str:
        """Generate a prompt for David to comment on a news item."""
        return f"""Write a tweet commenting on this news:

HEADLINE: {item.title}

SUMMARY: {item.summary[:300]}

SOURCE: {item.source}

DAVID'S ANGLES:
- If about CBDCs/digital currency: Programmable money, control infrastructure
- If about crypto regulation: Freedom vs control, Clarity Act implications
- If about surveillance/IDs: The infrastructure being built while people sleep
- If about Fed/money printing: The silent tax, debasement math
- If about Bitcoin/decentralization: The escape route, the accident they can't undo

Remember:
- Stay in character as David Flip
- Connect to the bigger picture of control vs freedom
- No price predictions
- Under 280 characters"""

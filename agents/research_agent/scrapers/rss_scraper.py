"""
RSS Feed Scraper - Monitors news feeds for relevant content.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List
from xml.etree import ElementTree

import httpx
import yaml

from ..knowledge_store import ResearchItem

logger = logging.getLogger(__name__)

# Load config
CONFIG_PATH = "config/research_goals.yaml"


class RSSScraper:
    """Scrapes RSS feeds for news and articles."""

    name = "rss"

    def __init__(self):
        self.feeds = self._load_feeds()
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    def _load_feeds(self) -> List[dict]:
        """Load RSS feed configuration."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("sources", {}).get("rss", {}).get("feeds", [])
        except Exception as e:
            logger.error(f"Failed to load RSS config: {e}")
            return []

    async def scrape(self) -> List[ResearchItem]:
        """Scrape all configured RSS feeds."""
        items = []

        tasks = [self._scrape_feed(feed) for feed in self.feeds]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"RSS scrape error: {result}")
            else:
                items.extend(result)

        logger.info(f"RSS scraper found {len(items)} items from {len(self.feeds)} feeds")
        return items

    async def _scrape_feed(self, feed: dict) -> List[ResearchItem]:
        """Scrape a single RSS feed."""
        items = []
        feed_name = feed.get("name", "Unknown")
        feed_url = feed.get("url", "")

        if not feed_url:
            return items

        try:
            response = await self.client.get(feed_url)
            response.raise_for_status()

            # Parse XML
            root = ElementTree.fromstring(response.content)

            # Handle both RSS and Atom formats
            if root.tag == "rss":
                items = self._parse_rss(root, feed_name)
            elif root.tag == "{http://www.w3.org/2005/Atom}feed":
                items = self._parse_atom(root, feed_name)
            else:
                # Try RSS format anyway
                items = self._parse_rss(root, feed_name)

            logger.debug(f"Scraped {len(items)} items from {feed_name}")

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error fetching {feed_name}: {e}")
        except ElementTree.ParseError as e:
            logger.warning(f"XML parse error for {feed_name}: {e}")
        except Exception as e:
            logger.error(f"Error scraping {feed_name}: {e}")

        return items

    def _parse_rss(self, root: ElementTree.Element, source_name: str) -> List[ResearchItem]:
        """Parse RSS 2.0 format."""
        items = []

        for item in root.findall(".//item"):
            title = self._get_text(item, "title")
            link = self._get_text(item, "link")
            description = self._get_text(item, "description")
            pub_date = self._parse_date(self._get_text(item, "pubDate"))
            guid = self._get_text(item, "guid") or link

            if title and link:
                items.append(ResearchItem(
                    source="rss",
                    source_id=f"{source_name}:{guid}",
                    url=link,
                    title=title,
                    content=self._clean_html(description) if description else "",
                    published_at=pub_date
                ))

        return items

    def _parse_atom(self, root: ElementTree.Element, source_name: str) -> List[ResearchItem]:
        """Parse Atom format."""
        items = []
        ns = {"atom": "http://www.w3.org/2005/Atom"}

        for entry in root.findall("atom:entry", ns):
            title = self._get_text(entry, "atom:title", ns)

            # Get link (prefer alternate)
            link = ""
            for link_elem in entry.findall("atom:link", ns):
                href = link_elem.get("href", "")
                rel = link_elem.get("rel", "alternate")
                if rel == "alternate" and href:
                    link = href
                    break
                elif href and not link:
                    link = href

            # Get content or summary
            content = self._get_text(entry, "atom:content", ns)
            if not content:
                content = self._get_text(entry, "atom:summary", ns)

            pub_date = self._parse_date(self._get_text(entry, "atom:published", ns))
            if not pub_date:
                pub_date = self._parse_date(self._get_text(entry, "atom:updated", ns))

            entry_id = self._get_text(entry, "atom:id", ns) or link

            if title and link:
                items.append(ResearchItem(
                    source="rss",
                    source_id=f"{source_name}:{entry_id}",
                    url=link,
                    title=title,
                    content=self._clean_html(content) if content else "",
                    published_at=pub_date
                ))

        return items

    def _get_text(self, element: ElementTree.Element, tag: str,
                  ns: dict = None) -> str:
        """Get text content from an XML element."""
        if ns:
            child = element.find(tag, ns)
        else:
            child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    def _parse_date(self, date_str: str) -> datetime:
        """Parse various date formats."""
        if not date_str:
            return None

        # Common formats
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%a, %d %b %Y %H:%M:%S %Z",  # RFC 822 with timezone name
            "%Y-%m-%dT%H:%M:%S%z",  # ISO 8601
            "%Y-%m-%dT%H:%M:%SZ",  # ISO 8601 UTC
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try without timezone
        try:
            # Remove timezone info and parse
            clean = date_str.split("+")[0].split("Z")[0].strip()
            for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                try:
                    return datetime.strptime(clean, fmt)
                except ValueError:
                    continue
        except Exception:
            pass

        return None

    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""

        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Decode common entities
        clean = clean.replace('&amp;', '&')
        clean = clean.replace('&lt;', '<')
        clean = clean.replace('&gt;', '>')
        clean = clean.replace('&quot;', '"')
        clean = clean.replace('&#39;', "'")
        clean = clean.replace('&nbsp;', ' ')
        # Normalize whitespace
        clean = ' '.join(clean.split())
        return clean[:2000]  # Limit length

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

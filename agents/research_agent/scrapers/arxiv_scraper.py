"""
ArXiv Scraper - Monitors research papers for AI agent breakthroughs.

Uses the ArXiv API (free, no auth needed).
Frequency: DAILY tier.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List
from xml.etree import ElementTree

import httpx
import yaml

from ..knowledge_store import ResearchItem

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/research_goals.yaml"
ARXIV_API = "https://export.arxiv.org/api/query"


class ArXivScraper:
    """Scrapes ArXiv for AI agent research papers."""

    name = "arxiv"
    frequency = "daily"

    def __init__(self):
        self.config = self._load_config()
        self.client = httpx.AsyncClient(timeout=60.0)
        self.categories = self.config.get("categories", ["cs.AI", "cs.CL", "cs.MA"])
        self.keywords = self.config.get("search_keywords", [])
        self.max_per_category = self.config.get("max_results_per_category", 20)
        self.days_back = self.config.get("days_back", 3)

    def _load_config(self) -> dict:
        """Load ArXiv configuration."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("sources", {}).get("arxiv", {})
        except Exception as e:
            logger.error(f"Failed to load ArXiv config: {e}")
            return {}

    async def scrape(self) -> List[ResearchItem]:
        """Scrape ArXiv for recent relevant papers."""
        if not self.config.get("enabled", True):
            return []

        items = []

        for category in self.categories:
            try:
                papers = await self._search_category(category)
                items.extend(papers)
                # ArXiv asks for 3-second delay between requests
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Error scraping ArXiv {category}: {e}")

        logger.info(f"ArXiv scraper found {len(items)} papers from {len(self.categories)} categories")
        return items

    async def _search_category(self, category: str) -> List[ResearchItem]:
        """Search a single ArXiv category for relevant papers."""
        items = []

        # Build query: category + keywords
        keyword_query = " OR ".join(f'all:"{kw}"' for kw in self.keywords)
        query = f"cat:{category} AND ({keyword_query})" if self.keywords else f"cat:{category}"

        params = {
            "search_query": query,
            "start": 0,
            "max_results": self.max_per_category,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            response = await self.client.get(ARXIV_API, params=params)
            response.raise_for_status()

            root = ElementTree.fromstring(response.text)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            cutoff = datetime.utcnow() - timedelta(days=self.days_back)

            for entry in root.findall("atom:entry", ns):
                try:
                    # Title
                    title_el = entry.find("atom:title", ns)
                    title = title_el.text.strip().replace("\n", " ") if title_el is not None and title_el.text else ""

                    # Abstract
                    summary_el = entry.find("atom:summary", ns)
                    abstract = summary_el.text.strip().replace("\n", " ") if summary_el is not None and summary_el.text else ""

                    # ArXiv ID
                    id_el = entry.find("atom:id", ns)
                    arxiv_url = id_el.text.strip() if id_el is not None and id_el.text else ""
                    arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else arxiv_url

                    # Published date
                    pub_el = entry.find("atom:published", ns)
                    published = None
                    if pub_el is not None and pub_el.text:
                        try:
                            published = datetime.fromisoformat(pub_el.text.replace("Z", "+00:00"))
                            if published.replace(tzinfo=None) < cutoff:
                                continue  # Skip old papers
                        except (ValueError, TypeError):
                            pass

                    # Authors
                    authors = []
                    for author_el in entry.findall("atom:author", ns):
                        name_el = author_el.find("atom:name", ns)
                        if name_el is not None and name_el.text:
                            authors.append(name_el.text.strip())
                    author_str = ", ".join(authors[:3])
                    if len(authors) > 3:
                        author_str += f" et al. ({len(authors)} authors)"

                    # PDF link
                    pdf_link = ""
                    for link_el in entry.findall("atom:link", ns):
                        if link_el.get("title") == "pdf":
                            pdf_link = link_el.get("href", "")
                            break

                    if not title:
                        continue

                    content = (
                        f"Authors: {author_str}\n"
                        f"Category: {category}\n"
                        f"PDF: {pdf_link}\n\n"
                        f"Abstract:\n{abstract[:1500]}"
                    )

                    items.append(ResearchItem(
                        source="arxiv",
                        source_id=f"arxiv:{arxiv_id}",
                        url=arxiv_url,
                        title=f"[ArXiv {category}] {title}",
                        content=content,
                        published_at=published,
                    ))

                except Exception as e:
                    logger.debug(f"Error parsing ArXiv entry: {e}")
                    continue

        except httpx.HTTPError as e:
            logger.warning(f"ArXiv API error for {category}: {e}")
        except ElementTree.ParseError as e:
            logger.warning(f"XML parse error for {category}: {e}")
        except Exception as e:
            logger.error(f"Error searching ArXiv {category}: {e}")

        return items

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

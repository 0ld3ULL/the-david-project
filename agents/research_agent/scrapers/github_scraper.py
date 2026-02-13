"""
GitHub Scraper - Monitors repositories for releases, commits, and updates.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import List

import httpx
import yaml

from ..knowledge_store import ResearchItem

logger = logging.getLogger(__name__)

CONFIG_PATH = "config/research_goals.yaml"


class GitHubScraper:
    """Scrapes GitHub repositories for updates."""

    name = "github"

    def __init__(self):
        self.config = self._load_config()
        self.token = os.environ.get("GITHUB_TOKEN", "")
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {self.token}" if self.token else "",
            }
        )

    def _load_config(self) -> dict:
        """Load GitHub configuration."""
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
            return config.get("sources", {}).get("github", {})
        except Exception as e:
            logger.error(f"Failed to load GitHub config: {e}")
            return {}

    async def scrape(self) -> List[ResearchItem]:
        """Scrape all configured GitHub repos."""
        items = []
        repos = self.config.get("repos", [])
        check_releases = self.config.get("check_releases", True)
        check_commits = self.config.get("check_commits", True)

        for repo in repos:
            try:
                if check_releases:
                    releases = await self._get_releases(repo)
                    items.extend(releases)

                if check_commits:
                    commits = await self._get_recent_commits(repo)
                    items.extend(commits)

            except Exception as e:
                logger.error(f"Error scraping {repo}: {e}")

        logger.info(f"GitHub scraper found {len(items)} items from {len(repos)} repos")
        return items

    async def _get_releases(self, repo: str, limit: int = 5) -> List[ResearchItem]:
        """Get recent releases from a repository."""
        items = []
        url = f"https://api.github.com/repos/{repo}/releases"

        try:
            response = await self.client.get(url, params={"per_page": limit})

            if response.status_code == 404:
                logger.debug(f"No releases found for {repo}")
                return items

            response.raise_for_status()
            releases = response.json()

            for release in releases:
                tag = release.get("tag_name", "")
                name = release.get("name", tag)
                body = release.get("body", "")
                html_url = release.get("html_url", "")
                published = release.get("published_at", "")

                items.append(ResearchItem(
                    source="github",
                    source_id=f"{repo}:release:{tag}",
                    url=html_url,
                    title=f"[{repo}] Release {name}",
                    content=body[:2000] if body else f"New release {name} for {repo}",
                    published_at=self._parse_date(published)
                ))

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error getting releases for {repo}: {e}")
        except Exception as e:
            logger.error(f"Error getting releases for {repo}: {e}")

        return items

    async def _get_recent_commits(self, repo: str, days: int = 1) -> List[ResearchItem]:
        """Get commits from the last N days."""
        items = []
        url = f"https://api.github.com/repos/{repo}/commits"
        since = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"

        try:
            response = await self.client.get(url, params={
                "since": since,
                "per_page": 20
            })

            if response.status_code == 404:
                logger.debug(f"Repo not found: {repo}")
                return items

            response.raise_for_status()
            commits = response.json()

            # Group commits by significance (skip merge commits, focus on meaningful ones)
            significant_commits = []
            for commit in commits:
                message = commit.get("commit", {}).get("message", "")
                # Skip merge commits and trivial updates
                if message.startswith("Merge "):
                    continue
                if len(message) < 20:
                    continue
                significant_commits.append(commit)

            # Only report if there are multiple significant commits (indicates active development)
            if len(significant_commits) >= 3:
                # Summarize the commits
                sha = significant_commits[0].get("sha", "")[:7]
                messages = [c.get("commit", {}).get("message", "").split("\n")[0]
                           for c in significant_commits[:5]]
                content = f"{len(significant_commits)} commits in last {days} day(s):\n" + "\n".join(f"- {m}" for m in messages)

                items.append(ResearchItem(
                    source="github",
                    source_id=f"{repo}:commits:{sha}",
                    url=f"https://github.com/{repo}/commits",
                    title=f"[{repo}] Active development ({len(significant_commits)} commits)",
                    content=content,
                    published_at=datetime.utcnow()
                ))

        except httpx.HTTPError as e:
            logger.warning(f"HTTP error getting commits for {repo}: {e}")
        except Exception as e:
            logger.error(f"Error getting commits for {repo}: {e}")

        return items

    def _parse_date(self, date_str: str) -> datetime:
        """Parse GitHub date format."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

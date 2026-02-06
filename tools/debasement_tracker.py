"""
Debasement Tracker - Money supply monitoring.

Tracks Federal Reserve balance sheet, M2 money supply, and calculates
the real-time erosion of purchasing power. David's cold math.

Sources:
- FRED (Federal Reserve Economic Data) - free API
- US Debt Clock data
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# FRED API (Federal Reserve Economic Data)
FRED_API_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Key series we track
SERIES = {
    "M2SL": "M2 Money Supply (Seasonally Adjusted)",
    "WALCL": "Federal Reserve Total Assets",
    "BOGMBASE": "Monetary Base",
}


class DebasementTracker:
    """Track money printing and calculate purchasing power erosion."""

    def __init__(self):
        self.fred_api_key = os.environ.get("FRED_API_KEY", "")
        self._cache = {}
        self._cache_time = None

    async def get_m2_money_supply(self) -> dict:
        """
        Get M2 money supply data.

        Returns latest value, change from last week/month/year.
        """
        if not self.fred_api_key:
            return {"error": "FRED_API_KEY not configured"}

        try:
            async with httpx.AsyncClient() as client:
                # Get last 2 years of weekly data
                params = {
                    "series_id": "M2SL",
                    "api_key": self.fred_api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 104,  # ~2 years of weekly data
                }
                response = await client.get(FRED_API_BASE, params=params)
                data = response.json()

                if "observations" not in data:
                    return {"error": "No data returned from FRED"}

                observations = data["observations"]
                if len(observations) < 2:
                    return {"error": "Insufficient data"}

                # Latest value
                latest = float(observations[0]["value"])
                latest_date = observations[0]["date"]

                # Find comparison points
                week_ago = None
                month_ago = None
                year_ago = None

                for obs in observations:
                    obs_date = datetime.strptime(obs["date"], "%Y-%m-%d")
                    latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
                    days_diff = (latest_dt - obs_date).days

                    if week_ago is None and days_diff >= 7:
                        week_ago = float(obs["value"])
                    if month_ago is None and days_diff >= 30:
                        month_ago = float(obs["value"])
                    if year_ago is None and days_diff >= 365:
                        year_ago = float(obs["value"])

                return {
                    "series": "M2 Money Supply",
                    "latest_value": latest,
                    "latest_date": latest_date,
                    "unit": "Billions USD",
                    "week_change": latest - week_ago if week_ago else None,
                    "week_change_pct": ((latest - week_ago) / week_ago * 100) if week_ago else None,
                    "month_change": latest - month_ago if month_ago else None,
                    "month_change_pct": ((latest - month_ago) / month_ago * 100) if month_ago else None,
                    "year_change": latest - year_ago if year_ago else None,
                    "year_change_pct": ((latest - year_ago) / year_ago * 100) if year_ago else None,
                }

        except Exception as e:
            logger.error(f"Failed to fetch M2 data: {e}")
            return {"error": str(e)}

    async def get_fed_balance_sheet(self) -> dict:
        """Get Federal Reserve total assets (balance sheet size)."""
        if not self.fred_api_key:
            return {"error": "FRED_API_KEY not configured"}

        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "series_id": "WALCL",
                    "api_key": self.fred_api_key,
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 104,
                }
                response = await client.get(FRED_API_BASE, params=params)
                data = response.json()

                if "observations" not in data:
                    return {"error": "No data returned"}

                observations = data["observations"]
                latest = float(observations[0]["value"])
                latest_date = observations[0]["date"]

                # Year ago comparison
                year_ago = None
                for obs in observations:
                    obs_date = datetime.strptime(obs["date"], "%Y-%m-%d")
                    latest_dt = datetime.strptime(latest_date, "%Y-%m-%d")
                    if (latest_dt - obs_date).days >= 365:
                        year_ago = float(obs["value"])
                        break

                return {
                    "series": "Fed Balance Sheet",
                    "latest_value": latest,
                    "latest_date": latest_date,
                    "unit": "Millions USD",
                    "year_change": latest - year_ago if year_ago else None,
                    "year_change_pct": ((latest - year_ago) / year_ago * 100) if year_ago else None,
                }

        except Exception as e:
            logger.error(f"Failed to fetch Fed balance sheet: {e}")
            return {"error": str(e)}

    def calculate_purchasing_power_loss(
        self,
        money_supply_change_pct: float,
        your_savings: float = 10000,
    ) -> dict:
        """
        Calculate how much purchasing power was lost.

        Simple model: If money supply increased X%, your dollars
        are worth X% less (all else equal).
        """
        loss_pct = money_supply_change_pct
        loss_amount = your_savings * (loss_pct / 100)

        return {
            "original_savings": your_savings,
            "purchasing_power_loss_pct": loss_pct,
            "purchasing_power_loss_amount": loss_amount,
            "effective_value": your_savings - loss_amount,
        }

    async def generate_debasement_report(self) -> dict:
        """
        Generate a full debasement report for David to comment on.
        """
        m2_data = await self.get_m2_money_supply()
        fed_data = await self.get_fed_balance_sheet()

        report = {
            "generated_at": datetime.now().isoformat(),
            "m2_money_supply": m2_data,
            "fed_balance_sheet": fed_data,
        }

        # Calculate impact on $10,000 savings
        if m2_data.get("year_change_pct"):
            report["impact_on_savings"] = self.calculate_purchasing_power_loss(
                m2_data["year_change_pct"],
                your_savings=10000,
            )

        return report

    def format_for_david(self, report: dict) -> str:
        """
        Format debasement report as a prompt for David to comment on.
        """
        lines = ["**Debasement Report**\n"]

        m2 = report.get("m2_money_supply", {})
        if not m2.get("error"):
            lines.append(f"M2 Money Supply: ${m2.get('latest_value', 0):,.0f} billion")
            if m2.get("week_change"):
                sign = "+" if m2["week_change"] > 0 else ""
                lines.append(f"  Week change: {sign}${m2['week_change']:,.0f}B ({sign}{m2['week_change_pct']:.2f}%)")
            if m2.get("year_change"):
                sign = "+" if m2["year_change"] > 0 else ""
                lines.append(f"  Year change: {sign}${m2['year_change']:,.0f}B ({sign}{m2['year_change_pct']:.2f}%)")

        fed = report.get("fed_balance_sheet", {})
        if not fed.get("error"):
            # Convert millions to trillions for readability
            value_t = fed.get("latest_value", 0) / 1_000_000
            lines.append(f"\nFed Balance Sheet: ${value_t:.2f} trillion")
            if fed.get("year_change"):
                change_t = fed["year_change"] / 1_000_000
                sign = "+" if change_t > 0 else ""
                lines.append(f"  Year change: {sign}${change_t:.2f}T ({sign}{fed['year_change_pct']:.1f}%)")

        impact = report.get("impact_on_savings", {})
        if impact:
            lines.append(f"\nImpact on $10,000 savings (past year):")
            lines.append(f"  Lost purchasing power: ${impact['purchasing_power_loss_amount']:.2f}")
            lines.append(f"  Effective value: ${impact['effective_value']:,.2f}")

        return "\n".join(lines)

    def generate_david_tweet_prompt(self, report: dict) -> str:
        """Generate a prompt for David to tweet about the debasement data."""
        m2 = report.get("m2_money_supply", {})
        impact = report.get("impact_on_savings", {})

        if m2.get("error"):
            return None

        week_change = m2.get("week_change", 0)
        week_pct = m2.get("week_change_pct", 0)
        year_pct = m2.get("year_change_pct", 0)
        loss = impact.get("purchasing_power_loss_amount", 0) if impact else 0

        prompt = f"""Write a tweet about money printing and debasement.

DATA:
- M2 money supply changed ${week_change:+,.0f} billion this week ({week_pct:+.2f}%)
- Year-over-year money supply change: {year_pct:+.1f}%
- Someone with $10,000 in savings lost ${loss:.2f} in purchasing power this year

ANGLE OPTIONS (pick one):
1. The cold math of how printing steals from savers
2. "The tax nobody votes for"
3. Why this is why Bitcoin/decentralization matters
4. Connect to control systems - they don't need to take your money directly

Remember: No price predictions, no financial advice. Just truth."""

        return prompt

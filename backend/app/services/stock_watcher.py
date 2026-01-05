"""Stock Watcher client for House and Senate stock trades.

This module fetches congressional stock trade data from:
1. Stock Watcher APIs (primary - when available)
2. GitHub historical data (fallback - reliable historical data)

For official government disclosures, users should visit the official sites directly:
- Senate: https://efdsearch.senate.gov/search/home/
- House: https://disclosures-clerk.house.gov/FinancialDisclosure
"""

import httpx
from datetime import datetime

# Third-party APIs (may be down)
HOUSE_STOCK_WATCHER_URL = "https://housestockwatcher.com/api/all-transactions"
SENATE_STOCK_WATCHER_URL = "https://senatestockwatcher.com/api/all-transactions"

# GitHub fallback for Senate data (historical data from 2020-2021)
SENATE_GITHUB_FALLBACK_URL = "https://raw.githubusercontent.com/timothycarambat/senate-stock-watcher-data/master/aggregate/all_transactions.json"


class StockWatcherClient:
    """Client for fetching House and Senate stock trade data.

    Data sources:
    1. Stock Watcher APIs (housestockwatcher.com, senatestockwatcher.com)
    2. GitHub historical data (fallback)
    """

    def __init__(self):
        """Initialize the client."""
        pass

    async def _fetch_json(self, url: str, timeout: float = 60.0) -> list[dict]:
        """Fetch JSON data from a URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            return response.json()

    async def get_house_trades(self) -> list[dict]:
        """
        Get all House stock trades from Stock Watcher API.

        Returns:
            List of trade dictionaries
        """
        try:
            data = await self._fetch_json(HOUSE_STOCK_WATCHER_URL)
            print(f"House Stock Watcher API returned {len(data)} trades")
            return [transform_house_trade(t) for t in data if isinstance(t, dict)]
        except Exception as e:
            print(f"House Stock Watcher API failed: {e}")
            return []

    async def get_senate_trades(self) -> list[dict]:
        """
        Get all Senate stock trades.

        Data source priority:
        1. Senate Stock Watcher API
        2. GitHub historical data (fallback)

        Returns:
            List of trade dictionaries
        """
        # Try Stock Watcher API first
        try:
            data = await self._fetch_json(SENATE_STOCK_WATCHER_URL)
            print(f"Senate Stock Watcher API returned {len(data)} trades")
            return [transform_senate_trade(t) for t in data if isinstance(t, dict)]
        except Exception as e:
            print(f"Senate Stock Watcher API failed: {e}")

        # Try GitHub fallback
        try:
            print("Trying GitHub fallback for Senate trades...")
            data = await self._fetch_json(SENATE_GITHUB_FALLBACK_URL, timeout=30.0)
            print(f"GitHub fallback returned {len(data)} Senate trades")
            return [transform_github_senate_trade(t) for t in data if isinstance(t, dict)]
        except Exception as e:
            print(f"GitHub fallback also failed: {e}")
            return []

    async def get_all_trades(self) -> list[dict]:
        """
        Get all stock trades from both House and Senate.

        Returns:
            Combined list of trade dictionaries
        """
        house_trades = await self.get_house_trades()
        senate_trades = await self.get_senate_trades()
        return house_trades + senate_trades


def transform_github_senate_trade(trade: dict) -> dict:
    """Transform GitHub Senate Stock Watcher trade to our schema."""
    return {
        "representative": trade.get("senator", ""),
        "chamber": "senate",
        "transaction_date": _parse_date(trade.get("transaction_date")),
        "disclosure_date": None,  # Not in GitHub data
        "ticker": trade.get("ticker"),
        "asset_description": trade.get("asset_description"),
        "transaction_type": _normalize_transaction_type(trade.get("type")),
        "amount_range": trade.get("amount"),
        "amount_min": _parse_amount_min(trade.get("amount")),
        "amount_max": _parse_amount_max(trade.get("amount")),
        "filing_url": trade.get("ptr_link"),
    }


def transform_house_trade(trade: dict) -> dict:
    """Transform House Stock Watcher trade to our schema."""
    return {
        "representative": trade.get("representative", ""),
        "chamber": "house",
        "transaction_date": _parse_date(trade.get("transaction_date")),
        "disclosure_date": _parse_date(trade.get("disclosure_date")),
        "ticker": trade.get("ticker"),
        "asset_description": trade.get("asset_description"),
        "transaction_type": _normalize_transaction_type(trade.get("type")),
        "amount_range": trade.get("amount"),
        "amount_min": _parse_amount_min(trade.get("amount")),
        "amount_max": _parse_amount_max(trade.get("amount")),
        "filing_url": trade.get("ptr_link"),
    }


def transform_senate_trade(trade: dict) -> dict:
    """Transform Senate Stock Watcher trade to our schema."""
    return {
        "representative": trade.get("senator", ""),
        "chamber": "senate",
        "transaction_date": _parse_date(trade.get("transaction_date")),
        "disclosure_date": _parse_date(trade.get("disclosure_date")),
        "ticker": trade.get("ticker"),
        "asset_description": trade.get("asset_description"),
        "transaction_type": _normalize_transaction_type(trade.get("type")),
        "amount_range": trade.get("amount"),
        "amount_min": _parse_amount_min(trade.get("amount")),
        "amount_max": _parse_amount_max(trade.get("amount")),
        "filing_url": trade.get("ptr_link"),
    }


def _parse_date(date_str: str | None) -> str | None:
    """Parse date string to ISO format."""
    if not date_str:
        return None

    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue

    return None


def _normalize_transaction_type(type_str: str | None) -> str:
    """Normalize transaction type to standard values."""
    if not type_str:
        return "unknown"

    type_lower = type_str.lower()
    if "purchase" in type_lower or "buy" in type_lower:
        return "purchase"
    elif "sale" in type_lower or "sell" in type_lower:
        return "sale"
    elif "exchange" in type_lower:
        return "exchange"

    return "unknown"


# Amount range parsing
AMOUNT_RANGES = {
    "$1,001 - $15,000": (1001, 15000),
    "$15,001 - $50,000": (15001, 50000),
    "$50,001 - $100,000": (50001, 100000),
    "$100,001 - $250,000": (100001, 250000),
    "$250,001 - $500,000": (250001, 500000),
    "$500,001 - $1,000,000": (500001, 1000000),
    "$1,000,001 - $5,000,000": (1000001, 5000000),
    "$5,000,001 - $25,000,000": (5000001, 25000000),
    "$25,000,001 - $50,000,000": (25000001, 50000000),
    "Over $50,000,000": (50000001, 100000000),
}


def _parse_amount_min(amount_str: str | None) -> int | None:
    """Parse minimum amount from range string."""
    if not amount_str:
        return None

    for range_str, (min_val, _) in AMOUNT_RANGES.items():
        if range_str.lower() in amount_str.lower():
            return min_val

    return None


def _parse_amount_max(amount_str: str | None) -> int | None:
    """Parse maximum amount from range string."""
    if not amount_str:
        return None

    for range_str, (_, max_val) in AMOUNT_RANGES.items():
        if range_str.lower() in amount_str.lower():
            return max_val

    return None


def match_trade_to_politician(trade: dict, politicians: list[dict]) -> str | None:
    """
    Match a trade to a politician by name.

    Args:
        trade: Trade dictionary with 'representative' field
        politicians: List of politician dictionaries

    Returns:
        Politician ID if matched, None otherwise
    """
    trade_name = trade.get("representative", "").lower()
    if not trade_name:
        return None

    for politician in politicians:
        full_name = f"{politician['first_name']} {politician['last_name']}".lower()
        last_name = politician["last_name"].lower()

        if full_name in trade_name or trade_name in full_name:
            return politician["id"]
        if last_name in trade_name:
            return politician["id"]

    return None

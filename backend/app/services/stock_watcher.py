"""Stock Watcher scraper for House and Senate stock trades."""

import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

HOUSE_STOCK_WATCHER_URL = "https://housestockwatcher.com/api/all-transactions"
SENATE_STOCK_WATCHER_URL = "https://senatestockwatcher.com/api/all-transactions"


class StockWatcherClient:
    """Client for scraping House and Senate stock trade data."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_json(self, url: str) -> list[dict]:
        """Fetch JSON data from Stock Watcher API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            return response.json()

    async def get_house_trades(self) -> list[dict]:
        """
        Get all House stock trades.

        Returns:
            List of trade dictionaries
        """
        try:
            data = await self._fetch_json(HOUSE_STOCK_WATCHER_URL)
            return [transform_house_trade(t) for t in data if isinstance(t, dict)]
        except Exception:
            return []

    async def get_senate_trades(self) -> list[dict]:
        """
        Get all Senate stock trades.

        Returns:
            List of trade dictionaries
        """
        try:
            data = await self._fetch_json(SENATE_STOCK_WATCHER_URL)
            return [transform_senate_trade(t) for t in data if isinstance(t, dict)]
        except Exception:
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

"""Celery task to refresh stock trade data from Stock Watcher."""

import asyncio
import uuid
from datetime import datetime
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Politician, StockTrade
from app.services.stock_watcher import StockWatcherClient, match_trade_to_politician


@celery_app.task(name="app.tasks.refresh_stocks.refresh_all_stocks")
def refresh_all_stocks():
    """Refresh stock trade data from House and Senate Stock Watcher."""
    return asyncio.run(_refresh_all_stocks_async())


async def _refresh_all_stocks_async():
    """Async implementation of stock refresh."""
    client = StockWatcherClient()
    db = SessionLocal()

    try:
        added = 0
        skipped = 0

        # Get all current politicians for matching
        politicians = db.query(Politician).filter(Politician.in_office == True).all()
        politicians_data = [
            {
                "id": str(p.id),
                "first_name": p.first_name,
                "last_name": p.last_name,
                "chamber": p.chamber,
            }
            for p in politicians
        ]

        # Fetch all trades
        trades = await client.get_all_trades()

        for trade in trades:
            # Match trade to politician
            politician_id = match_trade_to_politician(trade, politicians_data)
            if not politician_id:
                skipped += 1
                continue

            # Parse dates
            transaction_date = _parse_date(trade.get("transaction_date"))
            disclosure_date = _parse_date(trade.get("disclosure_date"))

            if not transaction_date or not disclosure_date:
                skipped += 1
                continue

            # Check for existing trade (avoid duplicates)
            existing = db.query(StockTrade).filter(
                StockTrade.politician_id == politician_id,
                StockTrade.transaction_date == transaction_date,
                StockTrade.ticker == trade.get("ticker"),
                StockTrade.amount_range == trade.get("amount_range"),
            ).first()

            if existing:
                skipped += 1
                continue

            # Create new stock trade
            stock_trade = StockTrade(
                id=uuid.uuid4(),
                politician_id=politician_id,
                transaction_date=transaction_date,
                disclosure_date=disclosure_date,
                ticker=trade.get("ticker"),
                asset_description=trade.get("asset_description"),
                transaction_type=trade.get("transaction_type"),
                amount_range=trade.get("amount_range"),
                amount_min=trade.get("amount_min"),
                amount_max=trade.get("amount_max"),
                filing_url=trade.get("filing_url"),
            )
            db.add(stock_trade)
            added += 1

        db.commit()
        return {"trades_added": added, "trades_skipped": skipped}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def _parse_date(date_str: str | None) -> datetime | None:
    """Parse date string to date object."""
    if not date_str:
        return None

    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None

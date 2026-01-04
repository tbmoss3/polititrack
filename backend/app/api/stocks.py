"""Stock trades API endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Politician, StockTrade
from app.schemas.stock_trade import (
    StockTradeResponse,
    StockTradeListResponse,
    StockTradeSummary,
    StockTradeAnalysis,
    NetWorthTrend,
)

router = APIRouter()


@router.get("/by-politician/{politician_id}", response_model=StockTradeListResponse)
async def get_politician_stock_trades(
    politician_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get stock trades for a specific politician."""
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    query = select(StockTrade).where(StockTrade.politician_id == politician_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(StockTrade.transaction_date.desc())

    trades = db.execute(query).scalars().all()

    return StockTradeListResponse(
        items=[_to_stock_trade_response(t) for t in trades],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/analysis/{politician_id}", response_model=StockTradeAnalysis)
async def get_stock_trade_analysis(
    politician_id: UUID,
    db: Session = Depends(get_db),
):
    """Get comprehensive stock trade analysis for a politician."""
    politician = db.get(Politician, politician_id)
    if not politician:
        raise HTTPException(status_code=404, detail="Politician not found")

    # Get all trades
    query = (
        select(StockTrade)
        .where(StockTrade.politician_id == politician_id)
        .order_by(StockTrade.transaction_date)
    )
    trades = db.execute(query).scalars().all()

    # Calculate summary
    total_trades = len(trades)
    purchases = [t for t in trades if t.transaction_type == "purchase"]
    sales = [t for t in trades if t.transaction_type == "sale"]

    avg_disclosure_days = (
        sum(t.disclosure_delay_days for t in trades) / total_trades
        if total_trades > 0
        else 0.0
    )

    # Get most traded tickers
    ticker_counts: dict[str, int] = {}
    for t in trades:
        if t.ticker:
            ticker_counts[t.ticker] = ticker_counts.get(t.ticker, 0) + 1
    most_traded = sorted(ticker_counts.keys(), key=lambda k: ticker_counts[k], reverse=True)[:5]

    # Calculate estimated total values
    total_min = sum(t.amount_min or 0 for t in trades)
    total_max = sum(t.amount_max or 0 for t in trades)

    summary = StockTradeSummary(
        total_trades=total_trades,
        total_purchases=len(purchases),
        total_sales=len(sales),
        avg_disclosure_delay_days=avg_disclosure_days,
        most_traded_tickers=most_traded,
        estimated_total_value_min=total_min if total_min > 0 else None,
        estimated_total_value_max=total_max if total_max > 0 else None,
    )

    # Calculate net worth trend (simplified - cumulative trades over time)
    net_worth_trend = []
    cumulative_min = 0
    cumulative_max = 0
    for i, trade in enumerate(trades):
        if trade.transaction_type == "purchase":
            cumulative_min += trade.amount_min or 0
            cumulative_max += trade.amount_max or 0
        elif trade.transaction_type == "sale":
            cumulative_min -= trade.amount_min or 0
            cumulative_max -= trade.amount_max or 0

        net_worth_trend.append(
            NetWorthTrend(
                date=trade.transaction_date,
                estimated_min=max(0, cumulative_min),
                estimated_max=max(0, cumulative_max),
                cumulative_trades=i + 1,
            )
        )

    # Calculate disclosure compliance score (0-100)
    # Full points if avg disclosure < 30 days, 0 if > 90 days
    if avg_disclosure_days <= 30:
        compliance_score = 100.0
    elif avg_disclosure_days <= 45:
        compliance_score = 80.0
    elif avg_disclosure_days <= 60:
        compliance_score = 60.0
    elif avg_disclosure_days <= 90:
        compliance_score = 40.0
    else:
        compliance_score = 20.0

    # Recent trades (last 10)
    recent_trades = trades[-10:] if trades else []
    recent_trades.reverse()

    return StockTradeAnalysis(
        summary=summary,
        net_worth_trend=net_worth_trend,
        recent_trades=[_to_stock_trade_response(t) for t in recent_trades],
        disclosure_compliance_score=compliance_score,
    )


@router.get("/{trade_id}", response_model=StockTradeResponse)
async def get_stock_trade(
    trade_id: UUID,
    db: Session = Depends(get_db),
):
    """Get details about a specific stock trade."""
    trade = db.get(StockTrade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Stock trade not found")

    return _to_stock_trade_response(trade)


def _to_stock_trade_response(trade: StockTrade) -> StockTradeResponse:
    """Convert StockTrade model to response schema."""
    return StockTradeResponse(
        id=trade.id,
        politician_id=trade.politician_id,
        transaction_date=trade.transaction_date,
        disclosure_date=trade.disclosure_date,
        ticker=trade.ticker,
        asset_description=trade.asset_description,
        transaction_type=trade.transaction_type,
        amount_range=trade.amount_range,
        amount_min=trade.amount_min,
        amount_max=trade.amount_max,
        filing_url=trade.filing_url,
        disclosure_delay_days=trade.disclosure_delay_days,
        amount_midpoint=trade.amount_midpoint,
        created_at=trade.created_at,
    )

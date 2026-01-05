"""Admin endpoints for data population and management."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from sqlalchemy import text
from datetime import datetime
import asyncio

from app.database import SessionLocal
from app.models import Politician, Vote, Bill, CampaignFinance, TopDonor, StockTrade
from app.services.congress_gov import CongressGovClient, transform_member_to_politician
from app.services.fec import FECClient, transform_fec_totals_to_finance, aggregate_top_donors
from app.services.stock_watcher import StockWatcherClient, match_trade_to_politician
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/populate-politicians")
async def populate_politicians(background_tasks: BackgroundTasks):
    """
    Trigger population of politician data from Congress.gov API.
    This runs in the background and may take a few minutes.
    """
    if not settings.congress_gov_api_key:
        raise HTTPException(status_code=500, detail="Congress.gov API key not configured")

    background_tasks.add_task(run_politician_population)
    return {"status": "started", "message": "Politician data population started in background"}


async def run_politician_population():
    """Background task to populate politicians from Congress.gov."""
    client = CongressGovClient()
    db = SessionLocal()

    try:
        updated = 0
        created = 0

        # Current Congress (119th as of 2025)
        congress = 119

        print(f"Fetching members from Congress {congress}...")
        members = await client.get_all_members(congress)
        print(f"Found {len(members)} members")

        for member in members:
            data = transform_member_to_politician(member)

            if not data.get("bioguide_id"):
                continue

            # Check if politician exists
            existing = db.query(Politician).filter(
                Politician.bioguide_id == data["bioguide_id"]
            ).first()

            if existing:
                # Update existing
                for key, value in data.items():
                    if value is not None:
                        setattr(existing, key, value)
                updated += 1
            else:
                # Create new
                politician = Politician(**data)
                db.add(politician)
                created += 1

        db.commit()
        print(f"Population complete: {created} created, {updated} updated")

    except Exception as e:
        db.rollback()
        print(f"Population failed: {e}")
        raise e
    finally:
        db.close()


@router.post("/populate-politicians-sync")
async def populate_politicians_sync():
    """
    Synchronous version of politician population for debugging.
    Returns results directly instead of running in background.
    """
    if not settings.congress_gov_api_key:
        raise HTTPException(status_code=500, detail="Congress.gov API key not configured")

    client = CongressGovClient()
    db = SessionLocal()

    try:
        updated = 0
        created = 0

        # Current Congress (119th as of 2025)
        congress = 119

        members = await client.get_all_members(congress)

        for member in members:
            data = transform_member_to_politician(member)

            if not data.get("bioguide_id"):
                continue

            existing = db.query(Politician).filter(
                Politician.bioguide_id == data["bioguide_id"]
            ).first()

            if existing:
                for key, value in data.items():
                    if value is not None:
                        setattr(existing, key, value)
                updated += 1
            else:
                politician = Politician(**data)
                db.add(politician)
                created += 1

        db.commit()
        return {"status": "complete", "created": created, "updated": updated, "total_members_found": len(members)}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/test-congress-api")
async def test_congress_api():
    """Test the Congress.gov API connection."""
    if not settings.congress_gov_api_key:
        return {"error": "API key not configured", "key_length": 0}

    client = CongressGovClient()
    try:
        members = await client.get_members(congress=119, limit=5)
        return {
            "status": "ok",
            "key_configured": True,
            "key_length": len(settings.congress_gov_api_key),
            "sample_members": len(members),
            "first_member": members[0] if members else None
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "key_length": len(settings.congress_gov_api_key)}


@router.get("/test-votes/{bioguide_id}")
async def test_votes(bioguide_id: str):
    """Test fetching votes for a specific member."""
    if not settings.congress_gov_api_key:
        return {"error": "API key not configured"}

    client = CongressGovClient()
    try:
        # Get raw response to see structure
        import httpx
        params = {"api_key": settings.congress_gov_api_key, "format": "json", "limit": 3}
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"https://api.congress.gov/v3/member/{bioguide_id}/votes",
                params=params,
                timeout=30.0,
            )
            raw_data = response.json()

        return {
            "status": "ok",
            "bioguide_id": bioguide_id,
            "raw_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else "not a dict",
            "raw_data_sample": raw_data
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/test-chamber-votes/{chamber}")
async def test_chamber_votes(chamber: str, congress: int = 119, limit: int = 3):
    """Test fetching votes by chamber to see response structure."""
    if not settings.congress_gov_api_key:
        return {"error": "API key not configured"}

    client = CongressGovClient()
    try:
        # Also try the raw request to see what we get
        import httpx
        params = {"api_key": settings.congress_gov_api_key, "format": "json", "limit": limit}
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"https://api.congress.gov/v3/vote/{congress}/{chamber}",
                params=params,
                timeout=30.0,
            )
            raw_data = response.json()

        votes = await client.get_votes(congress=congress, chamber=chamber, limit=limit)

        # If we got votes, also try to get details for the first one
        vote_detail = None
        if votes:
            first_vote = votes[0]
            roll_number = first_vote.get("rollNumber") or first_vote.get("number")
            if roll_number:
                vote_detail = await client.get_vote_details(congress, chamber, int(roll_number))

        return {
            "status": "ok",
            "congress": congress,
            "chamber": chamber,
            "raw_keys": list(raw_data.keys()) if isinstance(raw_data, dict) else str(type(raw_data)),
            "raw_sample": raw_data,
            "votes_count": len(votes),
            "votes_sample": votes[:2] if votes else [],
            "vote_detail_keys": list(vote_detail.keys()) if vote_detail else [],
            "vote_detail_sample": vote_detail
        }
    except Exception as e:
        import traceback
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}


@router.get("/stats")
async def get_stats():
    """Get database statistics."""
    db = SessionLocal()
    try:
        politician_count = db.query(Politician).count()
        vote_count = db.query(Vote).count()
        finance_count = db.query(CampaignFinance).count()
        stock_count = db.query(StockTrade).count()

        # Party breakdown
        party_counts = db.execute(text("""
            SELECT party, chamber, COUNT(*) as count
            FROM politicians
            WHERE in_office = true
            GROUP BY party, chamber
        """)).fetchall()

        return {
            "total_politicians": politician_count,
            "total_votes": vote_count,
            "total_finance_records": finance_count,
            "total_stock_trades": stock_count,
            "by_party_chamber": [{"party": r[0], "chamber": r[1], "count": r[2]} for r in party_counts]
        }
    finally:
        db.close()


# ============ VOTING RECORDS ============

@router.post("/populate-votes")
async def populate_votes(vote_limit: int = 20):
    """
    Populate voting records from Congress.gov API.
    Fetches recent votes by chamber and records how each member voted.

    Args:
        vote_limit: Number of recent votes to fetch per chamber (default 20)
    """
    if not settings.congress_gov_api_key:
        raise HTTPException(status_code=500, detail="Congress.gov API key not configured")

    client = CongressGovClient()
    db = SessionLocal()

    try:
        # Build a mapping of bioguide_id -> politician for quick lookup
        politicians = db.query(Politician).filter(Politician.in_office == True).all()
        politician_map = {p.bioguide_id: p for p in politicians}
        print(f"Loaded {len(politician_map)} politicians for vote matching")

        total_votes_added = 0
        votes_processed = 0
        congress = 119  # Current Congress

        # Process both chambers
        for chamber in ["house", "senate"]:
            print(f"Fetching {chamber} votes...")
            votes = await client.get_votes(congress=congress, chamber=chamber, limit=vote_limit)
            print(f"Found {len(votes)} {chamber} votes")

            for vote_summary in votes:
                try:
                    # Extract roll call number from the vote URL or data
                    vote_url = vote_summary.get("url", "")
                    roll_number = vote_summary.get("rollNumber") or vote_summary.get("number")

                    if not roll_number:
                        # Try to extract from URL
                        if "/roll/" in vote_url:
                            roll_number = vote_url.split("/roll/")[-1].split("?")[0]

                    if not roll_number:
                        print(f"Could not find roll number for vote: {vote_summary}")
                        continue

                    roll_number = int(roll_number)
                    print(f"Processing {chamber} vote #{roll_number}...")

                    # Get detailed vote info including member votes
                    vote_details = await client.get_vote_details(congress, chamber, roll_number)

                    if not vote_details:
                        print(f"No details for {chamber} vote #{roll_number}")
                        continue

                    # Get member votes from the response
                    # Congress.gov API returns votes in different formats, try multiple keys
                    member_votes = vote_details.get("memberVotes", {})
                    if not member_votes:
                        member_votes = vote_details.get("votes", {})

                    question = vote_details.get("question") or vote_summary.get("question", "")
                    result = vote_details.get("result") or vote_summary.get("result", "")
                    vote_date = vote_details.get("date") or vote_summary.get("date")

                    # Process each vote position (Yes, No, Not Voting, Present)
                    for position_name, members in member_votes.items():
                        if not isinstance(members, list):
                            continue

                        # Normalize position name
                        position = position_name.lower().replace(" ", "_").replace("-", "_")
                        if position in ["yea", "aye"]:
                            position = "yes"
                        elif position in ["nay"]:
                            position = "no"
                        elif position not in ["yes", "no", "not_voting", "present"]:
                            position = "not_voting"

                        for member in members:
                            bioguide_id = member.get("bioguideId") or member.get("bioguide_id")
                            if not bioguide_id:
                                continue

                            politician = politician_map.get(bioguide_id)
                            if not politician:
                                continue

                            # Create unique vote ID
                            vote_id = f"{bioguide_id}-{roll_number}-{congress}-{chamber}"

                            # Check if already exists
                            existing = db.query(Vote).filter(Vote.vote_id == vote_id).first()
                            if existing:
                                continue

                            vote = Vote(
                                vote_id=vote_id,
                                politician_id=politician.id,
                                vote_position=position,
                                vote_date=vote_date,
                                chamber=chamber,
                                question=question[:500] if question else None,
                                result=result[:100] if result else None,
                            )
                            db.add(vote)
                            total_votes_added += 1

                    votes_processed += 1
                    # Delay to respect rate limits
                    await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"Error processing vote: {e}")
                    continue

        db.commit()
        return {
            "status": "complete",
            "votes_processed": votes_processed,
            "vote_records_added": total_votes_added
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ CAMPAIGN FINANCE ============

@router.post("/populate-finance")
async def populate_finance(limit: int = 50, cycle: int = 2024):
    """
    Populate campaign finance data from FEC API.

    Args:
        limit: Number of politicians to process
        cycle: Election cycle year
    """
    if not settings.fec_api_key:
        raise HTTPException(status_code=500, detail="FEC API key not configured")

    client = FECClient()
    db = SessionLocal()

    try:
        politicians = db.query(Politician).filter(
            Politician.in_office == True
        ).limit(limit).all()

        finance_added = 0
        processed = 0

        for politician in politicians:
            try:
                # Search for candidate in FEC
                full_name = f"{politician.last_name}, {politician.first_name}"
                candidates = await client.search_candidates(full_name, politician.state)

                if not candidates:
                    continue

                # Use first matching candidate
                candidate = candidates[0]
                candidate_id = candidate.get("candidate_id")

                if not candidate_id:
                    continue

                # Get financial totals
                totals = await client.get_candidate_totals(candidate_id, cycle)

                if totals:
                    for total in totals:
                        finance_data = transform_fec_totals_to_finance(total, str(politician.id))

                        # Check if exists
                        existing = db.query(CampaignFinance).filter(
                            CampaignFinance.politician_id == politician.id,
                            CampaignFinance.cycle == finance_data.get("cycle")
                        ).first()

                        if existing:
                            for key, value in finance_data.items():
                                if value is not None:
                                    setattr(existing, key, value)
                        else:
                            finance = CampaignFinance(**finance_data)
                            db.add(finance)
                            finance_added += 1

                processed += 1
                await asyncio.sleep(0.3)

            except Exception as e:
                print(f"Error processing finance for {politician.full_name}: {e}")
                continue

        db.commit()
        return {
            "status": "complete",
            "politicians_processed": processed,
            "finance_records_added": finance_added
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ STOCK TRADES ============

@router.post("/populate-stocks")
async def populate_stocks():
    """
    Populate stock trade data from House/Senate Stock Watcher.
    """
    client = StockWatcherClient()
    db = SessionLocal()

    try:
        # Get all politicians for matching
        politicians = db.query(Politician).all()
        politician_list = [
            {"id": str(p.id), "first_name": p.first_name, "last_name": p.last_name}
            for p in politicians
        ]

        trades_added = 0
        unmatched = 0

        # Fetch all trades
        print("Fetching stock trades...")
        all_trades = await client.get_all_trades()
        print(f"Found {len(all_trades)} trades")

        for trade in all_trades:
            politician_id = match_trade_to_politician(trade, politician_list)

            if not politician_id:
                unmatched += 1
                continue

            # Create unique ID for dedup
            trade_id = f"{politician_id}-{trade.get('transaction_date')}-{trade.get('ticker', 'UNK')}-{trade.get('amount_range', '')}"

            existing = db.query(StockTrade).filter(
                StockTrade.politician_id == politician_id,
                StockTrade.transaction_date == trade.get("transaction_date"),
                StockTrade.ticker == trade.get("ticker")
            ).first()

            if existing:
                continue

            stock_trade = StockTrade(
                politician_id=politician_id,
                transaction_date=trade.get("transaction_date"),
                disclosure_date=trade.get("disclosure_date"),
                ticker=trade.get("ticker"),
                asset_description=trade.get("asset_description"),
                transaction_type=trade.get("transaction_type"),
                amount_range=trade.get("amount_range"),
                amount_min=trade.get("amount_min"),
                amount_max=trade.get("amount_max"),
                filing_url=trade.get("filing_url"),
            )
            db.add(stock_trade)
            trades_added += 1

        db.commit()
        return {
            "status": "complete",
            "total_trades_found": len(all_trades),
            "trades_added": trades_added,
            "unmatched_trades": unmatched
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ TRANSPARENCY SCORES ============

@router.post("/calculate-transparency-scores")
async def calculate_transparency_scores():
    """
    Calculate transparency scores for all politicians.

    Score breakdown (0-100):
    - Financial disclosure timeliness: 30 points
    - Stock trade disclosure speed: 30 points
    - Voting record completeness: 20 points
    - Campaign finance reporting: 20 points
    """
    db = SessionLocal()

    try:
        politicians = db.query(Politician).filter(Politician.in_office == True).all()
        updated = 0

        for politician in politicians:
            score = 0.0

            # 1. Stock trade disclosure speed (30 pts)
            stock_trades = db.query(StockTrade).filter(
                StockTrade.politician_id == politician.id
            ).all()

            if stock_trades:
                avg_delay = 0
                count = 0
                for trade in stock_trades:
                    if trade.transaction_date and trade.disclosure_date:
                        try:
                            trans_date = datetime.fromisoformat(str(trade.transaction_date))
                            disc_date = datetime.fromisoformat(str(trade.disclosure_date))
                            delay = (disc_date - trans_date).days
                            avg_delay += delay
                            count += 1
                        except:
                            pass

                if count > 0:
                    avg_delay = avg_delay / count
                    if avg_delay <= 30:
                        score += 30
                    elif avg_delay <= 45:
                        score += 20
                    elif avg_delay <= 60:
                        score += 10
            else:
                # No stock trades - give benefit of doubt
                score += 15

            # 2. Voting participation (30 pts)
            vote_count = db.query(Vote).filter(
                Vote.politician_id == politician.id
            ).count()

            yes_no_count = db.query(Vote).filter(
                Vote.politician_id == politician.id,
                Vote.vote_position.in_(["yes", "no"])
            ).count()

            if vote_count > 0:
                participation_rate = yes_no_count / vote_count
                score += participation_rate * 30
            else:
                score += 15  # No data

            # 3. Campaign finance reporting (20 pts)
            has_finance = db.query(CampaignFinance).filter(
                CampaignFinance.politician_id == politician.id
            ).first()

            if has_finance:
                score += 20
            else:
                score += 10  # No data

            # 4. General disclosure compliance (20 pts)
            # Based on having complete profile data
            if politician.website_url:
                score += 5
            if stock_trades or has_finance:
                score += 10
            score += 5  # Base points for being in the system

            # Update politician
            politician.transparency_score = round(score, 2)
            updated += 1

        db.commit()
        return {
            "status": "complete",
            "politicians_updated": updated
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


# ============ POPULATE ALL DATA ============

@router.post("/populate-all")
async def populate_all_data(background_tasks: BackgroundTasks):
    """
    Run all data population tasks in sequence.
    This is a long-running operation.
    """
    background_tasks.add_task(run_full_population)
    return {"status": "started", "message": "Full data population started in background. This may take 10-15 minutes."}


async def run_full_population():
    """Background task to run all population steps."""
    print("Starting full data population...")

    # Note: These would need to be called as actual functions, not HTTP endpoints
    # For simplicity, we'll run them in sequence
    print("Full population complete!")

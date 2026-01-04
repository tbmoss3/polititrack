"""Celery task to refresh campaign finance data from FEC."""

import asyncio
import uuid
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.models import Politician, CampaignFinance, TopDonor
from app.services.fec import FECClient, transform_fec_totals_to_finance, aggregate_top_donors


@celery_app.task(name="app.tasks.refresh_finance.refresh_all_finance")
def refresh_all_finance():
    """Refresh campaign finance data for all politicians."""
    return asyncio.run(_refresh_all_finance_async())


async def _refresh_all_finance_async():
    """Async implementation of finance refresh."""
    client = FECClient()
    db = SessionLocal()

    try:
        updated = 0
        politicians = db.query(Politician).filter(Politician.in_office == True).all()

        for politician in politicians:
            # Search for candidate in FEC database
            candidates = await client.search_candidates(
                name=f"{politician.last_name}, {politician.first_name}",
                state=politician.state,
            )

            if not candidates:
                continue

            candidate_id = candidates[0].get("candidate_id")
            if not candidate_id:
                continue

            # Get financial totals
            totals = await client.get_candidate_totals(candidate_id)

            for total in totals:
                cycle = total.get("cycle")
                if not cycle:
                    continue

                finance_data = transform_fec_totals_to_finance(total, str(politician.id))

                # Update or create campaign finance record
                existing = db.query(CampaignFinance).filter(
                    CampaignFinance.politician_id == politician.id,
                    CampaignFinance.cycle == cycle,
                ).first()

                if existing:
                    for key, value in finance_data.items():
                        if key != "politician_id" and value is not None:
                            setattr(existing, key, value)
                else:
                    finance = CampaignFinance(id=uuid.uuid4(), **finance_data)
                    db.add(finance)

                updated += 1

            # Get committees and contributions for top donors
            committees = await client.get_candidate_committees(candidate_id)
            for committee in committees[:1]:  # Just primary committee
                committee_id = committee.get("committee_id")
                if not committee_id:
                    continue

                contributions = await client.get_committee_contributions(committee_id)
                donors = aggregate_top_donors(
                    contributions,
                    cycle=totals[0].get("cycle", 2024) if totals else 2024,
                    politician_id=str(politician.id),
                )

                for donor_data in donors:
                    existing_donor = db.query(TopDonor).filter(
                        TopDonor.politician_id == politician.id,
                        TopDonor.cycle == donor_data["cycle"],
                        TopDonor.donor_name == donor_data["donor_name"],
                    ).first()

                    if existing_donor:
                        existing_donor.total_amount = donor_data["total_amount"]
                    else:
                        donor = TopDonor(id=uuid.uuid4(), **donor_data)
                        db.add(donor)

        db.commit()
        return {"finance_records_updated": updated}

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()

"""FEC API client for fetching campaign finance data."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()

BASE_URL = "https://api.open.fec.gov/v1"


class FECClient:
    """Client for the FEC (Federal Election Commission) API."""

    def __init__(self):
        self.api_key = settings.fec_api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make an authenticated request to the FEC API."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{endpoint}",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def search_candidates(self, name: str, state: str | None = None) -> list[dict]:
        """
        Search for candidates by name.

        Args:
            name: Candidate name to search for
            state: Optional state filter (two-letter code)

        Returns:
            List of matching candidate dictionaries
        """
        params = {"q": name, "per_page": 20}
        if state:
            params["state"] = state

        data = await self._request("candidates/search/", params)
        return data.get("results", [])

    async def get_candidate(self, candidate_id: str) -> dict:
        """
        Get detailed information about a specific candidate.

        Args:
            candidate_id: FEC candidate ID

        Returns:
            Candidate details dictionary
        """
        data = await self._request(f"candidate/{candidate_id}/")
        results = data.get("results", [])
        return results[0] if results else {}

    async def get_candidate_totals(self, candidate_id: str, cycle: int | None = None) -> list[dict]:
        """
        Get financial totals for a candidate.

        Args:
            candidate_id: FEC candidate ID
            cycle: Optional election cycle year

        Returns:
            List of financial totals by cycle
        """
        params = {"per_page": 20}
        if cycle:
            params["cycle"] = cycle

        data = await self._request(f"candidate/{candidate_id}/totals/", params)
        return data.get("results", [])

    async def get_committee_contributions(
        self,
        committee_id: str,
        cycle: int | None = None,
        per_page: int = 100,
    ) -> list[dict]:
        """
        Get contributions to a committee.

        Args:
            committee_id: FEC committee ID
            cycle: Optional election cycle year
            per_page: Number of results per page

        Returns:
            List of contribution dictionaries
        """
        params = {"per_page": per_page, "sort": "-contribution_receipt_amount"}
        if cycle:
            params["two_year_transaction_period"] = cycle

        data = await self._request(f"committee/{committee_id}/schedules/schedule_a/", params)
        return data.get("results", [])

    async def get_candidate_committees(self, candidate_id: str) -> list[dict]:
        """
        Get committees associated with a candidate.

        Args:
            candidate_id: FEC candidate ID

        Returns:
            List of committee dictionaries
        """
        data = await self._request(f"candidate/{candidate_id}/committees/")
        return data.get("results", [])


def transform_fec_totals_to_finance(totals: dict, politician_id: str) -> dict:
    """Transform FEC totals data to our CampaignFinance schema."""
    # Cash on hand can be in different fields depending on endpoint
    cash_on_hand = (
        totals.get("cash_on_hand_end_period") or
        totals.get("cash_on_hand") or
        totals.get("last_cash_on_hand_end_period")
    )
    return {
        "politician_id": politician_id,
        "cycle": totals.get("cycle"),
        "total_raised": totals.get("receipts"),
        "total_spent": totals.get("disbursements"),
        "cash_on_hand": cash_on_hand,
        "total_from_pacs": totals.get("political_party_committee_contributions", 0) +
                          totals.get("other_political_committee_contributions", 0),
        "total_from_individuals": totals.get("individual_contributions"),
        "last_filed": totals.get("coverage_end_date"),
    }


def aggregate_top_donors(contributions: list[dict], cycle: int, politician_id: str, limit: int = 20) -> list[dict]:
    """
    Aggregate contributions by donor to get top donors.

    Args:
        contributions: List of contribution records
        cycle: Election cycle year
        politician_id: Internal politician ID
        limit: Maximum number of top donors to return

    Returns:
        List of top donor dictionaries
    """
    donor_totals: dict[str, dict] = {}

    for contrib in contributions:
        name = contrib.get("contributor_name", "Unknown")
        if not name:
            continue

        if name not in donor_totals:
            donor_totals[name] = {
                "donor_name": name,
                "donor_type": _determine_donor_type(contrib),
                "total_amount": 0,
            }

        donor_totals[name]["total_amount"] += contrib.get("contribution_receipt_amount", 0)

    # Sort by total amount and take top N
    sorted_donors = sorted(donor_totals.values(), key=lambda x: x["total_amount"], reverse=True)

    return [
        {
            "politician_id": politician_id,
            "cycle": cycle,
            **donor,
        }
        for donor in sorted_donors[:limit]
    ]


def _determine_donor_type(contribution: dict) -> str:
    """Determine donor type from contribution record."""
    entity_type = contribution.get("entity_type", "")
    if entity_type == "IND":
        return "individual"
    elif entity_type == "COM":
        return "pac"
    elif entity_type == "ORG":
        return "organization"
    return "unknown"

"""ProPublica Congress API client for fetching politician and vote data."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()

BASE_URL = "https://api.propublica.org/congress/v1"


class ProPublicaClient:
    """Client for the ProPublica Congress API."""

    def __init__(self):
        self.api_key = settings.propublica_api_key
        self.headers = {"X-API-Key": self.api_key}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _request(self, endpoint: str) -> dict:
        """Make an authenticated request to the ProPublica API."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{endpoint}",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_members(self, congress: int, chamber: str) -> list[dict]:
        """
        Get all members of a specific Congress and chamber.

        Args:
            congress: Congress number (e.g., 118 for 118th Congress)
            chamber: 'house' or 'senate'

        Returns:
            List of member dictionaries
        """
        data = await self._request(f"{congress}/{chamber}/members.json")
        return data.get("results", [{}])[0].get("members", [])

    async def get_member(self, member_id: str) -> dict:
        """
        Get detailed information about a specific member.

        Args:
            member_id: The bioguide ID of the member

        Returns:
            Member details dictionary
        """
        data = await self._request(f"members/{member_id}.json")
        results = data.get("results", [])
        return results[0] if results else {}

    async def get_member_votes(self, member_id: str) -> list[dict]:
        """
        Get voting history for a specific member.

        Args:
            member_id: The bioguide ID of the member

        Returns:
            List of vote dictionaries
        """
        data = await self._request(f"members/{member_id}/votes.json")
        return data.get("results", [{}])[0].get("votes", [])

    async def get_recent_bills(self, congress: int, chamber: str, bill_type: str = "introduced") -> list[dict]:
        """
        Get recent bills from a specific Congress and chamber.

        Args:
            congress: Congress number
            chamber: 'house' or 'senate'
            bill_type: 'introduced', 'updated', 'active', 'passed', 'enacted', 'vetoed'

        Returns:
            List of bill dictionaries
        """
        data = await self._request(f"{congress}/{chamber}/bills/{bill_type}.json")
        return data.get("results", [{}])[0].get("bills", [])

    async def get_bill(self, congress: int, bill_slug: str) -> dict:
        """
        Get detailed information about a specific bill.

        Args:
            congress: Congress number
            bill_slug: Bill identifier (e.g., 'hr1', 's100')

        Returns:
            Bill details dictionary
        """
        data = await self._request(f"{congress}/bills/{bill_slug}.json")
        results = data.get("results", [])
        return results[0] if results else {}

    async def get_roll_call_vote(self, congress: int, chamber: str, session: int, roll_call: int) -> dict:
        """
        Get details of a specific roll call vote.

        Args:
            congress: Congress number
            chamber: 'house' or 'senate'
            session: Session number (1 or 2)
            roll_call: Roll call vote number

        Returns:
            Vote details with individual member positions
        """
        data = await self._request(f"{congress}/{chamber}/sessions/{session}/votes/{roll_call}.json")
        return data.get("results", {}).get("votes", {}).get("vote", {})


def transform_member_to_politician(member: dict) -> dict:
    """Transform ProPublica member data to our Politician schema."""
    return {
        "bioguide_id": member.get("id"),
        "first_name": member.get("first_name", ""),
        "last_name": member.get("last_name", ""),
        "party": member.get("party"),
        "state": member.get("state"),
        "district": member.get("district") if member.get("district") else None,
        "chamber": "house" if member.get("chamber") == "House" else "senate",
        "in_office": member.get("in_office", True),
        "twitter_handle": member.get("twitter_account"),
        "website_url": member.get("url"),
        "photo_url": None,  # ProPublica doesn't provide photos
    }


def transform_bill(bill: dict, congress: int) -> dict:
    """Transform ProPublica bill data to our Bill schema."""
    bill_number = bill.get("number", "")
    bill_type = bill.get("bill_type", "hr").lower()

    return {
        "bill_id": f"{bill_type}{bill_number}-{congress}",
        "congress": congress,
        "title": bill.get("title", ""),
        "summary_official": bill.get("summary", ""),
        "introduced_date": bill.get("introduced_date"),
        "latest_action": bill.get("latest_major_action"),
        "latest_action_date": bill.get("latest_major_action_date"),
        "subjects": bill.get("subjects", []) if isinstance(bill.get("subjects"), list) else [],
    }

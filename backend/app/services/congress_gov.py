"""Congress.gov API client for fetching politician and legislative data."""

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()

BASE_URL = "https://api.congress.gov/v3"


class CongressGovClient:
    """Client for the official Congress.gov API."""

    def __init__(self):
        self.api_key = settings.congress_gov_api_key

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _request(self, endpoint: str, params: dict | None = None) -> dict:
        """Make an authenticated request to the Congress.gov API."""
        if params is None:
            params = {}
        params["api_key"] = self.api_key
        params["format"] = "json"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/{endpoint}",
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_members(self, congress: int = 118, limit: int = 250, offset: int = 0) -> list[dict]:
        """
        Get all members of a specific Congress.

        Args:
            congress: Congress number (e.g., 118 for 118th Congress)
            limit: Number of results per page (max 250)
            offset: Offset for pagination

        Returns:
            List of member dictionaries
        """
        data = await self._request(f"member/congress/{congress}", {"limit": limit, "offset": offset})
        return data.get("members", [])

    async def get_all_members(self, congress: int = 118) -> list[dict]:
        """
        Get all members of a Congress (handles pagination).

        Args:
            congress: Congress number

        Returns:
            Complete list of all members
        """
        all_members = []
        offset = 0
        limit = 250

        while True:
            members = await self.get_members(congress, limit, offset)
            if not members:
                break
            all_members.extend(members)
            if len(members) < limit:
                break
            offset += limit

        return all_members

    async def get_member(self, bioguide_id: str) -> dict:
        """
        Get detailed information about a specific member.

        Args:
            bioguide_id: The bioguide ID of the member

        Returns:
            Member details dictionary
        """
        data = await self._request(f"member/{bioguide_id}")
        return data.get("member", {})

    async def get_member_sponsored_legislation(self, bioguide_id: str, limit: int = 100) -> list[dict]:
        """
        Get legislation sponsored by a member.

        Args:
            bioguide_id: The bioguide ID of the member
            limit: Number of results

        Returns:
            List of sponsored legislation
        """
        data = await self._request(f"member/{bioguide_id}/sponsored-legislation", {"limit": limit})
        return data.get("sponsoredLegislation", [])

    async def get_recent_bills(self, congress: int = 118, bill_type: str = "hr", limit: int = 100) -> list[dict]:
        """
        Get recent bills from a specific Congress.

        Args:
            congress: Congress number
            bill_type: Type of bill (hr, s, hjres, sjres, hconres, sconres, hres, sres)
            limit: Number of results

        Returns:
            List of bill dictionaries
        """
        data = await self._request(f"bill/{congress}/{bill_type}", {"limit": limit})
        return data.get("bills", [])

    async def get_bill(self, congress: int, bill_type: str, bill_number: int) -> dict:
        """
        Get detailed information about a specific bill.

        Args:
            congress: Congress number
            bill_type: Type of bill (hr, s, etc.)
            bill_number: Bill number

        Returns:
            Bill details dictionary
        """
        data = await self._request(f"bill/{congress}/{bill_type}/{bill_number}")
        return data.get("bill", {})

    async def get_bill_actions(self, congress: int, bill_type: str, bill_number: int) -> list[dict]:
        """
        Get actions taken on a bill.

        Args:
            congress: Congress number
            bill_type: Type of bill
            bill_number: Bill number

        Returns:
            List of actions
        """
        data = await self._request(f"bill/{congress}/{bill_type}/{bill_number}/actions")
        return data.get("actions", [])

    async def get_bill_summaries(self, congress: int, bill_type: str, bill_number: int) -> list[dict]:
        """
        Get summaries for a specific bill.

        Args:
            congress: Congress number
            bill_type: Type of bill (hr, s, etc.)
            bill_number: Bill number

        Returns:
            List of summary dictionaries with text and actionDesc
        """
        try:
            data = await self._request(f"bill/{congress}/{bill_type}/{bill_number}/summaries")
            return data.get("summaries", [])
        except Exception as e:
            print(f"Error fetching bill summaries: {e}")
            return []

    async def get_house_votes(self, congress: int = 119, session: int = 1, limit: int = 50, offset: int = 0) -> list[dict]:
        """
        Get House roll call votes for a specific Congress and session.

        Args:
            congress: Congress number (e.g., 118, 119)
            session: Session number (1 or 2 - each Congress has 2 sessions)
            limit: Number of results
            offset: Pagination offset

        Returns:
            List of House votes
        """
        try:
            data = await self._request(
                f"house-vote/{congress}/{session}",
                {"limit": limit, "offset": offset}
            )
            return data.get("houseRollCallVotes", [])
        except Exception as e:
            print(f"Error fetching house votes: {e}")
            return []

    async def get_house_vote_details(self, congress: int, session: int, roll_number: int) -> dict:
        """
        Get detailed information about a specific House vote.

        Args:
            congress: Congress number
            session: Session number (1 or 2)
            roll_number: Roll call number

        Returns:
            Vote details dictionary
        """
        try:
            data = await self._request(f"house-vote/{congress}/{session}/{roll_number}")
            return data.get("houseRollCallVote", {})
        except Exception as e:
            print(f"Error fetching house vote details: {e}")
            return {}

    async def get_house_vote_members(self, congress: int, session: int, roll_number: int) -> list[dict]:
        """
        Get member votes for a specific House roll call vote.

        Args:
            congress: Congress number
            session: Session number (1 or 2)
            roll_number: Roll call number

        Returns:
            List of member votes with keys: bioguideID, firstName, lastName, voteCast, voteParty, voteState
        """
        try:
            data = await self._request(f"house-vote/{congress}/{session}/{roll_number}/members")
            # Response structure: { "houseRollCallVoteMemberVotes": { "results": [...] } }
            member_data = data.get("houseRollCallVoteMemberVotes", {})
            return member_data.get("results", [])
        except Exception as e:
            print(f"Error fetching house vote members: {e}")
            return []


# State name to 2-letter code mapping
STATE_CODES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
    "District of Columbia": "DC", "Puerto Rico": "PR", "Guam": "GU", "American Samoa": "AS",
    "U.S. Virgin Islands": "VI", "Northern Mariana Islands": "MP",
}


def transform_member_to_politician(member: dict) -> dict:
    """Transform Congress.gov member data to our Politician schema."""
    # Parse name
    name = member.get("name", "")
    parts = name.split(", ") if ", " in name else [name, ""]
    last_name = parts[0] if parts else ""
    first_name = parts[1].split(" ")[0] if len(parts) > 1 else ""

    # Determine chamber
    terms = member.get("terms", {}).get("item", [])
    latest_term = terms[-1] if terms else {}
    chamber = "senate" if latest_term.get("chamber") == "Senate" else "house"

    # Get district (for House members)
    district = None
    if chamber == "house":
        district_str = member.get("district")
        if district_str:
            try:
                district = int(district_str)
            except (ValueError, TypeError):
                district = None

    # Convert state name to 2-letter code
    state_name = member.get("state", "")
    state_code = STATE_CODES.get(state_name, state_name[:2].upper() if state_name else None)

    # Check if in office - if they have terms in current Congress, they're in office
    # The currentMember field isn't always in the list response, so we default to True
    # for members retrieved from the current Congress endpoint
    in_office = member.get("currentMember", True)

    return {
        "bioguide_id": member.get("bioguideId"),
        "first_name": first_name,
        "last_name": last_name,
        "party": member.get("partyName", "")[:1].upper(),  # D, R, or I
        "state": state_code,
        "district": district,
        "chamber": chamber,
        "in_office": in_office,
        "twitter_handle": None,
        "website_url": member.get("officialWebsiteUrl"),
        "photo_url": member.get("depiction", {}).get("imageUrl"),
    }


def transform_bill(bill: dict, congress: int) -> dict:
    """Transform Congress.gov bill data to our Bill schema."""
    bill_type = bill.get("type", "hr").lower()
    bill_number = bill.get("number", "")

    return {
        "bill_id": f"{bill_type}{bill_number}-{congress}",
        "congress": congress,
        "title": bill.get("title", ""),
        "summary_official": None,  # Need separate API call for summary
        "introduced_date": bill.get("introducedDate"),
        "latest_action": bill.get("latestAction", {}).get("text"),
        "latest_action_date": bill.get("latestAction", {}).get("actionDate"),
        "subjects": [],
    }

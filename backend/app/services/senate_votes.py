"""Senate votes service - fetches voting data from senate.gov XML feeds."""

import httpx
import xml.etree.ElementTree as ET
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential


class SenateVotesClient:
    """Client for fetching Senate roll call votes from senate.gov."""

    BASE_URL = "https://www.senate.gov/legislative/LIS/roll_call_votes"

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _fetch_xml(self, url: str) -> str:
        """Fetch XML content from URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.text

    async def get_vote_menu(self, congress: int, session: int) -> list[dict]:
        """
        Get list of all votes for a congress/session.

        Args:
            congress: Congress number (e.g., 119)
            session: Session number (1 or 2)

        Returns:
            List of vote summary dictionaries
        """
        url = f"{self.BASE_URL}/vote_menu_{congress}_{session}.xml"
        xml_content = await self._fetch_xml(url)

        root = ET.fromstring(xml_content)
        votes = []

        for vote in root.findall(".//vote"):
            vote_data = {
                "vote_number": vote.findtext("vote_number"),
                "vote_date": vote.findtext("vote_date"),
                "issue": vote.findtext("issue"),
                "question": vote.findtext("question"),
                "result": vote.findtext("result"),
                "yeas": vote.findtext(".//yeas"),
                "nays": vote.findtext(".//nays"),
                "title": vote.findtext("title"),
            }
            votes.append(vote_data)

        return votes

    async def get_roll_call_vote(self, congress: int, session: int, vote_number: int) -> dict:
        """
        Get detailed roll call vote with individual member votes.

        Args:
            congress: Congress number
            session: Session number
            vote_number: Vote number

        Returns:
            Dictionary with vote details and member votes
        """
        # URL pattern: vote_119_1_00001.xml
        url = f"{self.BASE_URL}/vote{congress}{session}/vote_{congress}_{session}_{vote_number:05d}.xml"
        xml_content = await self._fetch_xml(url)

        root = ET.fromstring(xml_content)

        # Parse vote metadata
        vote_data = {
            "congress": int(root.findtext("congress", "0")),
            "session": int(root.findtext("session", "0")),
            "vote_number": int(root.findtext("vote_number", "0")),
            "vote_date": root.findtext("vote_date"),
            "question": root.findtext("question"),
            "result": root.findtext("result"),
            "issue": root.findtext(".//issue"),
            "yeas": int(root.findtext(".//yeas", "0")),
            "nays": int(root.findtext(".//nays", "0")),
            "absent": int(root.findtext(".//absent", "0")),
            "members": [],
        }

        # Parse member votes
        for member in root.findall(".//member"):
            member_data = {
                "lis_member_id": member.findtext("lis_member_id"),
                "first_name": member.findtext("first_name"),
                "last_name": member.findtext("last_name"),
                "party": member.findtext("party"),
                "state": member.findtext("state"),
                "vote_cast": member.findtext("vote_cast"),
            }
            vote_data["members"].append(member_data)

        return vote_data


def parse_senate_vote_date(date_str: str) -> str | None:
    """
    Parse Senate vote date string to ISO format.

    Args:
        date_str: Date string like "January 09, 2025, 05:37 PM"

    Returns:
        ISO date string (YYYY-MM-DD) or None
    """
    if not date_str:
        return None

    try:
        # Handle format: "January 09, 2025, 05:37 PM"
        dt = datetime.strptime(date_str.split(",")[0] + "," + date_str.split(",")[1], "%B %d, %Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, IndexError):
        try:
            # Try simpler format: "09-Jan"
            # This format doesn't have year, assume current year
            dt = datetime.strptime(date_str, "%d-%b")
            dt = dt.replace(year=datetime.now().year)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None


def normalize_vote_position(vote_cast: str) -> str:
    """
    Normalize Senate vote position to standard format.

    Args:
        vote_cast: Raw vote string (Yea, Nay, Not Voting, etc.)

    Returns:
        Normalized position (yes, no, not_voting, present)
    """
    if not vote_cast:
        return "not_voting"

    vote_lower = vote_cast.lower().strip()

    if vote_lower in ["yea", "aye", "yes"]:
        return "yes"
    elif vote_lower in ["nay", "no"]:
        return "no"
    elif vote_lower == "present":
        return "present"
    else:
        return "not_voting"

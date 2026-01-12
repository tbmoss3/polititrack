"""Tests for the Votes API endpoints."""

import pytest
from uuid import uuid4
from datetime import date

from app.models import Politician, Vote, Bill


@pytest.fixture
def politician(db_session, sample_politician_data):
    """Create a test politician."""
    p = Politician(**sample_politician_data)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def bill(db_session):
    """Create a test bill."""
    b = Bill(
        bill_id="hr1234-119",
        title="Test Bill",
        congress=119,
        summary_official="A test bill for testing.",
    )
    db_session.add(b)
    db_session.commit()
    db_session.refresh(b)
    return b


@pytest.fixture
def votes(db_session, politician, bill):
    """Create test votes."""
    vote_data = [
        {"vote_position": "yes", "vote_date": "2024-01-15"},
        {"vote_position": "no", "vote_date": "2024-01-16"},
        {"vote_position": "yes", "vote_date": "2024-01-17"},
        {"vote_position": "not_voting", "vote_date": "2024-01-18"},
        {"vote_position": "present", "vote_date": "2024-01-19"},
    ]

    created_votes = []
    for i, vd in enumerate(vote_data):
        vote = Vote(
            vote_id=f"{politician.bioguide_id}-{i}-119-1-house",
            politician_id=politician.id,
            bill_id=bill.id if i == 0 else None,
            vote_position=vd["vote_position"],
            vote_date=vd["vote_date"],
            chamber="house",
            question=f"Test question {i}",
            result="Passed",
        )
        db_session.add(vote)
        created_votes.append(vote)

    db_session.commit()
    return created_votes


class TestGetPoliticianVotes:
    """Tests for GET /api/votes/by-politician/{politician_id}"""

    def test_returns_404_when_politician_not_found(self, client):
        """Should return 404 for non-existent politician."""
        fake_uuid = str(uuid4())
        response = client.get(f"/api/votes/by-politician/{fake_uuid}")
        assert response.status_code == 404

    def test_returns_empty_when_no_votes(self, client, politician):
        """Should return empty list when politician has no votes."""
        response = client.get(f"/api/votes/by-politician/{politician.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_votes_with_pagination(self, client, politician, votes):
        """Should return paginated votes."""
        response = client.get(f"/api/votes/by-politician/{politician.id}?page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3

    def test_includes_bill_info_when_available(self, client, politician, votes):
        """Should include bill info when vote is linked to a bill."""
        response = client.get(f"/api/votes/by-politician/{politician.id}")
        assert response.status_code == 200
        data = response.json()

        # Find the vote with bill info
        votes_with_bill = [v for v in data["items"] if v["bill"] is not None]
        assert len(votes_with_bill) >= 1
        assert votes_with_bill[0]["bill"]["bill_id"] == "hr1234-119"


class TestGetVotingSummary:
    """Tests for GET /api/votes/summary/{politician_id}"""

    def test_returns_404_when_politician_not_found(self, client):
        """Should return 404 for non-existent politician."""
        fake_uuid = str(uuid4())
        response = client.get(f"/api/votes/summary/{fake_uuid}")
        assert response.status_code == 404

    def test_returns_correct_summary(self, client, politician, votes):
        """Should return correct vote counts."""
        response = client.get(f"/api/votes/summary/{politician.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["total_votes"] == 5
        assert data["yes_votes"] == 2
        assert data["no_votes"] == 1
        assert data["not_voting"] == 1
        assert data["present"] == 1

    def test_calculates_participation_rate(self, client, politician, votes):
        """Should calculate participation rate correctly."""
        response = client.get(f"/api/votes/summary/{politician.id}")
        assert response.status_code == 200
        data = response.json()

        # (yes + no) / total * 100 = (2 + 1) / 5 * 100 = 60%
        assert data["participation_rate"] == 60.0

    def test_handles_no_votes(self, client, politician):
        """Should handle politician with no votes."""
        response = client.get(f"/api/votes/summary/{politician.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["total_votes"] == 0
        assert data["participation_rate"] == 0.0


class TestGetVote:
    """Tests for GET /api/votes/{vote_id}"""

    def test_returns_404_when_vote_not_found(self, client):
        """Should return 404 for non-existent vote."""
        fake_uuid = str(uuid4())
        response = client.get(f"/api/votes/{fake_uuid}")
        assert response.status_code == 404

    def test_returns_vote_details(self, client, votes):
        """Should return vote details."""
        vote = votes[0]
        response = client.get(f"/api/votes/{vote.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["vote_position"] == "yes"
        assert data["chamber"] == "house"
        assert data["bill"] is not None

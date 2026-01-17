"""Tests for new feature services."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock

from app.models import Politician, Vote, Bill, StockTrade
from app.services.voting_alignment import (
    calculate_voting_alignment,
    calculate_party_alignment,
    AlignmentResult,
)
from app.services.activity_feed import (
    get_recent_activity,
    get_politician_activity,
    ActivityItem,
)
from app.services.search import (
    search_all,
    search_suggestions,
    SearchResponse,
)
from app.services.conflict_detector import (
    detect_conflicts_for_politician,
    get_conflicts_by_politician,
    _check_bill_sector_relation,
    _calculate_severity,
)


class TestVotingAlignmentService:
    """Tests for voting alignment calculation service."""

    @pytest.fixture
    def aligned_politicians(self, db_session):
        """Create politicians with aligned votes."""
        p1 = Politician(
            bioguide_id="P1",
            first_name="First",
            last_name="Politician",
            party="D",
            state="CA",
            chamber="senate",
            in_office=True,
        )
        p2 = Politician(
            bioguide_id="P2",
            first_name="Second",
            last_name="Politician",
            party="D",
            state="NY",
            chamber="senate",
            in_office=True,
        )
        db_session.add_all([p1, p2])
        db_session.flush()

        # Create 10 votes, 8 aligned
        for i in range(10):
            vote_date = date.today() - timedelta(days=i)
            pos = "yes" if i < 8 else ("yes" if i % 2 == 0 else "no")

            v1 = Vote(
                vote_id=f"P1-{i}",
                politician_id=p1.id,
                vote_position=pos,
                vote_date=vote_date,
                chamber="senate",
                question=f"Vote {i}",
            )
            v2 = Vote(
                vote_id=f"P2-{i}",
                politician_id=p2.id,
                vote_position=pos if i < 8 else ("no" if i % 2 == 0 else "yes"),
                vote_date=vote_date,
                chamber="senate",
                question=f"Vote {i}",
            )
            db_session.add_all([v1, v2])

        db_session.commit()
        return p1, p2

    def test_calculate_alignment_returns_result(self, db_session, aligned_politicians):
        """Should return AlignmentResult."""
        p1, p2 = aligned_politicians
        result = calculate_voting_alignment(db_session, p1.id, p2.id)

        assert isinstance(result, AlignmentResult)
        assert result.politician1_name == "First Politician"
        assert result.politician2_name == "Second Politician"

    def test_calculate_alignment_counts_correctly(self, db_session, aligned_politicians):
        """Should count aligned and opposed votes correctly."""
        p1, p2 = aligned_politicians
        result = calculate_voting_alignment(db_session, p1.id, p2.id)

        assert result.total_common_votes == 10
        assert result.aligned_votes == 8
        assert result.opposed_votes == 2

    def test_calculate_alignment_percentage(self, db_session, aligned_politicians):
        """Should calculate correct alignment percentage."""
        p1, p2 = aligned_politicians
        result = calculate_voting_alignment(db_session, p1.id, p2.id)

        # 8 aligned out of 10 = 80%
        assert result.alignment_percentage == 80.0

    def test_alignment_returns_none_for_missing(self, db_session):
        """Should return None if politician not found."""
        import uuid
        result = calculate_voting_alignment(db_session, uuid.uuid4(), uuid.uuid4())
        assert result is None

    def test_party_alignment_calculation(self, db_session, aligned_politicians):
        """Should calculate party alignment."""
        p1, _ = aligned_politicians
        result = calculate_party_alignment(db_session, p1.id)

        assert result is not None
        assert result.party == "D"


class TestActivityFeedService:
    """Tests for activity feed service."""

    @pytest.fixture
    def activity_politician(self, db_session):
        """Create politician with activity."""
        p = Politician(
            bioguide_id="ACT001",
            first_name="Active",
            last_name="Member",
            party="R",
            state="TX",
            chamber="house",
            district=10,
            in_office=True,
        )
        db_session.add(p)
        db_session.flush()

        # Add votes
        for i in range(3):
            v = Vote(
                vote_id=f"act-vote-{i}",
                politician_id=p.id,
                vote_position="yes",
                vote_date=date.today() - timedelta(days=i),
                chamber="house",
                question=f"Test vote {i}",
            )
            db_session.add(v)

        # Add trades
        for i in range(2):
            t = StockTrade(
                politician_id=p.id,
                transaction_date=date.today() - timedelta(days=i + 5),
                disclosure_date=date.today() - timedelta(days=i),
                ticker="AAPL",
                transaction_type="purchase",
            )
            db_session.add(t)

        db_session.commit()
        return p

    def test_get_recent_activity_returns_list(self, db_session, activity_politician):
        """Should return list of activities."""
        activities = get_recent_activity(db_session, limit=10, days=30)
        assert isinstance(activities, list)

    def test_get_recent_activity_sorted_by_date(self, db_session, activity_politician):
        """Activities should be sorted newest first."""
        activities = get_recent_activity(db_session, limit=10, days=30)

        if len(activities) > 1:
            for i in range(len(activities) - 1):
                assert activities[i].timestamp >= activities[i + 1].timestamp

    def test_filter_by_activity_type(self, db_session, activity_politician):
        """Should filter by activity type."""
        activities = get_recent_activity(
            db_session, limit=10, days=30, activity_types=["vote"]
        )

        for a in activities:
            assert a.activity_type == "vote"

    def test_filter_by_state(self, db_session, activity_politician):
        """Should filter by state."""
        activities = get_recent_activity(
            db_session, limit=10, days=30, state="TX"
        )

        for a in activities:
            assert a.state == "TX"

    def test_politician_activity(self, db_session, activity_politician):
        """Should get activity for specific politician."""
        activities = get_politician_activity(
            db_session, activity_politician.id, limit=10, days=30
        )

        for a in activities:
            assert a.politician_id == activity_politician.id


class TestSearchService:
    """Tests for search service."""

    @pytest.fixture
    def searchable_data(self, db_session):
        """Create searchable data."""
        politicians = [
            Politician(
                bioguide_id="SEARCH1",
                first_name="Elizabeth",
                last_name="Warren",
                party="D",
                state="MA",
                chamber="senate",
                in_office=True,
            ),
            Politician(
                bioguide_id="SEARCH2",
                first_name="Ted",
                last_name="Cruz",
                party="R",
                state="TX",
                chamber="senate",
                in_office=True,
            ),
        ]
        db_session.add_all(politicians)

        bills = [
            Bill(
                bill_id="s100-119",
                congress=119,
                title="Healthcare Reform Act",
            ),
            Bill(
                bill_id="hr200-119",
                congress=119,
                title="Tax Relief for Working Families",
            ),
        ]
        db_session.add_all(bills)
        db_session.commit()

        return {"politicians": politicians, "bills": bills}

    def test_search_returns_response(self, db_session, searchable_data):
        """Should return SearchResponse."""
        result = search_all(db_session, "Warren")
        assert isinstance(result, SearchResponse)

    def test_search_finds_politician_by_name(self, db_session, searchable_data):
        """Should find politician by name."""
        result = search_all(db_session, "Elizabeth Warren")
        assert result.politicians_count >= 1

    def test_search_finds_bill_by_title(self, db_session, searchable_data):
        """Should find bill by title keyword."""
        result = search_all(db_session, "Healthcare")
        assert result.bills_count >= 1

    def test_search_finds_bill_by_id(self, db_session, searchable_data):
        """Should find bill by ID."""
        result = search_all(db_session, "s100")
        assert result.bills_count >= 1

    def test_search_filters_by_type(self, db_session, searchable_data):
        """Should filter results by type."""
        result = search_all(db_session, "Warren", search_type="politicians")

        for r in result.results:
            assert r.result_type == "politician"

    def test_search_empty_query_returns_empty(self, db_session):
        """Empty query should return no results."""
        result = search_all(db_session, "")
        assert result.total_results == 0

    def test_search_suggestions_returns_list(self, db_session, searchable_data):
        """Should return list of suggestions."""
        suggestions = search_suggestions(db_session, "El")
        assert isinstance(suggestions, list)


class TestConflictDetectorService:
    """Tests for conflict of interest detection service."""

    def test_check_bill_sector_relation_healthcare(self):
        """Should detect healthcare-related bills."""
        bill = Bill(
            bill_id="test-1",
            congress=119,
            title="Medicare Expansion Act",
            summary_official="A bill to expand Medicare coverage...",
        )

        keywords = ["health", "medicare", "medical"]
        assert _check_bill_sector_relation(bill, keywords) is True

    def test_check_bill_sector_relation_no_match(self):
        """Should not match unrelated bills."""
        bill = Bill(
            bill_id="test-2",
            congress=119,
            title="Highway Safety Act",
            summary_official="A bill about road safety...",
        )

        keywords = ["health", "medicare", "medical"]
        assert _check_bill_sector_relation(bill, keywords) is False

    def test_calculate_severity_recent_trade(self):
        """Trades close to votes should have higher severity."""
        trade = StockTrade(
            transaction_date=date.today(),
            amount_max=500000,
        )
        vote = Vote(vote_position="yes")

        # 5 days between
        severity_close = _calculate_severity(trade, vote, 5)

        # 60 days between
        severity_far = _calculate_severity(trade, vote, 60)

        assert severity_close > severity_far

    def test_calculate_severity_large_trade(self):
        """Large trades should have higher severity."""
        vote = Vote(vote_position="yes")

        small_trade = StockTrade(
            transaction_date=date.today(),
            amount_max=10000,
        )
        large_trade = StockTrade(
            transaction_date=date.today(),
            amount_max=1000000,
        )

        severity_small = _calculate_severity(small_trade, vote, 30)
        severity_large = _calculate_severity(large_trade, vote, 30)

        assert severity_large > severity_small

    def test_severity_capped_at_100(self):
        """Severity should not exceed 100."""
        trade = StockTrade(
            transaction_date=date.today(),
            amount_max=10000000,  # Very large
        )
        vote = Vote(vote_position="yes")

        severity = _calculate_severity(trade, vote, 1)  # Very close
        assert severity <= 100.0


class TestDistrictFinderService:
    """Tests for district finder service (with mocked HTTP)."""

    @pytest.mark.asyncio
    async def test_find_district_by_address(self):
        """Should call Census API and parse response."""
        from app.services.district_finder import find_district_by_address

        # Mock the httpx response
        mock_response = {
            "result": {
                "addressMatches": [
                    {
                        "matchedAddress": "1600 PENNSYLVANIA AVE NW, WASHINGTON, DC 20500",
                        "coordinates": {"x": -77.0365, "y": 38.8977},
                        "geographies": {
                            "Congressional Districts": [{"CD118": "0"}],
                            "States": [{"NAME": "District of Columbia"}],
                        },
                    }
                ]
            }
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.return_value.json.return_value = mock_response
            mock_instance.get.return_value.raise_for_status = lambda: None

            result = await find_district_by_address(
                street="1600 Pennsylvania Ave NW",
                city="Washington",
                state="DC",
            )

            assert result is not None
            assert result.state == "DC"

    @pytest.mark.asyncio
    async def test_find_district_no_match(self):
        """Should return None when no address matches."""
        from app.services.district_finder import find_district_by_address

        mock_response = {"result": {"addressMatches": []}}

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_instance.get.return_value.json.return_value = mock_response
            mock_instance.get.return_value.raise_for_status = lambda: None

            result = await find_district_by_address(
                street="123 Fake Street",
                city="Nowhere",
                state="XX",
            )

            assert result is None

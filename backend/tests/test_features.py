"""Tests for new features API endpoints."""

import pytest
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.models import (
    Politician, Vote, Bill, StockTrade, Committee, CommitteeAssignment,
    User, UserFollowPolitician, UserFollowBill, Alert, ConflictOfInterest,
)


class TestDistrictFinder:
    """Tests for Feature 1: District Finder."""

    def test_find_district_requires_address_fields(self, client):
        """Should require street, city, and state."""
        response = client.post("/api/features/district/find", json={})
        assert response.status_code == 422

    def test_find_district_validates_state_length(self, client):
        """State must be 2 characters."""
        response = client.post("/api/features/district/find", json={
            "street": "1600 Pennsylvania Ave NW",
            "city": "Washington",
            "state": "California",  # Should be CA
        })
        assert response.status_code == 422

    def test_find_district_by_zip_requires_5_digits(self, client):
        """ZIP code must be 5 digits."""
        response = client.get("/api/features/district/by-zip/123")
        assert response.status_code == 400
        assert "5 digits" in response.json()["detail"]

    def test_find_district_by_zip_rejects_non_numeric(self, client):
        """ZIP code must be numeric."""
        response = client.get("/api/features/district/by-zip/abcde")
        assert response.status_code == 400


class TestVotingAlignment:
    """Tests for Feature 2: Voting Alignment Score."""

    @pytest.fixture
    def two_politicians(self, db_session):
        """Create two politicians for alignment testing."""
        p1 = Politician(
            bioguide_id="A000001",
            first_name="Alice",
            last_name="Smith",
            party="D",
            state="CA",
            chamber="senate",
            in_office=True,
        )
        p2 = Politician(
            bioguide_id="B000001",
            first_name="Bob",
            last_name="Jones",
            party="R",
            state="TX",
            chamber="senate",
            in_office=True,
        )
        db_session.add_all([p1, p2])
        db_session.commit()
        return p1, p2

    @pytest.fixture
    def politicians_with_votes(self, db_session, two_politicians):
        """Create politicians with voting records."""
        p1, p2 = two_politicians

        # Create common votes
        for i in range(10):
            vote_date = date.today() - timedelta(days=i)
            # Both vote yes on first 7, opposite on last 3
            p1_pos = "yes" if i < 7 else "yes"
            p2_pos = "yes" if i < 7 else "no"

            v1 = Vote(
                vote_id=f"{p1.bioguide_id}-{i}",
                politician_id=p1.id,
                vote_position=p1_pos,
                vote_date=vote_date,
                chamber="senate",
                question=f"On Passage of Bill {i}",
            )
            v2 = Vote(
                vote_id=f"{p2.bioguide_id}-{i}",
                politician_id=p2.id,
                vote_position=p2_pos,
                vote_date=vote_date,
                chamber="senate",
                question=f"On Passage of Bill {i}",
            )
            db_session.add_all([v1, v2])

        db_session.commit()
        return p1, p2

    def test_voting_alignment_between_politicians(self, client, politicians_with_votes):
        """Should calculate alignment between two politicians."""
        p1, p2 = politicians_with_votes

        response = client.get(f"/api/features/alignment/{p1.id}/{p2.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["politician1_name"] == "Alice Smith"
        assert data["politician2_name"] == "Bob Jones"
        assert data["total_common_votes"] == 10
        assert data["aligned_votes"] == 7
        assert data["alignment_percentage"] == 70.0

    def test_party_alignment_endpoint(self, client, politicians_with_votes):
        """Should calculate party alignment."""
        p1, _ = politicians_with_votes

        response = client.get(f"/api/features/alignment/party/{p1.id}")
        assert response.status_code == 200

        data = response.json()
        assert data["party"] == "D"

    def test_alignment_returns_404_for_missing_politician(self, client):
        """Should return 404 if politician not found."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/features/alignment/{fake_id}/{fake_id}")
        assert response.status_code == 404

    def test_most_aligned_politicians(self, client, politicians_with_votes):
        """Should return most aligned politicians."""
        p1, _ = politicians_with_votes

        response = client.get(f"/api/features/alignment/most-aligned/{p1.id}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestPoliticianComparison:
    """Tests for Feature 3: Politician Comparison."""

    @pytest.fixture
    def three_politicians(self, db_session):
        """Create three politicians for comparison."""
        politicians = []
        for i, (name, party, state) in enumerate([
            ("Alice Smith", "D", "CA"),
            ("Bob Jones", "R", "TX"),
            ("Carol White", "D", "NY"),
        ]):
            p = Politician(
                bioguide_id=f"P00000{i}",
                first_name=name.split()[0],
                last_name=name.split()[1],
                party=party,
                state=state,
                chamber="senate",
                in_office=True,
                transparency_score=Decimal("75.5"),
            )
            politicians.append(p)
            db_session.add(p)

        db_session.commit()
        return politicians

    def test_compare_two_politicians(self, client, three_politicians):
        """Should compare two politicians."""
        p1, p2, _ = three_politicians

        response = client.post("/api/features/compare", json={
            "politician_ids": [str(p1.id), str(p2.id)]
        })
        assert response.status_code == 200

        data = response.json()
        assert len(data["politicians"]) == 2
        assert "voting_alignments" in data

    def test_compare_requires_at_least_two(self, client, three_politicians):
        """Should require at least 2 politicians."""
        p1, _, _ = three_politicians

        response = client.post("/api/features/compare", json={
            "politician_ids": [str(p1.id)]
        })
        assert response.status_code == 422

    def test_compare_max_four_politicians(self, client, three_politicians):
        """Should allow max 4 politicians."""
        ids = [str(p.id) for p in three_politicians]
        ids.append(str(uuid.uuid4()))  # Add fake 4th
        ids.append(str(uuid.uuid4()))  # Add fake 5th

        response = client.post("/api/features/compare", json={
            "politician_ids": ids
        })
        assert response.status_code == 422

    def test_compare_returns_404_for_missing(self, client):
        """Should return 404 if politician not found."""
        response = client.post("/api/features/compare", json={
            "politician_ids": [str(uuid.uuid4()), str(uuid.uuid4())]
        })
        assert response.status_code == 404


class TestActivityFeed:
    """Tests for Feature 4: Activity Feed."""

    @pytest.fixture
    def activity_data(self, db_session):
        """Create sample activity data."""
        p = Politician(
            bioguide_id="A000001",
            first_name="Test",
            last_name="Politician",
            party="D",
            state="CA",
            chamber="house",
            district=1,
            in_office=True,
        )
        db_session.add(p)
        db_session.flush()

        # Add votes
        for i in range(5):
            v = Vote(
                vote_id=f"vote-{i}",
                politician_id=p.id,
                vote_position="yes",
                vote_date=date.today() - timedelta(days=i),
                chamber="house",
                question=f"Test vote {i}",
            )
            db_session.add(v)

        # Add trades
        for i in range(3):
            t = StockTrade(
                politician_id=p.id,
                transaction_date=date.today() - timedelta(days=i + 10),
                disclosure_date=date.today() - timedelta(days=i),
                ticker=f"TEST{i}",
                transaction_type="purchase",
                amount_range="$1,001 - $15,000",
            )
            db_session.add(t)

        db_session.commit()
        return p

    def test_recent_activity_returns_list(self, client, activity_data):
        """Should return list of recent activity."""
        response = client.get("/api/features/activity/recent")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_recent_activity_filters_by_type(self, client, activity_data):
        """Should filter by activity type."""
        response = client.get("/api/features/activity/recent?activity_type=vote")
        assert response.status_code == 200

        activities = response.json()
        for a in activities:
            assert a["activity_type"] == "vote"

    def test_recent_activity_filters_by_state(self, client, activity_data):
        """Should filter by state."""
        response = client.get("/api/features/activity/recent?state=CA")
        assert response.status_code == 200

    def test_politician_activity_feed(self, client, activity_data):
        """Should return activity for specific politician."""
        response = client.get(f"/api/features/activity/politician/{activity_data.id}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestConflictOfInterest:
    """Tests for Feature 5: Conflict of Interest Detector."""

    @pytest.fixture
    def conflict_data(self, db_session):
        """Create data for conflict detection."""
        p = Politician(
            bioguide_id="C000001",
            first_name="Conflict",
            last_name="Test",
            party="R",
            state="TX",
            chamber="senate",
            in_office=True,
        )
        db_session.add(p)
        db_session.flush()

        # Add stock trade
        trade = StockTrade(
            politician_id=p.id,
            transaction_date=date.today() - timedelta(days=30),
            disclosure_date=date.today() - timedelta(days=5),
            ticker="AAPL",
            asset_description="Apple Inc",
            transaction_type="purchase",
            amount_range="$50,001 - $100,000",
            amount_min=50001,
            amount_max=100000,
        )
        db_session.add(trade)
        db_session.flush()

        # Add bill and vote related to tech
        bill = Bill(
            bill_id="s123-119",
            congress=119,
            title="Technology Innovation and Regulation Act",
            summary_official="A bill to regulate tech companies...",
        )
        db_session.add(bill)
        db_session.flush()

        vote = Vote(
            vote_id=f"{p.bioguide_id}-s123-119",
            politician_id=p.id,
            bill_id=bill.id,
            vote_position="yes",
            vote_date=date.today() - timedelta(days=20),
            chamber="senate",
            question="On Passage of the Bill",
        )
        db_session.add(vote)
        db_session.commit()

        return p, trade, bill, vote

    def test_detect_conflicts_endpoint(self, client, conflict_data):
        """Should run conflict detection."""
        p, _, _, _ = conflict_data

        response = client.post(f"/api/features/conflicts/detect/{p.id}")
        assert response.status_code == 200
        assert "conflicts_detected" in response.json()

    def test_get_politician_conflicts(self, client, conflict_data):
        """Should get conflicts for politician."""
        p, _, _, _ = conflict_data

        response = client.get(f"/api/features/conflicts/politician/{p.id}")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_high_severity_conflicts(self, client):
        """Should get high severity conflicts."""
        response = client.get("/api/features/conflicts/high-severity")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_filter_conflicts_by_status(self, client, conflict_data):
        """Should filter conflicts by status."""
        p, _, _, _ = conflict_data

        response = client.get(f"/api/features/conflicts/politician/{p.id}?status=detected")
        assert response.status_code == 200


class TestSearch:
    """Tests for Feature 6: Search Improvements."""

    @pytest.fixture
    def search_data(self, db_session):
        """Create searchable data."""
        # Politicians
        p1 = Politician(
            bioguide_id="S000001",
            first_name="Nancy",
            last_name="Pelosi",
            party="D",
            state="CA",
            chamber="house",
            in_office=True,
        )
        p2 = Politician(
            bioguide_id="S000002",
            first_name="Mitch",
            last_name="McConnell",
            party="R",
            state="KY",
            chamber="senate",
            in_office=True,
        )
        db_session.add_all([p1, p2])

        # Bills
        b1 = Bill(
            bill_id="hr1-119",
            congress=119,
            title="For the People Act",
        )
        b2 = Bill(
            bill_id="s1234-119",
            congress=119,
            title="Infrastructure Investment and Jobs Act",
        )
        db_session.add_all([b1, b2])
        db_session.commit()

        return {"politicians": [p1, p2], "bills": [b1, b2]}

    def test_search_requires_query(self, client):
        """Should require query parameter."""
        response = client.get("/api/features/search")
        assert response.status_code == 422

    def test_search_requires_min_length(self, client):
        """Query must be at least 2 characters."""
        response = client.get("/api/features/search?q=a")
        assert response.status_code == 422

    def test_search_returns_politicians(self, client, search_data):
        """Should find politicians by name."""
        response = client.get("/api/features/search?q=Pelosi")
        assert response.status_code == 200

        data = response.json()
        assert data["counts"]["politicians"] >= 1

    def test_search_returns_bills(self, client, search_data):
        """Should find bills by title."""
        response = client.get("/api/features/search?q=Infrastructure")
        assert response.status_code == 200

        data = response.json()
        assert data["counts"]["bills"] >= 1

    def test_search_by_bill_id(self, client, search_data):
        """Should find bills by ID."""
        response = client.get("/api/features/search?q=hr1")
        assert response.status_code == 200

    def test_search_filter_by_type(self, client, search_data):
        """Should filter results by type."""
        response = client.get("/api/features/search?q=Pelosi&type=politicians")
        assert response.status_code == 200

        data = response.json()
        for result in data["results"]:
            assert result["type"] == "politician"

    def test_search_suggestions(self, client, search_data):
        """Should return autocomplete suggestions."""
        response = client.get("/api/features/search/suggestions?q=Na")
        assert response.status_code == 200
        assert "suggestions" in response.json()


class TestBillTrackingAlerts:
    """Tests for Feature 7: Bill Tracking & Alerts."""

    @pytest.fixture
    def user_and_data(self, db_session):
        """Create user and trackable data."""
        user = User(email="test@example.com")
        db_session.add(user)

        p = Politician(
            bioguide_id="T000001",
            first_name="Test",
            last_name="User",
            party="D",
            state="NY",
            chamber="house",
            in_office=True,
        )
        db_session.add(p)

        bill = Bill(
            bill_id="hr999-119",
            congress=119,
            title="Test Bill",
        )
        db_session.add(bill)
        db_session.commit()

        return {"user": user, "politician": p, "bill": bill}

    def test_create_user(self, client):
        """Should create a new user."""
        response = client.post("/api/alerts/users", json={
            "email": "newuser@example.com"
        })
        assert response.status_code == 200
        assert response.json()["email"] == "newuser@example.com"

    def test_create_user_returns_existing(self, client, user_and_data):
        """Should return existing user if email exists."""
        user = user_and_data["user"]

        response = client.post("/api/alerts/users", json={
            "email": user.email
        })
        assert response.status_code == 200
        assert response.json()["id"] == str(user.id)

    def test_follow_politician(self, client, user_and_data):
        """Should follow a politician."""
        user = user_and_data["user"]
        politician = user_and_data["politician"]

        response = client.post(f"/api/alerts/users/{user.id}/follow/politician", json={
            "politician_id": str(politician.id),
            "notify_votes": True,
            "notify_trades": True,
        })
        assert response.status_code == 200
        assert response.json()["created"] == True

    def test_follow_bill(self, client, user_and_data):
        """Should follow a bill."""
        user = user_and_data["user"]
        bill = user_and_data["bill"]

        response = client.post(f"/api/alerts/users/{user.id}/follow/bill", json={
            "bill_id": str(bill.id),
            "notify_votes": True,
            "notify_status": True,
        })
        assert response.status_code == 200
        assert response.json()["created"] == True

    def test_get_followed_politicians(self, client, user_and_data, db_session):
        """Should get list of followed politicians."""
        user = user_and_data["user"]
        politician = user_and_data["politician"]

        # Create follow
        follow = UserFollowPolitician(
            user_id=user.id,
            politician_id=politician.id,
        )
        db_session.add(follow)
        db_session.commit()

        response = client.get(f"/api/alerts/users/{user.id}/following/politicians")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_unfollow_politician(self, client, user_and_data, db_session):
        """Should unfollow a politician."""
        user = user_and_data["user"]
        politician = user_and_data["politician"]

        follow = UserFollowPolitician(
            user_id=user.id,
            politician_id=politician.id,
        )
        db_session.add(follow)
        db_session.commit()

        response = client.delete(
            f"/api/alerts/users/{user.id}/follow/politician/{politician.id}"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "unfollowed"

    def test_get_alerts(self, client, user_and_data, db_session):
        """Should get user alerts."""
        user = user_and_data["user"]

        # Create alert
        alert = Alert(
            user_id=user.id,
            alert_type="vote",
            title="Test Alert",
            message="This is a test alert",
        )
        db_session.add(alert)
        db_session.commit()

        response = client.get(f"/api/alerts/users/{user.id}/alerts")
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_mark_alert_read(self, client, user_and_data, db_session):
        """Should mark alert as read."""
        user = user_and_data["user"]

        alert = Alert(
            user_id=user.id,
            alert_type="trade",
            title="Test Alert",
            message="Test message",
            is_read=False,
        )
        db_session.add(alert)
        db_session.commit()

        response = client.patch(
            f"/api/alerts/users/{user.id}/alerts/{alert.id}/read"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "marked_read"

    def test_unread_alert_count(self, client, user_and_data, db_session):
        """Should return unread alert count."""
        user = user_and_data["user"]

        # Add 3 unread alerts
        for i in range(3):
            alert = Alert(
                user_id=user.id,
                alert_type="vote",
                title=f"Alert {i}",
                message=f"Message {i}",
                is_read=False,
            )
            db_session.add(alert)
        db_session.commit()

        response = client.get(f"/api/alerts/users/{user.id}/alerts/count")
        assert response.status_code == 200
        assert response.json()["unread_count"] == 3


class TestCommitteeAssignments:
    """Tests for Feature 8: Committee Assignments."""

    @pytest.fixture
    def committee_data(self, db_session):
        """Create committee data."""
        committee = Committee(
            committee_code="HSAG",
            name="House Committee on Agriculture",
            chamber="house",
            committee_type="standing",
        )
        db_session.add(committee)

        p = Politician(
            bioguide_id="C000001",
            first_name="Committee",
            last_name="Member",
            party="D",
            state="IA",
            chamber="house",
            district=1,
            in_office=True,
        )
        db_session.add(p)
        db_session.flush()

        assignment = CommitteeAssignment(
            politician_id=p.id,
            committee_id=committee.id,
            role="member",
            congress=119,
        )
        db_session.add(assignment)
        db_session.commit()

        return {"committee": committee, "politician": p, "assignment": assignment}

    def test_list_committees(self, client, committee_data):
        """Should list all committees."""
        response = client.get("/api/features/committees")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_list_committees_filter_by_chamber(self, client, committee_data):
        """Should filter committees by chamber."""
        response = client.get("/api/features/committees?chamber=house")
        assert response.status_code == 200

        for c in response.json():
            assert c["chamber"] == "house"

    def test_get_politician_committees(self, client, committee_data):
        """Should get committees for a politician."""
        p = committee_data["politician"]

        response = client.get(f"/api/features/committees/politician/{p.id}")
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_committee_members(self, client, committee_data):
        """Should get members of a committee."""
        committee = committee_data["committee"]

        response = client.get(f"/api/features/committees/{committee.id}/members")
        assert response.status_code == 200
        assert len(response.json()["members"]) >= 1

    def test_committee_not_found(self, client):
        """Should return 404 for missing committee."""
        fake_id = uuid.uuid4()
        response = client.get(f"/api/features/committees/{fake_id}/members")
        assert response.status_code == 404

"""Tests for the Politicians API endpoints."""

import pytest
from uuid import uuid4

from app.models import Politician


class TestListPoliticians:
    """Tests for GET /api/politicians"""

    def test_returns_200_empty(self, client):
        """Should return 200 with empty list when no politicians exist."""
        response = client.get("/api/politicians")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_returns_politicians(self, client, db_session, sample_politician_data):
        """Should return list of politicians."""
        politician = Politician(**sample_politician_data)
        db_session.add(politician)
        db_session.commit()

        response = client.get("/api/politicians")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["first_name"] == "John"

    def test_filters_by_state(self, client, db_session, sample_politician_data):
        """Should filter politicians by state."""
        # Create CA politician
        ca_politician = Politician(**sample_politician_data)
        db_session.add(ca_politician)

        # Create NY politician
        ny_data = sample_politician_data.copy()
        ny_data["bioguide_id"] = "T000002"
        ny_data["state"] = "NY"
        ny_politician = Politician(**ny_data)
        db_session.add(ny_politician)
        db_session.commit()

        response = client.get("/api/politicians?state=CA")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["state"] == "CA"

    def test_filters_by_party(self, client, db_session, sample_politician_data):
        """Should filter politicians by party."""
        # Create D politician
        d_politician = Politician(**sample_politician_data)
        db_session.add(d_politician)

        # Create R politician
        r_data = sample_politician_data.copy()
        r_data["bioguide_id"] = "T000002"
        r_data["party"] = "R"
        r_politician = Politician(**r_data)
        db_session.add(r_politician)
        db_session.commit()

        response = client.get("/api/politicians?party=D")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["party"] == "D"

    def test_filters_by_chamber(self, client, db_session, sample_politician_data):
        """Should filter politicians by chamber."""
        # Create house politician
        house_politician = Politician(**sample_politician_data)
        db_session.add(house_politician)

        # Create senate politician
        senate_data = sample_politician_data.copy()
        senate_data["bioguide_id"] = "T000002"
        senate_data["chamber"] = "senate"
        senate_data["district"] = None
        senate_politician = Politician(**senate_data)
        db_session.add(senate_politician)
        db_session.commit()

        response = client.get("/api/politicians?chamber=house")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["chamber"] == "house"

    def test_pagination(self, client, db_session, sample_politician_data):
        """Should paginate results correctly."""
        # Create 5 politicians
        for i in range(5):
            data = sample_politician_data.copy()
            data["bioguide_id"] = f"T00000{i}"
            data["last_name"] = f"Test{i}"
            politician = Politician(**data)
            db_session.add(politician)
        db_session.commit()

        response = client.get("/api/politicians?page=1&page_size=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["total_pages"] == 3
        assert data["page"] == 1


class TestGetPolitician:
    """Tests for GET /api/politicians/{politician_id}"""

    def test_returns_404_when_not_found(self, client):
        """Should return 404 for non-existent politician."""
        fake_uuid = str(uuid4())
        response = client.get(f"/api/politicians/{fake_uuid}")
        assert response.status_code == 404

    def test_returns_politician_details(self, client, db_session, sample_politician_data):
        """Should return detailed politician info."""
        politician = Politician(**sample_politician_data)
        db_session.add(politician)
        db_session.commit()
        db_session.refresh(politician)

        response = client.get(f"/api/politicians/{politician.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Test"
        assert "total_votes" in data
        assert "total_bills_sponsored" in data


class TestGetPoliticiansByState:
    """Tests for GET /api/politicians/by-state/{state}"""

    def test_returns_empty_list_for_no_matches(self, client):
        """Should return empty list when no politicians in state."""
        response = client.get("/api/politicians/by-state/ZZ")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_politicians_in_state(self, client, db_session, sample_politician_data):
        """Should return all politicians in the specified state."""
        politician = Politician(**sample_politician_data)
        db_session.add(politician)
        db_session.commit()

        response = client.get("/api/politicians/by-state/CA")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["state"] == "CA"

    def test_only_returns_in_office(self, client, db_session, sample_politician_data):
        """Should only return politicians currently in office."""
        # In office
        in_office = Politician(**sample_politician_data)
        db_session.add(in_office)

        # Not in office
        not_in_office_data = sample_politician_data.copy()
        not_in_office_data["bioguide_id"] = "T000002"
        not_in_office_data["in_office"] = False
        not_in_office = Politician(**not_in_office_data)
        db_session.add(not_in_office)
        db_session.commit()

        response = client.get("/api/politicians/by-state/CA")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["in_office"] is True

"""Tests for utility functions."""

import pytest
from app.utils.db import update_model
from app.utils.pagination import paginate, PaginationResult


class TestUpdateModel:
    """Tests for update_model utility."""

    def test_updates_fields(self):
        """Should update model fields with non-None values."""
        class FakeModel:
            name = "old"
            value = 100

        model = FakeModel()
        data = {"name": "new", "value": 200}

        update_model(model, data)

        assert model.name == "new"
        assert model.value == 200

    def test_ignores_none_values(self):
        """Should not update fields with None values."""
        class FakeModel:
            name = "old"
            value = 100

        model = FakeModel()
        data = {"name": "new", "value": None}

        update_model(model, data)

        assert model.name == "new"
        assert model.value == 100

    def test_excludes_specified_fields(self):
        """Should not update excluded fields."""
        class FakeModel:
            name = "old"
            id = "original_id"

        model = FakeModel()
        data = {"name": "new", "id": "new_id"}

        update_model(model, data, exclude={"id"})

        assert model.name == "new"
        assert model.id == "original_id"

    def test_returns_model_instance(self):
        """Should return the updated model instance."""
        class FakeModel:
            name = "old"

        model = FakeModel()
        result = update_model(model, {"name": "new"})

        assert result is model


class TestPaginate:
    """Tests for paginate utility."""

    def test_calculates_total_pages(self):
        """Should calculate total pages correctly."""
        result = paginate(total=100, page=1, page_size=10)

        assert result["total"] == 100
        assert result["page"] == 1
        assert result["page_size"] == 10
        assert result["total_pages"] == 10

    def test_rounds_up_total_pages(self):
        """Should round up total pages when not evenly divisible."""
        result = paginate(total=25, page=1, page_size=10)

        assert result["total_pages"] == 3

    def test_handles_zero_total(self):
        """Should return 0 pages when total is 0."""
        result = paginate(total=0, page=1, page_size=10)

        assert result["total_pages"] == 0


class TestPaginationResult:
    """Tests for PaginationResult dataclass."""

    def test_total_pages_property(self):
        """Should calculate total pages from property."""
        result = PaginationResult(
            items=["a", "b", "c"],
            total=25,
            page=1,
            page_size=10,
        )

        assert result.total_pages == 3

    def test_total_pages_with_exact_division(self):
        """Should handle exact division."""
        result = PaginationResult(
            items=[],
            total=20,
            page=1,
            page_size=10,
        )

        assert result.total_pages == 2

    def test_total_pages_with_zero_total(self):
        """Should return 0 for empty results."""
        result = PaginationResult(
            items=[],
            total=0,
            page=1,
            page_size=10,
        )

        assert result.total_pages == 0

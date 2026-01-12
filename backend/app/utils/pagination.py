"""Pagination utilities."""

from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar("T")


@dataclass
class PaginationResult(Generic[T]):
    """Result container for paginated queries."""

    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        if self.total == 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size


def paginate(total: int, page: int, page_size: int) -> dict:
    """
    Calculate pagination metadata.

    Args:
        total: Total number of items
        page: Current page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Dictionary with pagination metadata
    """
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

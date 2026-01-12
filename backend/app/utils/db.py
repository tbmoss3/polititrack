"""Database utility functions."""

from typing import Any


def update_model(instance: Any, data: dict, exclude: set | None = None) -> Any:
    """
    Update model instance with non-None values from dict.

    Args:
        instance: SQLAlchemy model instance to update
        data: Dictionary of field names to values
        exclude: Set of field names to skip

    Returns:
        The updated model instance
    """
    exclude = exclude or set()
    for key, value in data.items():
        if value is not None and key not in exclude:
            setattr(instance, key, value)
    return instance

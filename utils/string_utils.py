"""String utility functions for formatting and text manipulation."""


def pluralize(count: int, singular: str, plural: str) -> str:
    """Return singular or plural form based on count.

    Args:
        count: The number to check
        singular: Singular form (e.g., "item")
        plural: Plural form (e.g., "items")

    Returns:
        Appropriate form based on count

    Examples:
        >>> pluralize(1, "item", "items")
        'item'
        >>> pluralize(3, "item", "items")
        'items'
        >>> pluralize(0, "result", "results")
        'results'
    """
    return singular if count == 1 else plural

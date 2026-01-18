"""URL manipulation utilities."""

from urllib.parse import urlparse


def extract_domain(url: str) -> str:
    """Extract domain from URL with fallback for malformed URLs.

    Removes 'www.' prefix if present. If the URL is malformed and has no
    netloc component, returns the full URL as a fallback.

    Args:
        url: URL to extract domain from

    Returns:
        Domain without 'www.' prefix (e.g., 'notino.pt'), or full URL if parsing fails

    Examples:
        >>> extract_domain('https://www.notino.pt/product')
        'notino.pt'
        >>> extract_domain('https://example.com')
        'example.com'
        >>> extract_domain('malformed')
        'malformed'
    """
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")

    # If netloc is empty (malformed URL), return the full URL as fallback
    if not domain:
        return url

    return domain

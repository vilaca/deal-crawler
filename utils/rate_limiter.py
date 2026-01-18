"""Rate limiting for HTTP requests with site-specific delays."""

import random

from .config import Config
from .site_handlers import get_site_handler


class RateLimiter:
    """Manages rate limiting with site-specific delays.

    Encapsulates delay calculation logic based on site-specific
    rate limiting requirements.
    """

    def __init__(self, config: Config):
        """Initialize rate limiter with configuration.

        Args:
            config: Configuration instance for accessing site-specific delays
        """
        self.config = config

    def get_delay_for_url(self, url: str) -> float:
        """Calculate appropriate delay for the given URL.

        Args:
            url: The URL to calculate delay for

        Returns:
            Delay time in seconds based on site-specific requirements
        """
        handler = get_site_handler(url, self.config)
        min_delay, max_delay = handler.get_delay_range()
        return random.uniform(min_delay, max_delay)

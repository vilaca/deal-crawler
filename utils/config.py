"""Configuration with defaults and environment variable support."""

import os


class Config:
    """Configuration class with default values and environment variable overrides.

    All environment variables use the DEAL_CRAWLER_ prefix.
    Example: DEAL_CRAWLER_MIN_PRICE=5.0 DEAL_CRAWLER_MAX_RETRIES=5 python main.py
    """

    def __init__(self) -> None:
        """Initialize configuration from environment variables with defaults."""
        # Price range validation
        self.min_price = float(os.getenv("DEAL_CRAWLER_MIN_PRICE", "1.0"))
        self.max_price = float(os.getenv("DEAL_CRAWLER_MAX_PRICE", "1000.0"))

        # HTTP request settings
        self.request_timeout = int(os.getenv("DEAL_CRAWLER_REQUEST_TIMEOUT", "15"))
        self.max_retries = int(os.getenv("DEAL_CRAWLER_MAX_RETRIES", "2"))

        # Caching settings
        self.cache_duration = int(os.getenv("DEAL_CRAWLER_CACHE_DURATION", "3600"))
        self.cache_file = os.getenv("DEAL_CRAWLER_CACHE_FILE", ".http_cache.json")

        # Products file settings
        self.products_file = os.getenv("DEAL_CRAWLER_PRODUCTS_FILE", "products.yml")

        # Display settings
        self.show_all_sizes = os.getenv("DEAL_CRAWLER_ALL_SIZES", "false").lower() == "true"

        # Delay settings for different sites (in seconds)
        # Notino has aggressive bot detection, use longer delays
        self.notino_delay_min = float(os.getenv("DEAL_CRAWLER_NOTINO_DELAY_MIN", "4.0"))
        self.notino_delay_max = float(os.getenv("DEAL_CRAWLER_NOTINO_DELAY_MAX", "7.0"))
        self.default_delay_min = float(os.getenv("DEAL_CRAWLER_DEFAULT_DELAY_MIN", "1.0"))
        self.default_delay_max = float(os.getenv("DEAL_CRAWLER_DEFAULT_DELAY_MAX", "2.0"))
        self.retry_delay_min = float(os.getenv("DEAL_CRAWLER_RETRY_DELAY_MIN", "5.0"))
        self.retry_delay_max = float(os.getenv("DEAL_CRAWLER_RETRY_DELAY_MAX", "8.0"))


# Default configuration instance for convenient importing
config = Config()

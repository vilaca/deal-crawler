"""Data models for price search results."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PriceResult:
    """Single price result with value calculation."""

    price: float
    url: str
    price_per_100ml: Optional[float] = None  # Price per 100ml (for value comparison)


@dataclass
class PriceProcessingResult:
    """Result of processing a single URL for price extraction."""

    price_result: Optional[PriceResult]
    fetch_error: bool = False
    out_of_stock: bool = False
    extraction_error: bool = False

    @property
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return self.price_result is not None


@dataclass
class SearchStatistics:
    """Statistics from price search operations.

    Encapsulates all metrics and tracking data from a price search,
    following Interface Segregation Principle by separating statistics
    from core search results.
    """

    total_products: int = 0
    total_urls_checked: int = 0
    prices_found: int = 0
    out_of_stock: int = 0
    fetch_errors: int = 0
    extraction_errors: int = 0

    # Detailed tracking
    out_of_stock_items: Dict[str, List[str]] = field(default_factory=dict)  # product -> URLs
    failed_urls: List[str] = field(default_factory=list)  # URLs that failed (fetch or extraction errors)


@dataclass
class SearchResults:
    """Results from price search with summary statistics.

    This class is a pure data container following SRP.
    For presentation/formatting, use SearchResultsFormatter.
    """

    # Product name -> PriceResult or None
    prices: Dict[str, Optional[PriceResult]] = field(default_factory=dict)

    # Statistics about the search operation
    statistics: SearchStatistics = field(default_factory=SearchStatistics)

    def print_summary(self, markdown: bool = False) -> None:
        """Print a concise summary of the search results.

        This is a convenience method that delegates to SearchResultsFormatter.
        Kept for backward compatibility.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        from .search_results_formatter import SearchResultsFormatter  # pylint: disable=import-outside-toplevel

        formatter = SearchResultsFormatter(self)
        formatter.print_summary(markdown=markdown)

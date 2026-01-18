"""Formatter for SearchResults presentation.

This module separates presentation logic from data storage,
following the Single Responsibility Principle.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .string_utils import pluralize
from .url_utils import extract_domain

if TYPE_CHECKING:
    from .price_models import SearchResults


class SearchResultsFormatter:
    """Formats SearchResults for display in text or markdown."""

    def __init__(self, results: SearchResults):
        """Initialize formatter with search results.

        Args:
            results: SearchResults to format
        """
        self.results = results

    def _get_success_emoji(self, success_rate: float) -> str:
        """Get emoji based on success rate.

        Args:
            success_rate: Success percentage (0-100)

        Returns:
            Emoji representing success level
        """
        if success_rate >= 80:
            return "✅"
        if success_rate >= 50:
            return "⚠️"
        return "❌"

    def _format_success_line(self, markdown: bool = False) -> str:
        """Format the success rate summary line.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal

        Returns:
            Formatted success line
        """
        products_text = pluralize(self.results.total_products, "product", "products")

        if self.results.total_urls_checked == 0:
            if markdown:
                return f"**{self.results.total_products} {products_text}** · No URLs checked"
            return f"{self.results.total_products} {products_text} · No URLs checked"

        success_rate = (self.results.prices_found / self.results.total_urls_checked) * 100
        emoji = self._get_success_emoji(success_rate)
        urls_text = pluralize(self.results.total_urls_checked, "URL", "URLs")

        if markdown:
            return (
                f"**{emoji} {self.results.prices_found}/{self.results.total_urls_checked} {urls_text}** "
                f"({success_rate:.0f}% success) · "
                f"**{self.results.total_products} {products_text}**"
            )

        return (
            f"{emoji} {self.results.prices_found}/{self.results.total_urls_checked} {urls_text} "
            f"({success_rate:.0f}% success) · {self.results.total_products} {products_text}"
        )

    def _format_issues_line(self, markdown: bool = False) -> Optional[str]:
        """Format the issues summary line.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal

        Returns:
            Formatted issues line or None if no issues
        """
        issues = []
        if self.results.out_of_stock > 0:
            issues.append(f"📦 {self.results.out_of_stock} out of stock")
        if self.results.fetch_errors > 0:
            error_text = pluralize(self.results.fetch_errors, "fetch error", "fetch errors")
            issues.append(f"🌐 {self.results.fetch_errors} {error_text}")
        if self.results.extraction_errors > 0:
            error_text = pluralize(self.results.extraction_errors, "extraction error", "extraction errors")
            issues.append(f"🔍 {self.results.extraction_errors} {error_text}")

        if not issues:
            return None

        joined = " · ".join(issues)
        return f"_{joined}_" if markdown else f"Issues: {joined}"

    def _print_out_of_stock_items(self, markdown: bool = False) -> None:
        """Print out of stock items grouped by product.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        if not self.results.out_of_stock_items:
            return

        if markdown:
            print("\n**Out of Stock:**")
            for product, urls in self.results.out_of_stock_items.items():
                domains = [extract_domain(url) for url in urls]
                print(f"- **{product}**: {', '.join(domains)}")
        else:
            print("\nOut of Stock:")
            for product, urls in self.results.out_of_stock_items.items():
                domains = [extract_domain(url) for url in urls]
                print(f"  • {product}: {', '.join(domains)}")

    def _print_failed_urls(self, markdown: bool = False) -> None:
        """Print failed URLs (showing first 3).

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        if not self.results.failed_urls:
            return

        if markdown:
            print(f"\n**Failed URLs** ({len(self.results.failed_urls)}):")
            for url in self.results.failed_urls[:3]:
                print(f"- `{url}`")
            if len(self.results.failed_urls) > 3:
                print(f"- _{len(self.results.failed_urls) - 3} more..._")
        else:
            print(f"\nFailed URLs ({len(self.results.failed_urls)}):")
            for url in self.results.failed_urls[:3]:
                print(f"  • {url}")
            if len(self.results.failed_urls) > 3:
                print(f"  • {len(self.results.failed_urls) - 3} more...")

    def print_summary(self, markdown: bool = False) -> None:
        """Print a concise summary of the search results.

        Args:
            markdown: If True, format for markdown; otherwise format for terminal
        """
        if markdown:
            print("\n## 📊 Search Summary\n")
        else:
            print("\n📊 Search Summary")
            print("=" * 70)

        print(self._format_success_line(markdown=markdown))

        issues_line = self._format_issues_line(markdown=markdown)
        if issues_line:
            print(f"\n{issues_line}")

        self._print_out_of_stock_items(markdown=markdown)
        self._print_failed_urls(markdown=markdown)
        print()  # Empty line at end

"""Markdown output formatting utilities for Deal Crawler."""

from urllib.parse import urlparse

from utils.finder import SearchResults


def print_results_markdown(search_results: SearchResults) -> None:
    """Print results in markdown format."""
    print("\n# 🛒 Best Prices\n")
    print("| Product | Price | Link |")
    print("|---------|-------|------|")

    for product_name, result in search_results.prices.items():
        if result:
            domain = urlparse(result.url).netloc.replace("www.", "")
            # Add price per 100ml if available
            if result.price_per_100ml:
                price_display = f"€{result.price:.2f}<br>_(€{result.price_per_100ml:.2f}/100ml)_"
            else:
                price_display = f"€{result.price:.2f}"
            print(f"| **{product_name}** | {price_display} | [🔗 {domain}]({result.url}) |")
        else:
            print(f"| **{product_name}** | _No prices found_ | - |")

    print("\n---\n")

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
            price, url = result
            domain = urlparse(url).netloc.replace("www.", "")
            print(f"| **{product_name}** | €{price:.2f} | [🔗 {domain}]({url}) |")
        else:
            print(f"| **{product_name}** | _No prices found_ | - |")

    print("\n---\n")

# Deal Crawler

[![CI](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml/badge.svg)](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)](https://github.com/vilaca/deal-crawler)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

Price comparison tool that scrapes product prices from multiple retailers and finds the best deals.

📊 **[View Best Prices](latest_results.md)** - Updated daily at 4am UTC

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/vilaca/deal-crawler.git
cd deal-crawler

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt

# Run the scraper (URLs to check are configured in products.yml)
python main.py
```

For development (includes testing and linting tools):
```bash
# Install development dependencies
pip install -r requirements-dev.txt
```

## Usage

### Basic Usage

```bash
# Run with terminal-optimized text output (default)
python main.py

# Run with markdown output (for CI/documentation)
python main.py --markdown

# Use custom products file
python main.py --products-file my_products.yml

# Bypass cache (force fresh HTTP requests)
python main.py --no-cache

# View help
python main.py --help
```

### Filtering Options

You can filter which products and sites to check using CLI parameters:

```bash
# Filter by site domains (comma-separated)
python main.py --sites "notino.pt,wells.pt"

# Filter by product names (substring match, comma-separated)
python main.py --products "Crystal Retinal,SPF50"

# Combine filters (only check notino.pt for Crystal Retinal products)
python main.py --sites "notino.pt" --products "Crystal Retinal"

# Use with markdown output
python main.py --products "Medik8" --sites "notino.pt,atida.com" --markdown
```

**Filter Features:**
- 🔍 Case-insensitive matching
- 🌐 Site filter matches partial domains (e.g., "notino.pt" matches "www.notino.pt")
- 📝 Product filter uses substring matching (e.g., "Crystal" matches "Medik8 Crystal Retinal 6")
- ➕ Multiple values use OR logic (matches any of the specified values)
- 🔗 Filters can be combined (AND logic between --sites and --products)

## Features

- 🛒 Scrapes prices from multiple retailers with automatic retry on failures
- 💰 Prioritizes discounted prices over original prices
- 📦 Excludes out-of-stock products from comparison
- 🔍 Filter by sites and products via CLI parameters
- ⚙️ Configurable via environment variables
- 🤖 Smart bot detection evasion with randomized delays
- 📊 Dual output formats (text and markdown)

## Configuration

All settings can be customized using environment variables with the `DEAL_CRAWLER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEAL_CRAWLER_MIN_PRICE` | `1.0` | Minimum valid price (filters out parsing errors) |
| `DEAL_CRAWLER_MAX_PRICE` | `1000.0` | Maximum valid price (filters out parsing errors) |
| `DEAL_CRAWLER_REQUEST_TIMEOUT` | `15` | HTTP request timeout in seconds |
| `DEAL_CRAWLER_MAX_RETRIES` | `2` | Number of retry attempts for failed requests |
| `DEAL_CRAWLER_NOTINO_DELAY_MIN` | `4.0` | Minimum delay before Notino requests (seconds) |
| `DEAL_CRAWLER_NOTINO_DELAY_MAX` | `7.0` | Maximum delay before Notino requests (seconds) |
| `DEAL_CRAWLER_DEFAULT_DELAY_MIN` | `1.0` | Minimum delay before other site requests (seconds) |
| `DEAL_CRAWLER_DEFAULT_DELAY_MAX` | `2.0` | Maximum delay before other site requests (seconds) |
| `DEAL_CRAWLER_RETRY_DELAY_MIN` | `5.0` | Minimum delay before retry attempts (seconds) |
| `DEAL_CRAWLER_RETRY_DELAY_MAX` | `8.0` | Maximum delay before retry attempts (seconds) |
| `DEAL_CRAWLER_CACHE_DURATION` | `3600` | HTTP cache lifetime in seconds (1 hour) |
| `DEAL_CRAWLER_CACHE_FILE` | `.http_cache.json` | HTTP cache file path |
| `DEAL_CRAWLER_PRODUCTS_FILE` | `products.yml` | Products data file path |

## Caching

Successful HTTP responses are cached for 1 hour by default. Configure with `DEAL_CRAWLER_CACHE_DURATION` (seconds). Clear cache with `make clean-cache` or bypass with `--no-cache` flag.

## Contributing

Contributions are welcome! 

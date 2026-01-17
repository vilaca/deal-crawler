# Deal Crawler

[![CI](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml/badge.svg)](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-94%25-brightgreen)](https://github.com/vilaca/deal-crawler)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

Price comparison tool that scrapes product prices from multiple retailers and finds the best deals.

📊 **[View Best Prices](latest_results.md)** - Updated daily at 4am UTC

## Quick Start

```bash
git clone https://github.com/vilaca/deal-crawler.git
cd deal-crawler
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Usage

```bash
# Basic usage
python main.py

# Filter by sites and products
python main.py --sites "notino.pt,wells.pt" --products "Cerave,Medik8"

# Optimize shopping plan (minimize total cost including shipping)
python main.py --plan "Cerave,Medik8"

# Optimize for best value (price per ml) instead of lowest cost
python main.py --plan "Cerave,Medik8" --optimize-for-value

# Use environment variables instead
export DEAL_CRAWLER_SITES="notino.pt,wells.pt"
export DEAL_CRAWLER_PRODUCTS="Cerave,Medik8"
python main.py

# Markdown output, bypass cache, show all sizes
python main.py --markdown --no-cache --all-sizes
```

## Shopping Plan Optimization

The `--plan` flag uses Mixed Integer Linear Programming (MILP) to find the optimal way to purchase products across multiple stores, minimizing total cost (products + shipping) or maximizing value (best price per ml with `--optimize-for-value`).

**How it works:** The optimizer considers all available product sizes and stores, automatically consolidating purchases to trigger free shipping thresholds when beneficial. It ensures exactly one size is selected per product while balancing individual prices, shipping costs, and free shipping eligibility across stores.

## Configuration

All parameters work as **both CLI flags and environment variables** (CLI flags override env vars):

| CLI Flag | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `--markdown` | `DEAL_CRAWLER_MARKDOWN` | `false` | Output in markdown format |
| `--sites` | `DEAL_CRAWLER_SITES` | - | Filter by site domains (comma-separated) |
| `--products` | `DEAL_CRAWLER_PRODUCTS` | - | Filter by product names (comma-separated) |
| `--plan` | `DEAL_CRAWLER_PLAN` | - | Optimize shopping plan for products (comma-separated) |
| `--optimize-for-value` | `DEAL_CRAWLER_OPTIMIZE_FOR_VALUE` | `false` | Optimize for best price per ml instead of lowest cost |
| `--all-sizes` | `DEAL_CRAWLER_ALL_SIZES` | `false` | Show all product sizes instead of best value |
| `--no-cache` | `DEAL_CRAWLER_NO_CACHE` | `false` | Bypass HTTP cache |
| `--cache-duration` | `DEAL_CRAWLER_CACHE_DURATION` | `3600` | HTTP cache lifetime in seconds |
| `--request-timeout` | `DEAL_CRAWLER_REQUEST_TIMEOUT` | `15` | HTTP request timeout in seconds |
| `--products-file` | `DEAL_CRAWLER_PRODUCTS_FILE` | `products.yml` | Path to products data file |
| `--shipping-file` | `DEAL_CRAWLER_SHIPPING_FILE` | `shipping.yaml` | Path to shipping config file |

### Advanced Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEAL_CRAWLER_MIN_PRICE` | `1.0` | Minimum valid price |
| `DEAL_CRAWLER_MAX_PRICE` | `1000.0` | Maximum valid price |
| `DEAL_CRAWLER_MAX_RETRIES` | `2` | Retry attempts for failed requests |
| `DEAL_CRAWLER_CACHE_FILE` | `.http_cache.json` | Cache file path |
| `DEAL_CRAWLER_NOTINO_DELAY_MIN` | `4.0` | Min delay for Notino (seconds) |
| `DEAL_CRAWLER_NOTINO_DELAY_MAX` | `7.0` | Max delay for Notino (seconds) |
| `DEAL_CRAWLER_DEFAULT_DELAY_MIN` | `1.0` | Min delay for other sites (seconds) |
| `DEAL_CRAWLER_DEFAULT_DELAY_MAX` | `2.0` | Max delay for other sites (seconds) |
| `DEAL_CRAWLER_RETRY_DELAY_MIN` | `5.0` | Min delay before retry (seconds) |
| `DEAL_CRAWLER_RETRY_DELAY_MAX` | `8.0` | Max delay before retry (seconds) |

## Features

- 🛒 Multi-retailer price scraping with automatic retry
- 💰 Prioritizes discounted prices
- 📦 Excludes out-of-stock products
- 🔍 Flexible filtering (sites, products, sizes)
- 🧮 **Shopping plan optimization** - Uses MILP to minimize total cost across stores
- 📊 **Value optimization** - Optimize for best price per ml instead of lowest cost
- 🚚 **Smart shipping** - Considers free shipping thresholds when optimizing
- ⚙️ Configurable via CLI flags or environment variables
- 🤖 Bot detection evasion with randomized delays
- 📊 Text and markdown output formats
- 💾 HTTP response caching (1 hour default)

## Contributing

Contributions are welcome!

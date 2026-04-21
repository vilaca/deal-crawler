# Deal Crawler

[![CI](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml/badge.svg)](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen)](https://github.com/vilaca/deal-crawler)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

Price comparison tool that scrapes product prices from multiple Portuguese retailers and finds the best deals. A Raspberry Pi collects prices daily and a GitHub Action generates reports automatically.

📊 **[View Best Prices](latest_results.md)** - Updated daily

## Quick Start

```bash
git clone https://github.com/vilaca/deal-crawler.git
cd deal-crawler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Collect all prices from all sites
python collect_all_prices.py --verbose

# Generate the best-prices report
python generate_report.py
```

## Scripts

| Script | Purpose |
|--------|---------|
| `collect_all_prices.py` | Scrapes all prices from all sites, saves to `history/all/YYYY-MM-DD.csv` |
| `generate_report.py` | Reads latest CSV and generates `latest_results.md` |
| `main.py` | Interactive CLI for querying prices, filtering, and shopping plan optimization |
| `scripts/rpi_scrape.sh` | Cron wrapper: pull, collect, commit, push |

### collect_all_prices.py

```bash
# Collect all prices (default output: history/all/)
python collect_all_prices.py

# With verbose output
python collect_all_prices.py --verbose

# Custom output directory
python collect_all_prices.py --output-dir /tmp/prices
```

### generate_report.py

```bash
# Generate report from latest CSV
python generate_report.py

# Custom input/output
python generate_report.py --input-dir history/all --output report.md
```

### main.py (interactive use)

```bash
# Find cheapest prices
python main.py

# Filter by sites and products
python main.py --sites "notino.pt,wells.pt" --products "Cerave,Medik8"

# Optimize shopping plan (minimize total cost including shipping)
python main.py --plan "Cerave,Medik8"

# Optimize for best value (price per ml) instead of lowest cost
python main.py --plan "Cerave,Medik8" --optimize-for-value

# Markdown output, bypass cache, show all sizes
python main.py --markdown --no-cache --all-sizes

# Export cheapest prices to CSV
python main.py --dump results.csv
```

## Shopping Plan Optimization

The `--plan` flag in `main.py` uses Mixed Integer Linear Programming (MILP) to find the optimal way to purchase products across multiple stores, minimizing total cost (products + shipping) or maximizing value (best price per ml with `--optimize-for-value`).

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
| `--dump` | `DEAL_CRAWLER_DUMP` | - | Export results to CSV file |
| `--verbose` | - | `false` | Show detailed progress messages |
| `--no-progress` | - | `false` | Disable progress bar |
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

## Architecture

```
+-------------------+         git push CSV          +-------------------+
|   Raspberry Pi    | ----------------------------► |      GitHub       |
|                   |                               |                   |
|  cron (daily)     |                               |  history/all/     |
|  rpi_scrape.sh    |                               |   YYYY-MM-DD.csv  |
|  collect_all_     |                               |                   |
|   prices.py       |                               +--------+----------+
+-------------------+                                        |
                                                   push triggers workflow
                                                             |
                                                    +--------▼----------+
                                                    |   GitHub Actions  |
                                                    |                   |
                                                    |  generate_        |
                                                    |   report.py       |
                                                    |       ▼           |
                                                    |  latest_results.md|
                                                    +-------------------+
```

### Data collection (Raspberry Pi)

A cron job on the RPi runs `scripts/rpi_scrape.sh` every evening. This pulls the latest code, executes `collect_all_prices.py` to scrape **all** prices from all sites (not just cheapest), saves them to `history/all/YYYY-MM-DD.csv`, and pushes the CSV to GitHub.

### Report generation (GitHub Actions)

When a new CSV is pushed to `history/all/`, the **Generate Price Report** workflow triggers automatically. It runs `generate_report.py` to read the CSV, pick the cheapest price per product, and produce `latest_results.md`.

### CI (GitHub Actions)

The **CI** workflow runs on every push and pull request. It runs tests, coverage, linting (black, flake8, pylint), type checking (mypy), docstring coverage, complexity analysis, and security audits.

## Raspberry Pi Setup

The price scraper can run on a Raspberry Pi as a daily cron job. The RPi collects all prices and pushes results to GitHub, which triggers a GitHub Action to generate the report.

### Prerequisites

- Python 3.11+
- Git with push access to the repository (SSH key recommended)

### Installation

```bash
git clone git@github.com:vilaca/deal-crawler.git
cd deal-crawler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Git configuration

```bash
git config user.name "Your Name"
git config user.email "your@email.com"
```

### Cron setup

Run `crontab -e` and add:

```cron
0 20 * * * /path/to/deal-crawler/scripts/rpi_scrape.sh
```

This runs the scraper every day at 8pm. Adjust the time as needed.

### What the script does

1. Pulls the latest code from GitHub
2. Runs `collect_all_prices.py` to scrape all prices from all sites
3. Saves results to `history/all/YYYY-MM-DD.csv`
4. Commits and pushes the CSV to GitHub
5. A GitHub Action then generates `latest_results.md` from the new data

Logs are saved to `logs/scrape-YYYY-MM-DD.log` and automatically cleaned up after 30 days.

### Manual run

```bash
# Collect all prices
python collect_all_prices.py --verbose

# Generate report from collected data
python generate_report.py
```

## Deprecated Scripts

These scripts are from the earlier architecture where a GitHub Action handled scraping. They still work but are superseded by the RPi-based pipeline.

| Script | Replaced by | Notes |
|--------|-------------|-------|
| `crawl_prices.py` | `collect_all_prices.py` | Low-level debug tool, prints tab-separated output to stdout |
| `analyze_prices.py` | `generate_report.py` | Reads old `history/*.csv` format (cheapest-only, 4 columns) |

The old `history/*.csv` files (one cheapest price per product) are preserved for historical reference. New data is collected in `history/all/*.csv` (all prices from all sites, 5 columns).

## Contributing

Contributions are welcome!

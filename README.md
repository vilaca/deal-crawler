# Deal Crawler

[![CI](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml/badge.svg)](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen)](https://github.com/vilaca/deal-crawler)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Price comparison tool that scrapes product prices from multiple Portuguese retailers and finds the best deals.

📊 **[View Best Prices](latest_results.md)**

## Quick Start

```bash
git clone https://github.com/vilaca/deal-crawler.git
cd deal-crawler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Collect prices

```bash
# All products, all sites - saves to history/all/YYYY-MM-DD.csv
./collect_all_prices.py

# Single product
./collect_all_prices.py --products "Cerave Hydrating Cleanser" --stdout

# Filter by site
./collect_all_prices.py --sites "wells.pt,atida.com" --stdout

# Combine filters
./collect_all_prices.py --products "Cerave" --sites "wells.pt" --stdout --verbose
```

### Generate report

```bash
# Generate latest_results.md from most recent CSV
python generate_report.py

# Custom input/output
python generate_report.py --input-dir history/all --output report.md
```

### Find cheapest prices (interactive)

```bash
# All products
python main.py

# Filter by sites and products
python main.py --sites "notino.pt,wells.pt" --products "Cerave,Medik8"

# Markdown output, skip cache
python main.py --markdown --no-cache
```

### Optimize shopping plan

Uses Mixed Integer Linear Programming (MILP) to minimize total cost across stores, considering shipping costs and free shipping thresholds.

```bash
# Minimize total cost (products + shipping)
python main.py --plan "Cerave,Medik8"

# Optimize for best value (price per ml)
python main.py --plan "Cerave,Medik8" --optimize-for-value
```

## Architecture

```
+-------------------+         git push CSV          +-------------------+
|   Raspberry Pi    | ----------------------------► |      GitHub       |
|                   |                               |                   |
|  cron (8am daily) |                               |  history/all/     |
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

A cron job on the Raspberry Pi runs `scripts/rpi_scrape.sh` daily. It scrapes **all** prices from all sites, saves them to `history/all/YYYY-MM-DD.csv`, and pushes to GitHub. A GitHub Action then generates `latest_results.md` with the cheapest price per product.

### Data format

The daily CSV (`history/all/YYYY-MM-DD.csv`) stores one row per product per site:

```csv
Product,Site,Price,Price per 100ml,URL
Cerave Hydrating Cleanser (1000ml),wells.pt,16.05,1.61,https://wells.pt/...
Cerave Hydrating Cleanser (1000ml),notino.pt,18.99,1.90,https://www.notino.pt/...
```

### GitHub Actions

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| **Generate Price Report** | Push to `history/all/*.csv` | Runs `generate_report.py` to update `latest_results.md` |
| **CI** | Push / Pull request | Tests, coverage, linting, type checking, security audits |

## Scripts

| Script | Purpose |
|--------|---------|
| `collect_all_prices.py` | Scrape all prices from all sites, with `--products`/`--sites`/`--stdout` filters |
| `generate_report.py` | Generate `latest_results.md` from latest CSV |
| `main.py` | Interactive CLI: cheapest prices, filtering, shopping plan optimization |
| `scripts/rpi_scrape.sh` | Cron wrapper: git pull, collect, commit, push |

## Configuration

Products and their URLs are defined in `products.yml`. Shipping costs per store are in `shipping.yaml`.

### Environment variables

All `main.py` flags also accept environment variables (CLI flags take precedence):

| Flag | Environment Variable | Default | Description |
|------|---------------------|---------|-------------|
| `--markdown` | `DEAL_CRAWLER_MARKDOWN` | `false` | Markdown output |
| `--sites` | `DEAL_CRAWLER_SITES` | - | Filter by domains |
| `--products` | `DEAL_CRAWLER_PRODUCTS` | - | Filter by product names |
| `--plan` | `DEAL_CRAWLER_PLAN` | - | Optimize shopping plan |
| `--optimize-for-value` | `DEAL_CRAWLER_OPTIMIZE_FOR_VALUE` | `false` | Optimize for price/ml |
| `--all-sizes` | `DEAL_CRAWLER_ALL_SIZES` | `false` | Show all sizes |
| `--dump` | `DEAL_CRAWLER_DUMP` | - | Export to CSV |
| `--no-cache` | `DEAL_CRAWLER_NO_CACHE` | `false` | Bypass HTTP cache |
| `--cache-duration` | `DEAL_CRAWLER_CACHE_DURATION` | `3600` | Cache TTL (seconds) |
| `--request-timeout` | `DEAL_CRAWLER_REQUEST_TIMEOUT` | `15` | HTTP timeout (seconds) |
| `--products-file` | `DEAL_CRAWLER_PRODUCTS_FILE` | `products.yml` | Products file path |
| `--shipping-file` | `DEAL_CRAWLER_SHIPPING_FILE` | `shipping.yaml` | Shipping config path |

<details>
<summary>Rate limiting and retry settings</summary>

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DEAL_CRAWLER_MIN_PRICE` | `1.0` | Minimum valid price |
| `DEAL_CRAWLER_MAX_PRICE` | `1000.0` | Maximum valid price |
| `DEAL_CRAWLER_MAX_RETRIES` | `2` | Retry attempts |
| `DEAL_CRAWLER_NOTINO_DELAY_MIN` | `4.0` | Min delay for Notino (s) |
| `DEAL_CRAWLER_NOTINO_DELAY_MAX` | `7.0` | Max delay for Notino (s) |
| `DEAL_CRAWLER_DEFAULT_DELAY_MIN` | `1.0` | Min delay for other sites (s) |
| `DEAL_CRAWLER_DEFAULT_DELAY_MAX` | `2.0` | Max delay for other sites (s) |
| `DEAL_CRAWLER_RETRY_DELAY_MIN` | `5.0` | Min retry delay (s) |
| `DEAL_CRAWLER_RETRY_DELAY_MAX` | `8.0` | Max retry delay (s) |

</details>

## Raspberry Pi Setup

### Prerequisites

- Python 3.11+
- Git with SSH push access to the repository

### Installation

```bash
git clone git@github.com:vilaca/deal-crawler.git
cd deal-crawler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
git config user.name "Your Name"
git config user.email "your@email.com"
```

### Cron setup

```bash
crontab -e
```

Add:

```cron
0 8 * * * /path/to/deal-crawler/scripts/rpi_scrape.sh
```

Logs are saved to `logs/scrape-YYYY-MM-DD.log` and cleaned up after 30 days.

## Deprecated Scripts

| Script | Replaced by | Notes |
|--------|-------------|-------|
| `crawl_prices.py` | `collect_all_prices.py` | Low-level debug tool, tab-separated stdout |
| `analyze_prices.py` | `generate_report.py` | Reads old `history/*.csv` format (cheapest-only) |

## Contributing

Contributions are welcome!

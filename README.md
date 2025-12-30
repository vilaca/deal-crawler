# Deal Crawler

[![CI](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml/badge.svg)](https://github.com/vilaca/deal-crawler/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)](https://github.com/vilaca/deal-crawler)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

Price comparison tool that scrapes product prices from multiple retailers and finds the best deals.

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/vilaca/deal-crawler.git
cd deal-crawler

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the scraper (URLs to check are configured in data.yml)
python main.py
```

## Features

- 🛒 Scrapes prices from multiple retailers with automatic retry on failures
- 💰 Prioritizes discounted prices over original prices
- 📦 Excludes out-of-stock products from comparison
- ⚙️ Configurable via environment variables
- 🤖 Smart bot detection evasion with randomized delays

## Configuration

All settings can be customized using environment variables with the `FISHER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `FISHER_MIN_PRICE` | `1.0` | Minimum valid price (filters out parsing errors) |
| `FISHER_MAX_PRICE` | `1000.0` | Maximum valid price (filters out parsing errors) |
| `FISHER_REQUEST_TIMEOUT` | `15` | HTTP request timeout in seconds |
| `FISHER_MAX_RETRIES` | `2` | Number of retry attempts for failed requests |
| `FISHER_NOTINO_DELAY_MIN` | `4.0` | Minimum delay before Notino requests (seconds) |
| `FISHER_NOTINO_DELAY_MAX` | `7.0` | Maximum delay before Notino requests (seconds) |
| `FISHER_DEFAULT_DELAY_MIN` | `1.0` | Minimum delay before other site requests (seconds) |
| `FISHER_DEFAULT_DELAY_MAX` | `2.0` | Maximum delay before other site requests (seconds) |
| `FISHER_RETRY_DELAY_MIN` | `5.0` | Minimum delay before retry attempts (seconds) |
| `FISHER_RETRY_DELAY_MAX` | `8.0` | Maximum delay before retry attempts (seconds) |


## Contributing

Contributions are welcome! 

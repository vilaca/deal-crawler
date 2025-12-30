# Deal Crawler

Price comparison tool that scrapes product prices from multiple retailers and finds the best deals.

**Repository**: https://github.com/vilaca/deal-crawler

## Features

- 🛒 Scrapes prices from multiple retailers with automatic retry on failures
- 💰 Prioritizes discounted prices over original prices
- 📦 Excludes out-of-stock products from comparison
- 🌐 Supports notino.pt (JSON/Brotli), farmacia365.pt, atida.com, sabina.com, wells.pt

## Project Structure

```
deal-crawler/
├── config.py              # Configuration (defaults + env vars)
├── http_client.py         # HTTP operations and session management
├── extractors.py          # Price extraction strategies
├── stock_checker.py       # Stock availability detection
├── data_loader.py         # YAML file loading
├── finder.py              # Price comparison logic
├── main.py                # CLI entry point
├── test_*.py              # Module-specific tests (74 tests total)
└── data.yml               # Product URLs configuration
```

## How It Works

**Price extraction:** Checks data attributes, meta tags, and CSS classes. Prioritizes `price-actual`/`price-sale` over `price-original`/`price-old`.

**Stock detection:** Parses availability meta tags and text patterns (out of stock, esgotado, etc.)

**Anti-bot handling:** Brotli compression support, randomized delays (2-4s), automatic retry on 403 errors, persistent sessions.

## Dependencies

Install with: `pip install -r requirements.txt`

**Production:** requests, beautifulsoup4, pyyaml, lxml, brotli

**Development:** pytest, pytest-cov, flake8, black, mypy

**Development tools:**

Quick commands (Makefile):
```bash
make help          # Show all available commands
make test          # Run all tests
make coverage      # Run tests with coverage report
make lint          # Check code style (flake8)
make typecheck     # Run type checking (mypy)
make security      # Run security checks (bandit, pip-audit)
make quality       # Run code quality checks (vulture, interrogate)
make check-all     # Run all checks
```

Individual tools:
```bash
pytest test_*.py -v                                    # Run tests with pytest
pytest --cov=. --cov-report=html                       # Measure coverage
flake8 *.py                                            # Check code style
black *.py                                             # Format code
mypy *.py --ignore-missing-imports                     # Type check
```

Automation:
```bash
./check.sh                                             # Run all checks via shell script
pre-commit install                                     # Install git pre-commit hooks
pre-commit run --all-files                             # Run pre-commit checks manually
```

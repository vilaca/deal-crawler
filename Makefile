.PHONY: help install test coverage format format-check lint typecheck security quality check-all clean

help:
	@echo "Available targets (activate venv first: source venv/bin/activate):"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run all tests"
	@echo "  make coverage     - Run tests with coverage report"
	@echo "  make format       - Format code with black"
	@echo "  make format-check - Check if code is black-formatted (no changes)"
	@echo "  make lint         - Run code style checks (flake8 + black + pylint)"
	@echo "  make typecheck    - Run type checking (mypy)"
	@echo "  make security     - Run security checks (bandit, pip-audit)"
	@echo "  make quality      - Run code quality checks (vulture, interrogate)"
	@echo "  make check-all    - Run all checks (format, lint, typecheck, security, quality, test)"
	@echo "  make clean        - Clean up temporary files"

install:
	pip install -r requirements.txt

test:
	python3 -m unittest discover -s test -p 'test_*.py' -v

coverage:
	pytest --cov=utils --cov-report=html --cov-report=term
	@echo "\nHTML coverage report generated in htmlcov/index.html"

format:
	@echo "Formatting code with black..."
	black main.py utils/*.py test/*.py

format-check:
	@echo "Checking code formatting with black..."
	black --check main.py utils/*.py test/*.py

lint: format-check
	@echo "Running flake8..."
	flake8 main.py utils/*.py test/*.py
	@echo "\nRunning pylint..."
	@pylint main.py utils/*.py --score=y || true

typecheck:
	@echo "Running mypy..."
	mypy main.py utils/*.py test/*.py --ignore-missing-imports

security:
	@echo "Running bandit (code security analysis)..."
	@bandit -r main.py utils test -ll || true
	@echo "\nRunning pip-audit (dependency vulnerabilities)..."
	@pip-audit || true

quality:
	@echo "Running vulture (dead code detection)..."
	@vulture main.py utils test --min-confidence 100 || true
	@echo "\nRunning interrogate (docstring coverage)..."
	@interrogate -v main.py utils test

check-all: format-check lint typecheck quality security test
	@echo "\n✅ All checks completed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache
	@echo "Cleaned up temporary files"

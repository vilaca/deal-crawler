.PHONY: help install test coverage lint typecheck security quality check-all clean

help:
	@echo "Available targets:"
	@echo "  make install      - Install dependencies"
	@echo "  make test         - Run all tests"
	@echo "  make coverage     - Run tests with coverage report"
	@echo "  make lint         - Run code style checks (flake8)"
	@echo "  make typecheck    - Run type checking (mypy)"
	@echo "  make security     - Run security checks (bandit, pip-audit)"
	@echo "  make quality      - Run code quality checks (vulture, interrogate)"
	@echo "  make check-all    - Run all checks (lint, typecheck, security, quality, test)"
	@echo "  make clean        - Clean up temporary files"

install:
	pip install -r requirements.txt
	pip install -q bandit interrogate vulture pip-audit

test:
	python3 -m unittest discover -s . -p 'test_*.py' -v

coverage:
	pytest --cov=. --cov-report=html --cov-report=term
	@echo "\nHTML coverage report generated in htmlcov/index.html"

lint:
	@echo "Running flake8..."
	flake8 *.py

typecheck:
	@echo "Running mypy..."
	mypy *.py --ignore-missing-imports

security:
	@echo "Running bandit (code security analysis)..."
	@bandit -r *.py -ll || true
	@echo "\nRunning pip-audit (dependency vulnerabilities)..."
	@pip-audit || true

quality:
	@echo "Running vulture (dead code detection)..."
	@vulture *.py --min-confidence 100 || true
	@echo "\nRunning interrogate (docstring coverage)..."
	@interrogate -v *.py

check-all: lint typecheck quality security test
	@echo "\n✅ All checks completed!"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache
	@echo "Cleaned up temporary files"

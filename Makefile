.PHONY: help install test lint format clean

help:
	@echo "Available commands:"
	@echo "  make install  - Install the package for development"
	@echo "  make test     - Run tests with pytest"
	@echo "  make lint     - Run flake8 and mypy"
	@echo "  make format   - Run black and isort"
	@echo "  make clean    - Remove build and cache files"

install:
	pip install -e .[dev]
	pre-commit install

test:
	pytest

lint:
	flake8 src/ tests/
	mypy src/ tests/

format:
	black src/ tests/
	isort src/ tests/

clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf build
	rm -rf dist
	rm -rf src/*.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +

.PHONY: lint format fix add commit scraper-dataset help

help:
	@echo "Available commands:"
	@echo "  make lint    - Check code with ruff"
	@echo "  make format  - Format code with ruff"
	@echo "  make fix     - Auto-fix linting issues"
	@echo "  make add     - Stage all changes for commit"
	@echo "  make commit  - Interactive commit with commitizen"
	@echo "  make scraper-dataset - Run the scraper to generate dataset"
	@echo "  make help    - Show this help message"

lint:
	uv run ruff check .
format:
	uv run ruff format .
fix:
	uv run ruff check . --fix
add:
	git add .
commit:
	uv run cz commit
scraper-dataset:
	uv run python -m scraper.scrape
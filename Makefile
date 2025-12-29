.PHONY: scraper-dataset lint format fix add commit help

help:
	@echo "Available commands:"
	@echo "  make scraper-dataset - Run the scraper to generate dataset"
	@echo "  make lint    - Check code with ruff"
	@echo "  make format  - Format code with ruff"
	@echo "  make fix     - Auto-fix linting issues"
	@echo "  make add     - Stage all changes for commit"
	@echo "  make commit  - Interactive commit with commitizen"
	@echo "  make help    - Show this help message"

scraper-dataset:
	uv run python -m scraper.scrape
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

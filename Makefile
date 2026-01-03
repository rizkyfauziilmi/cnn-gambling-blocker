.PHONY: scraper-dataset lint format fix add commit help

help:
	@echo "Available commands:"
	@echo "  make scraper-dataset - Run the scraper to generate dataset"
	@echo "  make validate-dataset - Validate the generated dataset"
	@echo "  make format-dataset   - Format dataset filenames"
	@echo "  make generate-txt   - Generate dataset text files"
	@echo "  make lint    - Check code with ruff"
	@echo "  make format  - Format code with ruff"
	@echo "  make fix     - Auto-fix linting issues"
	@echo "  make add     - Stage all changes for commit"
	@echo "  make commit  - Interactive commit with commitizen"
	@echo "  make help    - Show this help message"

scraper-dataset:
	uv run python -m scraper.scrape
validate-dataset:
	uv run python -m scraper.validate_dataset
format-dataset:
	uv run python -m scraper.format_dataset
generate-txt:
	uv run python -m scraper.generate_txt
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

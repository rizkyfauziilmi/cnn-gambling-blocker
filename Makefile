.PHONY: lint format fix commit help

help:
	@echo "Available commands:"
	@echo "  make lint    - Check code with ruff"
	@echo "  make format  - Format code with ruff"
	@echo "  make fix     - Auto-fix linting issues"
	@echo "  make add     - Stage all changes for commit"
	@echo "  make commit  - Interactive commit with commitizen"

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

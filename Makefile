.PHONY: docs docs-serve lint test build bump-patch bump-minor bump-major

docs:
	uv run pdoc -o docs/api src/pysaj

docs-serve:
	uv run pdoc src/pysaj

lint:
	uv run ruff check .

test:
	uv run python -m pytest -q

build:
	uv build
	uv run twine check dist/*

# Patch bump (done automatically by CI on every push to main)
bump-patch:
	uv run bump-my-version bump patch

bump-minor:
	uv run bump-my-version bump minor

bump-major:
	uv run bump-my-version bump major

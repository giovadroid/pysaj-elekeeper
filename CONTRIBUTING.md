# Contributing

PySaj targets a narrow use case (SAJ Elekeeper API) and the upstream API is
private and undocumented. Contributions are welcome but the scope is intentionally
small.

## Getting started

```bash
git clone https://github.com/giovadroid/pysaj.git
cd pysaj-elekeeper
uv sync --extra dev
```

Copy `.env.example` to `.env` and fill in your credentials to run the examples
against a real account:

```bash
python examples/sample.py
python examples/plant_summary.py
```

## Before opening a PR

```bash
uv run ruff check .
uv run python -m pytest -q
uv build
uv run twine check dist/*
```

All four must pass. CI will enforce the same checks.

## What to contribute

- New wrapped endpoints (follow the pattern in `elekeeper/client.py`).
- Bug fixes or corrections to existing wrappers.
- Additional typed fields on response models.

If you are unsure whether something fits, open an issue first.

## License

By contributing you agree your code will be released under the MIT license.

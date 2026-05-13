# Security

PySaj reads SAJ credentials from environment variables (`SAJ_USER`, `SAJ_PASS`).
Never commit `.env` files, bearer tokens, or live API payloads — the project
already excludes them via `.gitignore`.

To report a vulnerability, open a [GitHub Security Advisory](https://github.com/giovadroid/pysaj-elekeeper/security/advisories/new).

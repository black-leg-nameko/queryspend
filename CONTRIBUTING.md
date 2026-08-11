# Contributing to queryspend

Thanks for helping make pre-merge warehouse cost review safer and more useful.

queryspend is alpha software. Keep changes small, evidence-backed, and honest about unknowns. A
contribution must not weaken the dry-run-only, no-raw-SQL, or fail-closed input invariants.

## Development setup

Prerequisites: Git and [uv](https://docs.astral.sh/uv/getting-started/installation/).

```bash
git clone https://github.com/queryspend/queryspend.git
cd queryspend
uv sync --extra dev --locked
uv run queryspend demo
uv run pytest
```

The first demo is credential-free and uses explicitly synthetic fixtures. Live BigQuery tests are
not part of the default contributor path.

## Before opening a pull request

```bash
uv run ruff check .
uv run mypy queryspend
uv run pytest --cov=queryspend --cov-report=term-missing --cov-fail-under=90
uv build
```

Also run the focused privacy and security tests when touching parsing, paths, rendering, providers,
or the Action adapter:

```bash
uv run pytest tests/test_artifacts_graph.py tests/test_config.py tests/test_provider.py tests/test_github_action.py
```

## Contribution workflow

- Bugs: use the bug report and include a minimal sanitized reproduction.
- Security issues: follow [SECURITY.md](SECURITY.md); do not open a public issue.
- Features: open a feature request before a large implementation.
- Starter work: see [docs/GOOD_FIRST_ISSUES.md](docs/GOOD_FIRST_ISSUES.md).
- Keep one concern per pull request and add tests for behavior changes.
- Use English commit messages; Conventional Commit prefixes are welcome.
- Update schemas and compatibility tests for any public contract change.

Never attach raw production SQL, manifests, credentials, provider errors, billing project IDs, or
client names to an issue. Replace them with the smallest synthetic fixture that reproduces the
behavior.

## Review contract

Maintainers check correctness, tests, typing, threat-model impact, documentation, and compatibility.
Schema v1 changes are additive only. Changes that turn unknowns into zero, fetch result rows, execute
non-SELECT statements, emit SQL/literals, or put credentials into PR-editable workflows will not be
accepted.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Contributions are
licensed under [Apache-2.0](LICENSE).

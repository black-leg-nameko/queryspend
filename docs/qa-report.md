# queryspend Phase 3 QA report

- Verification date: 2026-08-11 JST
- Scope: launch-grade CLI/Action prototype from `docs/SPEC.md`
- UI/design source: **N/A — no Web UI or mobile UI; `DESIGN.md` is intentionally absent**
- Runtime used: CPython 3.14 development environment; package declares Python 3.11+ and the CI
  matrix targets Python 3.11–3.13

## Outcome

The offline core is touchable end to end: a clean wheel install can run the credential-free demo,
base/head manifests normalize and diff, downstream uncertainty remains unknown, one report object
renders to terminal/Markdown/JSON, technical-gate validation is reproducible, and the Action adapter
produces the same decision/output fields. Live BigQuery was not tested because this environment has
no ADC/OIDC credential; the CLI returned the specified sanitized exit code 4 and wrote a partial
diagnostic report.

## Verification matrix

| Surface / state | Result | Evidence |
|---|---|---|
| Credential-free demo / success+partial | Pass, exit 0; simulated disclosure, two known + three unknown | `artifacts/verification/demo.log` |
| Clean wheel install | Pass, demo 0.52 seconds after install | `artifacts/verification/wheel-clean-venv-smoke.log` |
| `check` empty/no change | Pass, exit 0, zero provider calls by contract test | `artifacts/verification/check-empty.log` |
| `check` partial unknown | Pass, exit 0, view consumer reason and no false `$0` | `artifacts/verification/check-partial-unknown.log` |
| `check` invalid cycle | Pass, safe error and exit 2 | `artifacts/verification/check-invalid-cycle.log` |
| `check` no live credential | Expected safe failure, exit 4, partial report, SQL absent | `artifacts/verification/check-live-unavailable.log` |
| Markdown render | Pass, stable marker and five-column evidence table | `artifacts/verification/render-markdown.log` |
| Cost Change Manifest JSON | Pass, schema-valid in tests; no raw SQL field | `schemas/report/v1.json`, pytest log |
| Validation evaluator | Pass on explicitly synthetic 10-case corpus | `artifacts/verification/validate.log` |
| Action adapter | Pass local harness; outputs/summary/comment golden generated | `artifacts/verification/action-local-harness.log` |
| Tests/coverage | 69 passed; 91.70% total coverage, required 90% reached | `artifacts/verification/pytest-coverage.log` |
| Ruff / mypy strict | Pass | `artifacts/verification/static-analysis.log` |
| sdist / wheel | Pass | `artifacts/verification/packaging.log` |

## State and safety self-review

- Empty: identical manifests return `PASS`, `no_changed_models`, zero affected, and no provider
  construction/call.
- Partial/unknown: changed view and unchanged downstream models retain reason codes and null cost;
  known numbers are labeled subtotal.
- Error: invalid graph returns exit 2; no ADC returns exit 4 with permission remediation and a
  sanitized partial report; no stack trace or provider raw text is shown.
- Success: synthetic table changes render positive increase and negative saving from the same
  Decimal report/policy object.
- Offline: the bundled demo and validation evaluator need only local package data.
- Accessibility: status uses text labels and units, not color/emoji; v1 emits no ANSI; Markdown has
  a visible decision and a five-column table.
- Privacy: report schema has no raw SQL field; reports set `privacy.sql_included=false`; fixture,
  logs, comments, and output artifacts contain hashes/reason codes rather than SQL or credentials.
- Provider invariant: contract tests assert `dry_run=True`, `use_query_cache=False`, no result fetch,
  retry/error classification, and raw literal non-disclosure.
- Untrusted inputs: YAML safe loader, strict unknown keys, quoted decimals, JSON duplicate-key
  rejection, 100 MiB/100k node/2 MiB SQL limits, graph validation, Markdown/control escaping, and
  Action workspace path confinement are exercised.

## Validation caveat

The checked-in validation observation source is `synthetic_fixture_not_live`. Its passing median
APE 4.50%, p90 5.56%, cost-weighted attribution 99.29%, false blockers 0%, and coverage 88.89%
validate the evaluator and exclusion/accounting logic only. They are not evidence of live warehouse
prediction accuracy.

## Known gaps before production/public launch

1. Run live BigQuery tests with user/maintainer-owned ADC and GitHub OIDC in an isolated on-demand
   project; verify Job User + dataset-level Data Viewer and capture audit-log proof of zero
   result-producing/write jobs.
2. Replace synthetic accuracy observations with the frozen 3-project/10-PR scheduled-run truth
   protocol before treating the technical-gate metrics as product accuracy.
3. Run the composite Action on an actual same-repository PR to verify check naming, job summary,
   idempotent update, stale-head behavior, read-only token fallback, and artifact upload in GitHub.
4. Complete the mandated defensive security review before public launch (Gate C).

## Run locally

```bash
uv sync --extra dev
uv run queryspend demo
uv run pytest --cov=queryspend --cov-report=term-missing --cov-fail-under=90
uv run ruff check .
uv run mypy queryspend
uv build
```

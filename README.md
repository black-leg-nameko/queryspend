# queryspend

**See the recurring BigQuery cost delta of a dbt pull request before merge.**

[![CI](https://github.com/black-leg-nameko/queryspend/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/black-leg-nameko/queryspend/actions/workflows/ci.yml)
[![Python 3.11–3.13](https://img.shields.io/badge/python-3.11%E2%80%933.13-3776AB.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-0B7285.svg)](LICENSE)

![Terminal demo: queryspend labels a synthetic dbt pull request WARN, shows a known monthly BigQuery cost subtotal increase of 487.50 USD, and keeps three uncertain models unknown.](assets/demo.gif)

Prefer a still image? See the [static demo frame](assets/demo.png). The demo is synthetic and
credential-free; it is not a live BigQuery result or an accuracy benchmark.

## Quickstart — synthetic result in under 60 seconds

With [uv](https://docs.astral.sh/uv/getting-started/installation/) installed:

```bash
git clone https://github.com/black-leg-nameko/queryspend.git
cd queryspend
uv run queryspend demo
```

The clean-environment timing and exact reproduction procedure are recorded in
[`launch/repo-audit.md`](launch/repo-audit.md). No Google credential or configuration is needed.

queryspend combines base/head dbt manifests, semantic lineage, explicit run frequency,
explicit on-demand pricing, and BigQuery dry-run evidence. Unsupported or unsafe estimates
stay `unknown`; they are never presented as `$0`.

> Alpha: the offline core is runnable. Live BigQuery accuracy and least-privilege OIDC must
> still be validated in a credentialed isolated project before production use.

The bundled `northstar_retail` scenario is synthetic and always starts with this disclosure:

```text
SIMULATED DEMO — not a live BigQuery estimate
QUERYSPEND — ESTIMATE, NOT AN INVOICE
Decision: WARN (usd threshold exceeded)
Known monthly subtotal increase: +487.50 USD/month
Coverage: 2 known / 5 affected; 3 not known
Confidence: high
Largest known contributor: model.northstar_retail.fct_orders (+675.00 USD/month)
```

The report also shows a `-$187.50/month` saving and refuses to estimate two downstream models
or a changed view. Recorded demo evidence has `fixture=true`; it is not an accuracy claim.

For development:

```bash
uv sync --extra dev
uv run queryspend demo
```

## Why queryspend

| Approach | Before merge | Recurring monthly delta | Lineage-aware uncertainty | Needs query text outside your environment |
|---|:---:|:---:|:---:|:---:|
| `bq query --dry_run` per statement | Yes | No | No | No |
| dbt CI compile/run | Yes | No | No | Depends on your setup |
| Billing export / query history | No | Retrospective | No | No |
| **queryspend** | **Yes** | **Known subtotal** | **Yes; unsafe cases stay unknown** | **No** |

queryspend is deliberately narrower than a warehouse observability platform: it turns two dbt
artifacts plus explicit schedule/pricing assumptions into one reviewable PR policy decision.

## What is supported

| Input/case | MVP result |
|---|---|
| dbt manifest schema v10, v11, v12 | Normalized into one internal contract |
| BigQuery on-demand `table` model | Base/head dry-run and recurring Decimal estimate |
| Added/deleted `table` | One side is explicit zero; confidence is medium |
| `view` change | `unknown_view_consumer_cost`, not `$0` |
| Unchanged downstream SQL | `unknown_downstream_data_shape`, not `$0` |
| `incremental`, `ephemeral`, Python, seed, snapshot | `unsupported_materialization` |
| Missing explicit frequency | Per-run bytes retained; monthly value is unknown |
| Missing explicit price | Monthly bytes retained; USD value is unknown |
| External/federated or unsafe query evidence | Unknown with a stable reason code |
| BigQuery reservation/capacity pricing | Unsupported; no on-demand dollar extrapolation |

Snowflake, Databricks, Redshift, dashboards, SQL rewriting, and AI optimization are deliberate
non-goals. queryspend does not compile dbt projects; callers provide both artifacts.

## Configure explicit assumptions

Copy [`examples/queryspend.yml`](examples/queryspend.yml) to `.queryspend.yml` and change every
example value you rely on. queryspend never fetches a live list price and never converts cron.
YAML decimals must be quoted so money is never parsed through a binary float.

```yaml
version: 1
warehouse:
  provider: bigquery
  billing_model: on_demand
  billing_project: analytics-ci
  location: US
  price_per_tib_usd: "6.25" # example only
frequencies:
  default_runs_per_month: null
  models:
    model.analytics.fct_orders: "720"
policy:
  max_monthly_delta_usd: "500.00"
  action: block
  minimum_confidence: high
  unknown_behavior: warn
```

Frequency priority is exact config model, dbt
`config.meta.queryspend.runs_per_month`, explicit config default, then unknown. A config override is
recorded in evidence. Unknown keys, YAML numeric floats, negative values, NaN, and Infinity fail
closed with exit code 2.

## Run a real check

Create base and head artifacts in separate unprivileged steps, then authenticate with Application
Default Credentials:

```bash
queryspend check \
  --base path/to/base/manifest.json \
  --head path/to/head/manifest.json \
  --config .queryspend.yml \
  --output queryspend-report.json

queryspend render \
  --input queryspend-report.json \
  --format markdown
```

`--format json` writes JSON only to stdout. The report path is written through an owner-only temp
file, `fsync`, and atomic replace for pass, partial unknown, and policy block. `NO_COLOR`, non-TTY,
and `TERM=dumb` are safe because v1 emits no semantic ANSI or emoji.

### Exit codes

| Code | Meaning |
|---:|---|
| 0 | Evaluation completed: pass, warn, or default non-blocking unknown |
| 2 | CLI usage, config, or manifest invalid |
| 3 | Policy decision is block |
| 4 | Global authentication/authorization failure |
| 5 | Every eligible provider request failed after retry |
| 6 | Internal invariant or unexpected failure |

Per-model permission/provider failures remain reasoned diagnostics when other models succeed. If
every eligible request fails, a sanitized partial report is still written when possible.

## Dry-run-only security invariant

The production provider has one query call path. Every request uses:

```python
bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
```

It never calls `QueryJob.result()`, fetches rows, or implements load, extract, copy, DDL, DML, or
script execution. Statement types other than `SELECT` are unsupported even though BigQuery only
received a dry-run request. Same-run requests are cached by billing project, location, and SQL hash.
Only 429 and 5xx failures retry (three attempts); raw provider messages are discarded.

SQL is sent from the runner to the user's BigQuery API for validation. It is never sent to a
queryspend server. JSON, logs, Markdown, and comments contain the normalized SQL SHA-256 only—no
SQL text, literal, credential, relation name (by default), or raw provider error. This package has
no analytics/telemetry endpoint.

### Least privilege

Use a dedicated principal:

- billing/job project: `roles/bigquery.jobUser`;
- only referenced datasets/tables/views: dataset-level `roles/bigquery.dataViewer`;
- no Editor, Owner, BigQuery Admin, reservation, connection, or billing-account role;
- local auth through ADC; CI auth through GitHub OIDC + Google Workload Identity Federation;
- no long-lived service-account JSON key in config or Action inputs.

Restrict the Workload Identity Provider attribute condition to repository/owner IDs and the
trusted event/ref. See Google's and GitHub's current OIDC documentation before production rollout.

## GitHub Action: keep PR code away from cloud credentials

The Action consumes artifacts; it does not run `dbt compile`. Do not put compilation and OIDC in
one PR-editable workflow, and do not use `pull_request_target`.

Use the two-workflow pattern:

1. [`prepare-queryspend-manifests.yml`](examples/workflows/prepare-queryspend-manifests.yml) runs on
   `pull_request`, with `contents: read`, no cloud credential, and uploads base/head JSON as data.
2. [`evaluate-queryspend.yml`](examples/workflows/evaluate-queryspend.yml) is loaded from the
   default branch on `workflow_run`, verifies workflow/repository/event/head SHA, then obtains OIDC
   and invokes the locally checked-out Action. External Actions are pinned to full commit SHAs.

The evaluator needs `contents: read`, `actions: read`, and `id-token: write`; add
`pull-requests: write` only for same-repository comments. Forks skip cloud auth/comment by default.
Comment failure never changes the cost decision: the job summary and JSON artifact remain. The
marker `<!-- queryspend-report:v1 -->` updates the existing bot comment instead of duplicating it.
Configure the example's `queryspend-cost` environment with required reviewers and prevent
self-review; approval is required before PR-produced SQL reaches a credentialed dry-run.

For a published release, pin queryspend itself to a reviewed 40-character commit SHA rather than a
movable tag. The checked-in example uses `uses: ./` after checking out the trusted default branch
because this repository does not yet have a public release SHA.

## Cost Change Manifest JSON v1 and Python API

CLI, Python API, Action, terminal, Markdown, and JSON all consume the same policy decision:

```python
from queryspend import EvaluationRequest, evaluate

report = evaluate(
    EvaluationRequest(
        base_manifest="base/manifest.json",
        head_manifest="head/manifest.json",
        config=".queryspend.yml",
    )
)
print(report.policy.decision)
```

Canonical schemas are checked in under [`schemas/`](schemas/):

- `report/v1.json` — Cost Change Manifest;
- `config/v1.json` — strict config;
- `observation/v1.json` — validation ground truth;
- `validation/v1.json` — technical gate result.

Schema v1 changes are additive only. Unknown numeric fields are JSON `null`; money and monthly bytes
are six-place decimal strings. Raw SQL has no field in the schema.

## Reproduce the validation evaluator

```bash
queryspend validate \
  --predictions 'validation/predictions/*.json' \
  --observations validation/observations.jsonl \
  --output validation-report.json
```

The immutable `technical-gate-v1` checks at least eight eligible APE cases, median APE ≤15%, p90
APE ≤30%, cost-weighted attribution ≥80%, and money false blockers ≤5%. Actual zero cases are not
divided by zero; unknown predictions reduce coverage/attribution instead of silently disappearing.

The checked-in 3-project/10-case corpus is **synthetic evaluator test data**, identified by
`source: synthetic_fixture_not_live`. Its passing metrics prove evaluator reproducibility, not live
BigQuery accuracy. Production readiness still requires scheduled isolated-project observations and
audit-log confirmation that queryspend produced zero result/write jobs.

## Development and verification

```bash
uv sync --extra dev
uv run queryspend demo
uv run pytest --cov=queryspend --cov-report=term-missing --cov-fail-under=90
uv run ruff check .
uv run mypy queryspend
uv build
```

Provider contract tests cover success, cache, dry-run flags, 400/401/403/429/5xx/timeout, external
sources, location mismatch, and SQL/literal non-disclosure. A credentialed live BigQuery test is
intentionally not run in ordinary/fork CI.

## Honest status

- Offline core, demo, semantic diff/lineage, policy, three renderers, validation evaluator, and
  composite Action are implemented and tested.
- Web UI/mobile UI is a non-goal; `DESIGN.md` and screenshot QA are not applicable.
- The checked-in validation corpus is synthetic. No claim of real-world ≤15% error follows from it.
- The [defensive review](docs/SECURITY_REVIEW.md) has no open Critical, High, or code-level Medium
  findings; its live-integration residual risks still apply.
- Live ADC/OIDC, dataset-level least privilege, BigQuery audit-log zero-write evidence, and measured
  actual-vs-predicted accuracy remain mandatory before calling this production-ready.

## Documentation and roadmap

- [GitHub Action setup](docs/GITHUB_ACTION.md)
- [Security model and private vulnerability reporting](SECURITY.md)
- [Defensive security review](docs/SECURITY_REVIEW.md)
- [Release process](docs/RELEASING.md)
- [Roadmap and production-readiness gates](docs/ROADMAP.md)
- [Contributing](CONTRIBUTING.md) and [good first issue candidates](docs/GOOD_FIRST_ISSUES.md)

## License

[Apache-2.0](LICENSE). Contributions should preserve the dry-run-only and no-raw-SQL invariants.

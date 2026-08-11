# queryspend v0.1.0 — draft release notes

queryspend estimates the recurring on-demand BigQuery cost delta of a dbt pull request before merge.

## Included

- Credential-free synthetic demo
- dbt manifest v10–v12 normalization and lineage-aware affected-model analysis
- BigQuery dry-run provider with explicit pricing/frequency assumptions
- Stable Cost Change Manifest JSON v1 plus terminal and Markdown renderers
- Policy decisions and CI-friendly exit codes
- Composite GitHub Action and a trusted two-workflow OIDC pattern
- Reproducible synthetic validation evaluator

## Important alpha limits

Live BigQuery ADC/OIDC, dataset-level least privilege, audit-log zero-write evidence, and an actual
GitHub-hosted Action run are not yet verified. The checked-in validation corpus is synthetic and does
not establish real-world prediction accuracy. Capacity/reservation pricing and non-BigQuery
warehouses are unsupported.

Start without credentials:

```bash
uv run queryspend demo
```

See `README.md`, `SECURITY.md`, and `docs/ROADMAP.md` before production evaluation.

# Roadmap

queryspend is intentionally alpha. The roadmap favors verified safety and usefulness over provider
breadth.

## v0.1 — launch candidate

- [x] Credential-free synthetic demo and offline evaluation core
- [x] dbt manifest v10–v12 normalization, semantic lineage, and explicit unknown reasons
- [x] BigQuery dry-run provider contract and GitHub Action adapter
- [x] Stable JSON schema, Markdown/terminal renderers, policy exit codes, and 90% coverage gate
- [ ] Live ADC least-privilege run in an isolated BigQuery project
- [ ] GitHub-hosted same-repository OIDC/Action verification
- [ ] BigQuery audit-log proof that no result-producing or write jobs occurred

## v0.2 — evidence, not breadth

- Publish real, consented, reproducible actual-vs-predicted observations from the frozen validation
  protocol
- Improve diagnostics for the highest-frequency unknown reason codes without turning uncertainty
  into false precision
- Harden release provenance and document compatibility policy from launch feedback

## Later, only after evidence

- Evaluate reservation/capacity cost semantics separately from on-demand pricing
- Evaluate other warehouses only if user evidence shows the BigQuery wedge is validated

Snowflake, Databricks, Redshift, dashboards, SQL rewriting, and AI optimization remain explicit v0.1
non-goals. See [`docs/SPEC.md`](SPEC.md) for the implementation contract.

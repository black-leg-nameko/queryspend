# GitHub Action setup

queryspend intentionally separates untrusted pull-request compilation from cloud authentication.
Copy and adapt both examples:

1. [`prepare-queryspend-manifests.yml`](../examples/workflows/prepare-queryspend-manifests.yml) runs
   PR-controlled dbt compilation without cloud credentials and uploads manifests as untrusted data.
2. [`evaluate-queryspend.yml`](../examples/workflows/evaluate-queryspend.yml) is loaded from the
   default branch on `workflow_run`, verifies producer context before OIDC, and evaluates the data.

Before use, replace every placeholder, pin queryspend to a reviewed 40-character commit, and add a
Workload Identity Provider condition restricted to the immutable GitHub owner/repository IDs and the
intended event/ref. Grant only `roles/bigquery.jobUser` on the billing project and dataset-level
`roles/bigquery.dataViewer` for referenced data.

Create a protected GitHub Environment named `queryspend-cost`, require reviewers, prevent
self-review, and allow only the intended protected branch. The uncredentialed `verify-input` job
first verifies and re-uploads the exact artifact, logging its upstream head SHA. Inspect that log
before approving the dependent `queryspend-cost` environment. The evaluator requests OIDC only
after approval. A same-repository collaborator can otherwise submit an arbitrary compiled `SELECT`
in a manifest and use byte/table metadata as an oracle over every dataset the principal can view.
Keep the principal's dataset allowlist narrow even with approval.

Do not combine compilation and OIDC, use `pull_request_target`, accept arbitrary artifact run IDs,
store service-account JSON, or grant Editor/Owner/BigQuery Admin. Fork pull requests are skipped by
the example evaluator. Treat manifests as attacker-controlled data, not as proof that dbt produced
them; the example verifies the exact artifact file set, context, size, repository, event, and head
SHA before OIDC, then relies on the protected-environment approval for the trust decision.

Live OIDC and GitHub-hosted Action behavior are not yet verified. Treat the examples as reviewed
configuration starting points, not proof of a production integration.

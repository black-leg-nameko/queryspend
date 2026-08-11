# Security policy

## Reporting a vulnerability

Do not open a public issue or include secrets, raw SQL, production manifests, or client data in a
report. Use the repository's **Security** tab and choose **Report a vulnerability** to open a private
GitHub Security Advisory:

<https://github.com/queryspend/queryspend/security/advisories/new>

Include the affected version, impact, minimal sanitized reproduction, and suggested remediation if
known. Expect acknowledgement within 72 hours and a status update within seven days. Please allow a
reasonable remediation window before disclosure.

If private reporting is not available yet, do not publish details; wait for the repository owner to
enable private vulnerability reporting. No public fallback address is claimed before launch.

## Supported versions

queryspend is alpha software. Until a stable release, only the latest `0.x` release receives security
fixes.

| Version | Supported |
|---|:---:|
| Latest `0.x` | Yes |
| Older `0.x` | No |

## Security boundaries

- BigQuery requests must remain `dry_run=True` and `use_query_cache=False`; query results are never
  fetched.
- Raw SQL, SQL literals, credentials, relation names by default, and provider error text must not
  enter reports, comments, summaries, or logs.
- dbt manifests and configuration are untrusted input with size, structure, graph, and path limits.
- GitHub credentials must not be exposed to pull-request-controlled code. Follow the trusted
  two-workflow pattern in [docs/GITHUB_ACTION.md](docs/GITHUB_ACTION.md).

The defensive review and residual risks are recorded in
[`docs/SECURITY_REVIEW.md`](docs/SECURITY_REVIEW.md).

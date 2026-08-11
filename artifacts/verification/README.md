# Gate B verification evidence

All evidence below was generated locally on 2026-08-11 JST. No raw SQL or credential is intended
to be present in any report/log/comment artifact.

| Artifact | Purpose |
|---|---|
| `demo.log`, `demo-report.json` | Credential-free core flow with known/saving/unknown states |
| `check-empty.log`, `empty-report.json` | Empty/no-change state |
| `check-partial-unknown.log`, `partial-unknown-report.json` | Recoverable partial unknown state |
| `check-invalid-cycle.log` | Invalid artifact error and exit code 2 |
| `check-live-unavailable.log`, `live-unavailable-partial-report.json` | No-ADC error, exit 4, safe partial report |
| `render-markdown.log` | Provider-free renderer output |
| `validate.log`, `validation-report.json` | Synthetic technical-gate evaluator result |
| `action-local-harness.log`, `action-github-output.txt`, `action-job-summary.md` | Action adapter evidence |
| `github-comment-golden.md` | Stable PR comment equivalent |
| `pytest-coverage.log` | Tests and coverage gate |
| `static-analysis.log` | Ruff and mypy strict |
| `packaging.log`, `wheel-clean-venv-smoke.log` | Build and clean wheel smoke test |
| `privacy-invariants.log` | Report/log privacy and provider source invariants |
| `git-worktree-check.log` | Diff check, worktree inventory, and canonical doc hashes |
| `security-review.log` | Gate C matrix, dependency, secret, link, build, and clean-smoke closure |
| `launch-audit.log` | Launch copy, platform-rule, timing, link, ethics, and final quality audit |

Live BigQuery and a real GitHub-hosted Action run were not available. The corresponding local
contract/fake transport/harness evidence must not be described as a live integration result.

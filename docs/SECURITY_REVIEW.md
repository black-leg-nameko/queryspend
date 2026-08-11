# Defensive security and quality review

- Review date: 2026-08-11 JST
- Scope: the local `queryspend` CLI, Python package, composite Action, example workflows,
  packaging, dependencies, documentation, and generated launch assets
- Authorization: repository-owner requested pre-publication defensive review
- Review result: **Pass for Gate C — 0 open Critical/High findings and 0 open code-level
  Medium findings**
- Production status: **Alpha — live BigQuery ADC/OIDC and a GitHub-hosted Action run remain
  unverified**

The original review used the repository at its pre-initial-commit state. Publication checks and the
post-publication dependency finding below were added from the public repository. This is not a
claim that a future hosted credentialed deployment is secure. No third-party target was tested.

## Threat model

1. The primary assets are BigQuery credentials, dataset metadata, compiled SQL, model/relation
   names, cost-policy decisions, and release integrity.
2. The CLI accepts untrusted dbt manifest JSON, configuration YAML, saved report JSON, validation
   JSON/JSONL, file paths, and environment overrides.
3. The composite Action adds untrusted artifact files and GitHub event context at a boundary where
   a trusted workflow may later obtain OIDC credentials.
4. Pull-request authors are the most likely adversarial input source; compromised dependencies or
   Actions are the most consequential supply-chain adversary.
5. Raw SQL may cross only from the local runner to the user's BigQuery API for a dry run; it must
   not cross into reports, logs, summaries, or comments.
6. A forged or stale report could create a false pass/warn decision even if evaluation failed.
7. Oversized, deeply nested, cyclic, duplicate-key, aliased, or non-finite input could exhaust
   memory/CPU or create ambiguous policy behavior.
8. Path traversal or symlinks could make an Action read or overwrite a file outside its intended
   workspace.
9. A trusted-workflow mistake could expose OIDC or GitHub credentials to pull-request-controlled
   code or forward a token to an attacker-controlled host.
10. A mutable or unhashed dependency/Action could execute during CI or release with repository
    privileges.

## Security findings

Every confirmed finding was fixed and regression-tested. Severity reflects impact and practical
exploitability in the documented workflow, not the theoretical worst case.

| ID | Severity | Impact | Location | Fix and verification | Status |
|---|---|---|---|---|:---:|
| QS-SEC-001 | **High** | A pull-request artifact could pre-place a schema-valid `report_path`. If evaluation then failed before writing a new report, the composite Action could finalize and publish the stale attacker-controlled decision. | `action.yml:64-80`; `queryspend/github_action.py:42-89` | Preflight now rejects an existing report or report symlink before evaluation, rejects control characters and workspace escapes, and fails closed. Regression covers a valid forged demo report, missing input, and unsafe paths in `tests/test_github_action.py:13-46`. | Fixed |
| QS-SEC-002 | Medium | The original `workflow_run` example put PR-produced artifacts too close to an OIDC-capable job, increasing artifact-confusion and cloud-metadata exposure risk. | `examples/workflows/evaluate-queryspend.yml:10-121`; `docs/GITHUB_ACTION.md` | Added a credential-free verification job that enforces the producer event/repository/head SHA/PR, exact three-file set, no symlinks, and size limits. Only its re-upload reaches a separate protected-environment job; that job has explicit least-privilege permissions and requires human review before OIDC. Forks are skipped. | Fixed |
| QS-SEC-003 | Medium | Recursive graph traversal and quadratic queues allowed a deep, valid manifest to cause recursion failure or excessive CPU. | `queryspend/graph.py:23-130`; `tests/test_artifacts_graph.py:162-182` | Replaced recursion and front-of-list removal with iterative `deque`/heap Kahn traversal. A deterministic 2,500-node chain is a regression test. | Fixed |
| QS-SEC-004 | Medium | Ambiguous YAML plus insufficient JSON/resource boundaries could create configuration confusion or denial of service; validation diagnostics could include input values. | `queryspend/config.py:26-71,213-265`; `queryspend/dbt_artifacts.py:15-20,60-211` | Strict safe YAML rejects duplicate keys and aliases; errors omit input/context values. Manifests reject duplicate/non-finite JSON, depth over 64, over 100 MiB, over 100,000 resources, control/oversized identifiers, and compiled SQL over 2 MiB. Regressions cover each boundary. | Fixed |
| QS-SEC-005 | Medium | The composite Action installed runtime version ranges without hashes, allowing dependency drift at execution time. | `action.yml:39-45`; `requirements-action.txt` | Added an exact, hash-locked runtime export and install with `pip --require-hashes`; the Action executes reviewed source via `PYTHONPATH`. A fresh-venv installation and Action harness passed. External Actions are pinned to 40-character SHAs. | Fixed |
| QS-SEC-006 | Low | A malformed saved report could echo attacker-controlled validation content into CLI logs. | `queryspend/cli.py:98-115`; `tests/test_cli_validation.py:27-35` | Invalid-report output is now a fixed schema message that does not include parsed values. | Fixed |
| QS-SEC-007 | Low | The PR-comment transport accepted any HTTPS API base from environment, which could forward `GITHUB_TOKEN` if the environment were misconfigured. | `queryspend/github_action.py:144-259`; `tests/test_github_action.py:65-70` | Bind requests to GitHub's expected API host, reject URL credentials/fragments/non-HTTPS, validate repository/PR/SHA, bound event/API bodies, and re-check the live PR head SHA before commenting. | Fixed |
| QS-SEC-008 | Medium | GitHub's post-publication dependency scan found CVE-2025-71176 in the locked pytest 8.4.2 development dependency. On multi-user UNIX hosts, vulnerable pytest temporary-directory handling could allow local denial of service or privilege impact. | `pyproject.toml`; `uv.lock` | Raised the optional development constraint to pytest 9.0.3 or newer and locked 9.1.1. The runtime wheel never installs pytest. The 75-test suite, full development-dependency audit, and Action-runtime audit pass after the update. | Fixed |

Open finding count after re-review: Critical 0, High 0, Medium 0, Low 0.

## Dry-run and privacy invariants

- The package contains exactly one `client.query` call, at
  `queryspend/providers/bigquery.py:120-125`. It constructs
  `QueryJobConfig(dry_run=True, use_query_cache=False)` at lines 115-118 and does not call
  `QueryJob.result()` or fetch result rows.
- Non-`SELECT` statement types are marked unsupported; external/federated and incomplete table
  metadata become unknown rather than known zero.
- Raw provider messages are replaced with fixed diagnostics. Raw SQL is not present in the report
  schema, logs, Markdown, terminal output, or PR comment; only its SHA-256 is retained.
- Model names are included by default because they are necessary for review. Relation names are
  excluded by default. Set both privacy flags to false where model identifiers are sensitive.
- Report writes use an owner-only temporary file, `fsync`, and atomic replace
  (`queryspend/cli.py:149-169`). The Action additionally refuses stale outputs and input symlinks.

## Checked and clear

| Class | Verdict | Evidence |
|---|---|---|
| Secrets | Clear in working tree and full history | `gitleaks dir . --no-banner --redact` and `gitleaks git . --redact --no-banner` found no leaks; the pinned hosted secret-scan job also passed. No `.env`, private key, credential, internal URL, or raw SQL appeared in generated artifacts. |
| Authentication/session | N/A | No user accounts, sessions, passwords, OAuth callback, or service endpoint. ADC and GitHub OIDC are delegated identity mechanisms and reviewed under workflow trust. |
| Authorization/IDOR/multi-tenancy | N/A | No server, tenant, endpoint, or persistent datastore. BigQuery IAM guidance limits the job project and referenced datasets. |
| Input validation/path handling | Clear after fixes | Strict YAML/JSON models, regular-file and size checks, bounded graph/data, workspace containment, input-symlink rejection, and atomic output. |
| XSS/CSRF/SSRF | N/A | No browser UI, state-changing HTTP endpoint, or user-supplied URL fetch. Markdown is rendered as text for a GitHub comment and contains no raw SQL/provider content. |
| CORS/CSP/security headers | N/A | No HTTP service or browser surface. |
| Rate limiting/abuse | N/A locally | No public service. BigQuery calls have a 30-second timeout, three attempts only for 429/5xx, and per-run caching. GitHub Action jobs have 5/10-minute limits. |
| Dependency/supply chain | Clear at review time | `uv.lock` is present; pytest is patched to 9.1.1; full development and Action-runtime audits report no known vulnerabilities; runtime Action dependencies are exact and hashed; workflow Actions use full SHAs; releases produce provenance attestations. |
| Privacy/logging | Clear after fixes | No telemetry endpoint. Fixed provider/config/report diagnostics discard secrets and attacker values. Generated reports/logs were scanned for fixture SQL/literals. |
| Payments/webhooks | N/A | No payments, pricing transaction, or webhook handler. |
| File upload | N/A as a service | No upload endpoint. Local/Action artifact files are treated as untrusted and bounded before parsing. |
| AI/prompt injection | N/A | No model, prompt, agent tool call, or AI-generated execution path. |
| Browser automation | N/A | No browser automation. |

## Quality findings

| Severity | Issue | Fix | Status |
|---|---|---|:---:|
| Medium | Freshly built distributions emitted Core Metadata 2.5, which the locked `twine` rejected and would make the release workflow fail. | Pinned Hatch's wheel/sdist metadata to 2.4. Both artifacts now pass `twine check`; clean wheel and sdist metadata are 2.4. | Fixed |
| Low | Strict type checking excluded the security-sensitive GitHub Action adapter even though it type-checked cleanly. | Removed the exclusion; strict mypy now checks every package module. | Fixed |

## Residual operational risks and follow-ups

These are explicit limits, not open source-code vulnerabilities:

1. **Live integration unverified (Medium operational risk).** No isolated-project BigQuery ADC run,
   real GitHub-hosted `workflow_run`, OIDC exchange, protected-environment approval, or audit-log
   proof was available. Keep the alpha caveat and do not call the Action production-ready until the
   checklist in `docs/ROADMAP.md` passes.
2. **Human approval is part of the trust boundary (Low residual risk).** A same-repository
   contributor can intentionally submit arbitrary compiled SQL as artifact data. The credentialed
   job therefore depends on protected-environment reviewers inspecting the verified SHA. Keep the
   service account restricted to a dedicated billing project and only required datasets, and
   prevent self-review.
3. **Hosted credentialed Action path unverified (Low operational risk).** Public `main` CI, the
   full-history secret scan, private vulnerability reporting, release workflow, artifact
   attestations, and a clean release-wheel install are verified. A real hosted `workflow_run` with
   OIDC, protected-environment approval, and BigQuery credentials is still unverified; retain the
   alpha caveat until that path has sanitized evidence.
4. **Dependency results age (Low operational risk).** Regenerate `requirements-action.txt` from the
   locked graph, review the diff, and rerun `pip-audit` whenever dependencies change. A clean audit
   is point-in-time evidence, not a guarantee against future disclosures.

## Verification summary

The final reproducible command transcript is in
`artifacts/verification/security-review.log`. At review closure:

- Python 3.11/3.12/3.13: 75 tests passed on each; branch coverage
  90.64%/90.69%/90.69% (gate 90%);
- Ruff (including Bandit-derived `S` rules): passed;
- strict mypy over the full package: passed;
- actionlint over CI, release, and example workflows: passed;
- sdist/wheel build and `twine check`: passed;
- fresh-venv hash-locked Action harness and clean-wheel demo: passed;
- `pip-audit`: no known vulnerabilities;
- working-tree and full-history gitleaks plus public Markdown link checks: passed;
- hosted `main` CI run 31471049688 and v0.1.1 release run 31471163770: passed;
- Dependabot alert 1 for CVE-2025-71176: fixed, not dismissed;
- published v0.1.1 wheel/sdist attestations and clean release-wheel demo: verified.

Gate C and repository publication checks are complete. They do not erase the live ADC/OIDC limits
above and do not authorize Product Hunt, Hacker News, Reddit, X, LinkedIn, or other social posts.

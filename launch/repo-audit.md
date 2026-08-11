# Pre-launch repository audit

- Audit date: 2026-08-11 JST
- Mode: existing-repository audit
- Primary language/category: Python
- UI contract: **N/A — CLI/composite Action only; no Web or mobile UI and no `DESIGN.md`**
- Final repository verdict: **SHIP — public repository, hosted CI, full-history secret scan,
  Gate C, and current v0.1.1 release checks pass**

The public repository, initial v0.1.0 release, and corrective v0.1.1 security-maintenance release
were verified on 2026-08-11 after explicit user approval. Live BigQuery ADC, hosted
workflow-run/OIDC validation, social-preview upload, starter issues, and human-owned launch-channel
posts remain separate follow-ups and are not reported as complete.

## Measured time to value

The README quickstart was first reproduced from a temporary local Git origin, then repeated from a
fresh shallow clone of the public repository after publication.

```text
environment: CPython 3.14.6; fresh clone; fresh uv cache; fresh virtual environment
command path: git clone → cd queryspend → uv run queryspend demo
elapsed: 12.819 seconds (clone through rendered result)
exit: 0
credentials: none
result disclosure: SIMULATED DEMO — not a live BigQuery estimate

public-clone recheck: 4 seconds, exit 0, credentials none, same disclosure
```

The project supports Python 3.11–3.13; the local audit host used 3.14. Compatibility versions are
covered by the CI matrix. Network and machine speed vary, but the measured path has 47 seconds of
headroom against the 60-second gate.

## Blockers checklist

| Check | Result | Evidence / action |
|---|:---:|---|
| README first screen has one-line pitch, demo, quickstart | Pass | `README.md` |
| Quickstart executed literally from a clean clone in ≤60s | Pass | 12.819s, exit 0; procedure above |
| Demo is <10s, <5MB, and shows value | Pass | `assets/demo.gif`: 5.96s, 142KiB, 1200×760; synthetic disclosure visible |
| Reproducible demo source and static alternative | Pass | `assets/demo.tape`, `assets/demo.png`, README alt text |
| LICENSE matches package metadata | Pass | Apache-2.0 in `LICENSE` and `pyproject.toml` |
| Full-history gitleaks scan | Pass | Local complete-history scan found 0 leaks; hosted CI uses pinned gitleaks 8.24.3 and passed on the release source history. |
| No personal/internal information | Pass | Working-tree and full-history scans found no credential, client name, internal URL, `.env`, or raw SQL artifact. |
| CI green on default branch; badge matches | Pass | Latest hosted `main` run [31471049688](https://github.com/black-leg-nameko/queryspend/actions/runs/31471049688) passed the secret, quality, and Python 3.11–3.13 jobs; README shows its live badge. |
| Description configured, ≤120 chars, searchable | Pass | Applied description recorded in `launch/metadata.md`. |
| Defensive security review complete | Pass | `docs/SECURITY_REVIEW.md`: 0 open Critical/High and 0 open code-level Medium findings. |
| User confirms public publication | Pass | Explicit commit, push, and release instruction received on 2026-08-11. |

## Strong checklist

| Check | Result | Evidence / action |
|---|:---:|---|
| Topics 5–10 | Pass | Ten topics applied and verified through the repository API. |
| Social preview 1280×640 | Prepared, not uploaded | `assets/social-preview.png` (1280×640, 125KiB) plus SVG source |
| CONTRIBUTING setup | Pass | Credential-free setup and full quality commands |
| Bug/feature templates + PR template | Pass | `.github/` templates include privacy/security routing |
| SECURITY private route | Pass | Private vulnerability reporting is enabled; advisory link and 72-hour acknowledgement target are published. |
| 5–10 good first issues | Prepared, not opened | Six scoped candidates in `docs/GOOD_FIRST_ISSUES.md`; opening issues is external |
| Tag → release automation | Pass hosted | Current release run [31471163770](https://github.com/black-leg-nameko/queryspend/actions/runs/31471163770) built, checked, attested, and uploaded both distributions. |
| Current versioned release | Pass | Annotated unsigned tag and [v0.1.1 GitHub Release](https://github.com/black-leg-nameko/queryspend/releases/tag/v0.1.1) published; both asset attestations verified. v0.1.0 remains immutable history. |
| Honest named comparison | Pass | README compares dry-run, dbt CI, post-deploy billing, and queryspend |
| Reproducible claimed metrics | Pass | Synthetic evaluator is explicitly not a live accuracy claim; reproduction command included |
| Docs for config surface | Pass | Action, roadmap, release, security, schemas, examples |
| Roadmap visible | Pass | README link and `docs/ROADMAP.md` |
| Discussions enabled | Pass | Enabled and verified through the repository API. |
| FUNDING.yml | Justified skip | No sponsorship or commercial boundary has been approved |

## Tool evidence

```text
gitleaks dir . --no-banner --redact
  no leaks found; ~2.53 MB scanned

gitleaks git . --redact --no-banner
  complete release history; no leaks found locally and in hosted CI

actionlint .github/workflows/*.yml examples/workflows/*.yml
  exit 0

Python 3.11 / 3.12 / 3.13
  75 tests passed on each; coverage 90.64% / 90.69% / 90.69%

ruff / strict mypy / pip-audit / public Markdown links
  pass / 24 source files pass / 0 known vulnerabilities / 21 files pass

uv build / twine / clean wheel / hash-locked Action harness
  pass / both distributions pass / pass / pass

hosted main CI / release workflow / provenance
  run 31471049688 pass / run 31471163770 pass / wheel and sdist attestations present

published v0.1.1 artifacts
  wheel SHA-256: b2f3d2fddb29cf92d265ff46f132ac14dafa92cafe98dec9205e85200b795662
  sdist SHA-256: 5f830480893f321f7bc65e6aff4c88cbf9b32a8e918d92a589dd48d544f26a7e

demo asset
  149 frames; 5.96s; 1200×760; 144,739 bytes
  static PNG 1200×760; social preview PNG 1280×640
```

The final test, package, link, secret, and security results are recorded in
`artifacts/verification/security-review.log`.

## Finalization rule

Gate C and the public-release audit are `PASS`: every finding is resolved, hosted `main` CI is
green, the full release history is secret-scanned, and the published v0.1.1 wheel installs and runs
the credential-free demo. The tags are annotated but unsigned because no signing key was
available; GitHub provenance attestations exist for both current release assets. Live ADC/OIDC
results, social-preview upload, and launch-channel posts must still not be inferred from this
evidence.

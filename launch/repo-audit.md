# Pre-launch repository audit

- Audit date: 2026-08-11 JST
- Mode: existing-repository audit
- Primary language/category: Python
- UI contract: **N/A — CLI/composite Action only; no Web or mobile UI and no `DESIGN.md`**
- Phase 1/final controllable verdict: **SHIP — repository and Gate C code checks pass; external
  day-of operations remain pending user**

All controllable repository-standardization and defensive-review work is complete. A repository
with no remote still cannot have a green default-branch CI run, uploaded social preview, configured
metadata, release, full-history scan, or publication confirmation. These are explicit external
day-of gates, not locally fabricated passes, and they do not authorize external changes.

## Measured time to value

The README quickstart was reproduced from a temporary local Git origin so the clone and source-tree
behavior matched the published instructions without creating or pushing a remote repository.

```text
environment: CPython 3.14.6; fresh clone; fresh uv cache; fresh virtual environment
command path: git clone → cd queryspend → uv run queryspend demo
elapsed: 12.819 seconds (clone through rendered result)
exit: 0
credentials: none
result disclosure: SIMULATED DEMO — not a live BigQuery estimate
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
| Full-history gitleaks scan | Pending external history | Repository has zero commits; `gitleaks dir .` passed on 2026-08-11. Run `gitleaks git .` after the initial private commit and before public push. |
| No personal/internal information | Pass at working-tree audit | No credential, client name, personal email, internal URL, or `.env` found; placeholders are explicitly marked. Re-run on history. |
| CI green on default branch; badge matches | Pending external | The badge says only `CI configured` and links to the local workflow; `actionlint` passes. Replace it with the hosted status badge only after a green `main` run. |
| Description configured, ≤120 chars, searchable | Pending external | Exact approved proposal in `launch/metadata.md`; no `gh repo edit` was run. |
| Defensive security review complete | Pass | `docs/SECURITY_REVIEW.md`: 0 open Critical/High and 0 open code-level Medium findings. |
| User confirms public publication | Pending user | Preparation is not publication consent; no create/push/release command was run. |

## Strong checklist

| Check | Result | Evidence / action |
|---|:---:|---|
| Topics 5–10 | Prepared, not set | Ten exact topics in `launch/metadata.md` |
| Social preview 1280×640 | Prepared, not uploaded | `assets/social-preview.png` (1280×640, 125KiB) plus SVG source |
| CONTRIBUTING setup | Pass | Credential-free setup and full quality commands |
| Bug/feature templates + PR template | Pass | `.github/` templates include privacy/security routing |
| SECURITY private route | Prepared | Advisory link and 72-hour acknowledgement target; enable private reporting day-of |
| 5–10 good first issues | Prepared, not opened | Six scoped candidates in `docs/GOOD_FIRST_ISSUES.md`; opening issues is external |
| Tag → release automation | Pass locally | Pinned Actions, tests/build/twine, provenance attestation, GitHub Release assets |
| Versioned v0.1.0 release | Pending external | `pyproject.toml` is 0.1.0; draft notes exist; no tag/release was created |
| Honest named comparison | Pass | README compares dry-run, dbt CI, post-deploy billing, and queryspend |
| Reproducible claimed metrics | Pass | Synthetic evaluator is explicitly not a live accuracy claim; reproduction command included |
| Docs for config surface | Pass | Action, roadmap, release, security, schemas, examples |
| Roadmap visible | Pass | README link and `docs/ROADMAP.md` |
| Discussions enabled | Pending external | Exact day-of task; no repository exists |
| FUNDING.yml | Justified skip | No sponsorship or commercial boundary has been approved |

## Tool evidence

```text
gitleaks dir . --no-banner --redact
  no leaks found; ~2.53 MB scanned

actionlint .github/workflows/*.yml examples/workflows/*.yml
  exit 0

Python 3.11 / 3.12 / 3.13
  75 tests passed on each; coverage 90.64% / 90.69% / 90.69%

ruff / strict mypy / pip-audit / public Markdown links
  pass / 24 source files pass / 0 known vulnerabilities / 21 files pass

uv build / twine / clean wheel / hash-locked Action harness
  pass / both distributions pass / pass / pass

demo asset
  149 frames; 5.96s; 1200×760; 144,739 bytes
  static PNG 1200×760; social preview PNG 1280×640
```

The final test, package, link, secret, and security results are recorded in
`artifacts/verification/security-review.log`.

## Finalization rule

The local Gate C decision is `PASS`: every High-or-higher finding is resolved and the controllable
repository audit passes. Before a public push, the user must explicitly approve publication and
perform the external checklist in `launch/internal-audit-checklist.md`; hosted or live results must
not be inferred from local evidence.

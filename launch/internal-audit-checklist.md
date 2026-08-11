# Internal launch audit checklist

The maintainer checks and initials every item. Repository preparation does not satisfy external or
credentialed checks.

## Repository ownership and legal

- [x] Confirm the `black-leg-nameko/queryspend` GitHub owner/name is controlled by the project.
- [ ] Claim and verify the PyPI package name before any PyPI publication; v0.1.0 is GitHub-only.
- [ ] Confirm Apache-2.0 is the intended license and all included assets/data may be published.
- [x] Review the initial commit identity/history for personal or internal information.
- [x] Run `gitleaks git .` over the complete history and archive the clean log.
- [x] Confirm no unowned `queryspend.dev` URL is represented as a live docs endpoint.

## Hosted repository

- [x] Apply the `launch/metadata.md` description and topics.
- [ ] Upload `assets/social-preview.png` through the GitHub repository settings UI.
- [x] Enable Issues, Discussions, and private vulnerability reporting.
- [x] Run CI on `main`; confirm quality, Python 3.11–3.13, build, and secret-scan jobs are green.
- [x] After the first green `main` run, replace the honest `CI configured` badge with the hosted
  workflow status badge and confirm it resolves.
- [ ] Open six reviewed starter issues and apply `good first issue` labels.
- [ ] Pin a launch-feedback Discussion or issue and enable maintainer notifications.

## Product evidence

- [x] Re-run `uv run queryspend demo` from a fresh public clone in ≤60 seconds.
- [x] Confirm GIF/static image render and meaningful alt text in the public README.
- [ ] Complete isolated-project ADC and GitHub-hosted OIDC/Action validation before saying
  production-ready; until then keep every alpha caveat.
- [x] Confirm synthetic evaluator metrics are never described as real-world accuracy.

## Release and publication

- [x] Obtain explicit user approval for public push/tag/release.
- [x] Publish annotated `v0.1.0`; verify release workflow provenance and artifacts. The tag is
  unsigned because no signing key was available.
- [x] Install the release wheel cleanly and run the demo.
- [ ] Execute `docs/LAUNCH.md` only through human-owned channel accounts; never request upvotes or
  coordinate artificial engagement.

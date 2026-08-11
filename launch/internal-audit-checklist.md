# Internal launch audit checklist

The maintainer checks and initials every item. Repository preparation does not satisfy external or
credentialed checks.

## Repository ownership and legal

- [ ] Confirm the `queryspend` GitHub owner/name and PyPI package name are controlled by the project.
- [ ] Confirm Apache-2.0 is the intended license and all included assets/data may be published.
- [ ] Review the initial commit identity/history for personal or internal information.
- [ ] Run `gitleaks git .` over the complete private history and archive the clean log.
- [ ] Confirm no unowned `queryspend.dev` URL is represented as a live docs endpoint.

## Hosted repository

- [ ] Apply `launch/metadata.md` description/topics and upload `assets/social-preview.png`.
- [ ] Enable Issues, Discussions, and private vulnerability reporting.
- [ ] Run CI on `main`; confirm quality, Python 3.11–3.13, build, and secret-scan jobs are green.
- [ ] After the first green `main` run, replace the honest `CI configured` badge with the hosted
  workflow status badge and confirm it resolves.
- [ ] Open six reviewed starter issues and apply `good first issue` labels.
- [ ] Pin a launch-feedback Discussion or issue and enable maintainer notifications.

## Product evidence

- [ ] Re-run `uv run queryspend demo` from a fresh public clone in ≤60 seconds.
- [ ] Confirm GIF/static image render in GitHub light and dark modes and alt text is meaningful.
- [ ] Complete isolated-project ADC and GitHub-hosted OIDC/Action validation before saying
  production-ready; until then keep every alpha caveat.
- [ ] Confirm synthetic evaluator metrics are never described as real-world accuracy.

## Release and publication

- [ ] Obtain explicit user approval for public push/tag/release.
- [ ] Sign the `v0.1.0` tag and verify release workflow provenance and artifacts.
- [ ] Install the release wheel cleanly and run the demo.
- [ ] Execute `docs/LAUNCH.md` only through human-owned channel accounts; never request upvotes or
  coordinate artificial engagement.

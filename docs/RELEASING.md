# Releasing queryspend

Only maintainers release. Never publish from an unreviewed pull-request checkout.

## Preflight

1. Confirm CI and the defensive security review are green on `main`.
2. Confirm `pyproject.toml`, `queryspend.__version__`, and the intended tag match.
3. Run the clean verification commands from `CONTRIBUTING.md`.
4. Inspect `uv.lock`, dependency changes, and `git diff --check`.
5. Run `gitleaks git .` over full history and inspect the built wheel/sdist contents.
6. Regenerate the Action dependency lock with `uv export --no-dev --no-emit-project --locked
   --format requirements.txt --output-file requirements-action.txt`, review the diff, and run the
   dependency audit.
7. Update release notes with features, fixes, known alpha gaps, and upgrade notes.

## Build and tag

```bash
uv build
uvx twine check dist/*
git tag -s v0.1.0 -m "queryspend v0.1.0"
git push origin v0.1.0
```

Pushing a `v*` tag starts `.github/workflows/release.yml`, rebuilds from the trusted tag, checks the
artifacts, and creates a GitHub Release with the sdist and wheel. Tagging and pushing are human
operations; automation in this repository does not create a tag.

The workflow does **not** publish to PyPI. Configure PyPI Trusted Publishing as a separate protected
environment and review the package name and ownership before adding that step. Do not use a long-lived
PyPI token.

## After release

- Install the wheel in a clean environment and run `queryspend demo`.
- Verify the release asset hashes and curated notes.
- Pin GitHub Action consumers to the reviewed 40-character release commit SHA, not a movable tag.
- Keep the alpha caveats visible until live ADC/OIDC and real accuracy evidence exist.

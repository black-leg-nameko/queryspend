## What

<!-- Describe one focused change and its user-visible result. -->

## Why

<!-- Link an issue or explain the evidence for the change. -->

## Verification

<!-- Paste exact commands and sanitized results. -->

## Security and privacy impact

<!-- Address dry-run behavior, SQL/secret handling, untrusted input, paths, and Action trust. -->

## Checklist

- [ ] Tests cover behavior changes and important failure states.
- [ ] `ruff`, strict `mypy`, coverage, and build pass locally.
- [ ] Documentation and schemas are updated when public behavior changes.
- [ ] No raw SQL, credential, production identifier, or raw provider error is added to fixtures/logs.
- [ ] Dry-run-only and unknown-is-not-zero invariants remain intact.
- [ ] New third-party Actions are pinned to a full commit SHA.

# Good first issue candidates

These issues are scoped for launch-day seeding. A maintainer should open them individually, add the
`good first issue` label, and confirm they still match the code before publication. They are not
presented as already-open GitHub issues.

1. **Add a sanitized manifest size-limit error example** — add a small fixture and document the exit
   code 2 message; no provider call should occur.
2. **Document GitHub job-summary troubleshooting** — cover a read-only token, disabled comments,
   and where to download the JSON artifact.
3. **Add table-driven tests for dbt manifest v10–v12 metadata variations** — synthetic input only;
   preserve duplicate-key and node-count checks.
4. **Improve `TERM=dumb` snapshot coverage** — add a renderer regression test that proves meaning
   never depends on color or emoji.
5. **Add a configuration cookbook for per-model frequencies** — include exact, metadata, default,
   and unknown priority using fictitious model names.
6. **Check documentation links in CI** — use a pinned, non-networking checker for relative links and
   a separate non-blocking job for external links.

Avoid starter issues involving live credentials, OIDC policy, SQL disclosure, pricing semantics, or
the dry-run invariant; those require maintainer security review.

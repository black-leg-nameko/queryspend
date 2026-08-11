# queryspend v0.1.1

This security-maintenance release updates queryspend's optional development environment after
GitHub detected CVE-2025-71176 in pytest versions before 9.0.3. Runtime behavior is unchanged.

## Fixed

- Require pytest 9.0.3 or newer and lock pytest 9.1.1 for contributors and CI.
- Select the tag-matched release-notes file in the release workflow instead of a v0.1.0-specific
  path.

pytest is only part of the optional `dev` extra and is not installed by the queryspend runtime
wheel. The update prevents contributors and CI workers from resolving the vulnerable version.

## Alpha limits

Live BigQuery ADC/OIDC, dataset-level least privilege, audit-log zero-write evidence, and an actual
GitHub-hosted credentialed Action run remain unverified. The validation corpus is synthetic and
does not establish real-world prediction accuracy. Capacity/reservation pricing and non-BigQuery
warehouses are unsupported.

Install the published wheel and start without credentials:

```bash
python -m pip install https://github.com/black-leg-nameko/queryspend/releases/download/v0.1.1/queryspend-0.1.1-py3-none-any.whl
queryspend demo
```

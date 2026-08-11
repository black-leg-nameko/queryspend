"""Provider protocol and sanitized per-request failure."""

from __future__ import annotations

from typing import Protocol

from queryspend.models import DryRunEvidence, DryRunRequest, ReasonCode


class ProviderRequestError(Exception):
    """A sanitized provider failure that never carries raw SQL or provider text."""

    def __init__(
        self,
        reason_code: ReasonCode,
        remediation: str,
        *,
        authentication: bool = False,
    ) -> None:
        super().__init__(f"{reason_code.value}: {remediation}")
        self.reason_code = reason_code
        self.remediation = remediation
        self.authentication = authentication


class WarehouseProvider(Protocol):
    def dry_run(self, request: DryRunRequest) -> DryRunEvidence: ...


"""Bundled recorded-evidence provider used only by the simulated demo and tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from queryspend.exceptions import InputError
from queryspend.models import DryRunEvidence, DryRunRequest, ReasonCode
from queryspend.providers.base import ProviderRequestError


class RecordedProvider:
    def __init__(self, path: Path) -> None:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise InputError(f"Could not load recorded evidence: {path}") from error
        if not isinstance(raw, dict) or not isinstance(raw.get("responses"), dict):
            raise InputError("Recorded evidence must contain a responses object")
        self._responses: dict[str, Any] = raw["responses"]
        self.calls: list[DryRunRequest] = []

    def dry_run(self, request: DryRunRequest) -> DryRunEvidence:
        self.calls.append(request)
        response = self._responses.get(request.sql_sha256)
        if not isinstance(response, dict):
            raise ProviderRequestError(
                ReasonCode.PROVIDER_ERROR, "No recorded evidence exists for this SQL hash"
            )
        if "error" in response:
            try:
                code = ReasonCode(response["error"])
            except (ValueError, TypeError) as error:
                raise InputError("Recorded provider error code is invalid") from error
            raise ProviderRequestError(code, "Recorded provider failure", authentication=False)
        return DryRunEvidence.model_validate(
            {
                **response,
                "sql_sha256": request.sql_sha256,
                "fixture": True,
            }
        )


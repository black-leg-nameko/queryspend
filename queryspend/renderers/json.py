"""Canonical Cost Change Manifest JSON renderer."""

from __future__ import annotations

import json

from queryspend.models import QuerySpendReport


class JsonRenderer:
    def render(self, report: QuerySpendReport) -> str:
        return json.dumps(
            report.json_dict(),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ": "),
        ) + "\n"


"""Renderer protocol."""

from typing import Protocol

from queryspend.models import QuerySpendReport


class Renderer(Protocol):
    def render(self, report: QuerySpendReport) -> str | bytes: ...


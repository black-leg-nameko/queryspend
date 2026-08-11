"""Typed failures at the public API boundary."""

from __future__ import annotations

from queryspend.models import QuerySpendReport


class QuerySpendError(Exception):
    """Base class for expected queryspend failures."""

    exit_code = 6

    def __init__(self, message: str, *, partial_report: QuerySpendReport | None = None) -> None:
        super().__init__(message)
        self.partial_report = partial_report


class InputError(QuerySpendError):
    """Manifest, config, or command input is invalid."""

    exit_code = 2


class AuthenticationError(QuerySpendError):
    """Application Default Credentials could not be resolved or used."""

    exit_code = 4


class ProviderGlobalError(QuerySpendError):
    """Every eligible provider request failed after retries."""

    exit_code = 5


class InvariantError(QuerySpendError):
    """A safety or internal invariant was violated."""

    exit_code = 6


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

import pytest
from google.api_core.exceptions import (
    BadRequest,
    DeadlineExceeded,
    Forbidden,
    InternalServerError,
    ServiceUnavailable,
    TooManyRequests,
    Unauthorized,
)
from google.auth.exceptions import DefaultCredentialsError

from queryspend.exceptions import AuthenticationError, InputError
from queryspend.models import DryRunRequest, ModelStatus, ReasonCode
from queryspend.providers.base import ProviderRequestError
from queryspend.providers.bigquery import BigQueryProvider


@dataclass
class TableRef:
    project: str = "p"
    dataset_id: str = "d"
    table_id: str = "t"


class Job:
    statement_type = "SELECT"
    location = "US"
    total_bytes_processed = 123
    referenced_tables: ClassVar[list[TableRef]] = [TableRef()]


class Table:
    table_type = "TABLE"
    clustering_fields: ClassVar[list[str]] = []
    _properties: ClassVar[dict[str, Any]] = {}


class Client:
    project = "billing"

    def __init__(self, failures: list[Exception] | None = None) -> None:
        self.failures = failures or []
        self.configs: list[Any] = []
        self.sql_values: list[str] = []

    def query(self, sql: str, *, job_config: Any, location: str, timeout: int) -> Job:
        self.configs.append(job_config)
        self.sql_values.append(sql)
        if self.failures:
            raise self.failures.pop(0)
        assert location == "US"
        assert timeout == 30
        return Job()

    def get_table(self, reference: TableRef, *, timeout: int) -> Table:
        assert reference.table_id == "t"
        assert timeout == 30
        return Table()


def request(sql: str = "select 'secret-literal'") -> DryRunRequest:
    return DryRunRequest(
        model_unique_id="model.test.orders",
        side="head",
        sql=sql,
        sql_sha256="a" * 64,
        billing_project="billing",
        location="US",
    )


def test_provider_hard_dry_run_invariant_and_cache() -> None:
    client = Client()
    provider = BigQueryProvider("billing", client_factory=lambda _: client)
    first = provider.dry_run(request())
    second = provider.dry_run(request())
    assert first == second
    assert len(client.configs) == 1
    config = client.configs[0]
    assert config.dry_run is True
    assert config.use_query_cache is False
    assert first.raw_bytes == 123
    assert "secret" not in first.model_dump_json()


def test_provider_retries_429_without_leaking_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    client = Client([TooManyRequests("raw secret"), TooManyRequests("raw secret")])
    monkeypatch.setattr("queryspend.providers.bigquery.time.sleep", lambda _: None)
    provider = BigQueryProvider("billing", client_factory=lambda _: client)
    assert provider.dry_run(request()).status is ModelStatus.KNOWN
    assert len(client.configs) == 3
    failing = Client([BadRequest("select 'secret-literal'")])
    provider = BigQueryProvider("billing", client_factory=lambda _: failing)
    with pytest.raises(ProviderRequestError) as captured:
        provider.dry_run(request())
    assert captured.value.reason_code is ReasonCode.DRY_RUN_SYNTAX_ERROR
    assert "secret-literal" not in str(captured.value)


def test_provider_constructor_failures_are_typed() -> None:
    with pytest.raises(ValueError):
        BigQueryProvider("billing", max_attempts=0)
    with pytest.raises(AuthenticationError):
        BigQueryProvider(
            "billing", client_factory=lambda _: (_ for _ in ()).throw(DefaultCredentialsError())
        )
    empty = Client()
    empty.project = ""
    with pytest.raises(InputError, match="billing_project"):
        BigQueryProvider(None, client_factory=lambda _: empty)


@pytest.mark.parametrize(
    ("error", "reason", "authentication"),
    [
        (DeadlineExceeded("timeout"), ReasonCode.PROVIDER_TIMEOUT, False),
        (Unauthorized("no"), ReasonCode.PERMISSION_DENIED, True),
        (Forbidden("no"), ReasonCode.PERMISSION_DENIED, True),
        (ServiceUnavailable("down"), ReasonCode.PROVIDER_ERROR, False),
    ],
)
def test_provider_sanitized_error_classes(
    error: Exception,
    reason: ReasonCode,
    authentication: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("queryspend.providers.bigquery.time.sleep", lambda _: None)
    failures = [error]
    if isinstance(error, ServiceUnavailable):
        failures = [
            ServiceUnavailable("down"),
            InternalServerError("down"),
            InternalServerError("down"),
        ]
    provider = BigQueryProvider("billing", client_factory=lambda _: Client(failures))
    with pytest.raises(ProviderRequestError) as captured:
        provider.dry_run(request())
    assert captured.value.reason_code is reason
    assert captured.value.authentication is authentication
    assert "down" not in str(captured.value)


def test_provider_classifies_statement_location_external_cluster_and_unknown_count() -> None:
    class CaveatJob:
        statement_type = "UPDATE"
        location = "EU"
        total_bytes_processed = 0
        referenced_tables: ClassVar[list[TableRef]] = [TableRef()]

    class CaveatTable:
        table_type = "EXTERNAL"
        clustering_fields: ClassVar[list[str]] = ["customer_id"]
        _properties: ClassVar[dict[str, Any]] = {
            "externalDataConfiguration": {"sourceFormat": "CSV"}
        }

    client = Client()
    client.query = lambda *args, **kwargs: CaveatJob()  # type: ignore[method-assign]
    client.get_table = lambda *args, **kwargs: CaveatTable()  # type: ignore[method-assign]
    result = BigQueryProvider("billing", client_factory=lambda _: client).dry_run(request())
    assert result.status is ModelStatus.UNKNOWN
    assert set(result.reason_codes) >= {
        ReasonCode.UNSUPPORTED_STATEMENT_TYPE,
        ReasonCode.LOCATION_MISMATCH,
        ReasonCode.EXTERNAL_SOURCE_ESTIMATE_UNAVAILABLE,
        ReasonCode.CLUSTERED_TABLE_UPPER_BOUND,
    }

    class UnknownRefsJob:
        statement_type = "SELECT"
        location = "US"
        total_bytes_processed = 1
        referenced_tables = None

    client = Client()
    client.query = lambda *args, **kwargs: UnknownRefsJob()  # type: ignore[method-assign]
    result = BigQueryProvider("billing", client_factory=lambda _: client).dry_run(request())
    assert result.table_count is None
    assert ReasonCode.REFERENCED_TABLE_COUNT_UNKNOWN in result.reason_codes

    client = Client()
    client.get_table = lambda *args, **kwargs: (_ for _ in ()).throw(Forbidden("metadata"))  # type: ignore[method-assign]
    result = BigQueryProvider("billing", client_factory=lambda _: client).dry_run(request())
    assert result.status is ModelStatus.UNKNOWN
    assert ReasonCode.REFERENCED_TABLE_METADATA_UNAVAILABLE in result.reason_codes

"""BigQuery on-demand dry-run provider.

The only query path constructs QueryJobConfig with dry_run=True and
use_query_cache=False. It never calls QueryJob.result() or reads rows.
"""

from __future__ import annotations

import secrets
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from google.api_core import exceptions as google_exceptions
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery

from queryspend.exceptions import AuthenticationError, InputError
from queryspend.models import DryRunEvidence, DryRunRequest, ModelStatus, ReasonCode
from queryspend.providers.base import ProviderRequestError

ClientFactory = Callable[[str | None], Any]


class BigQueryProvider:
    """Production provider backed by Application Default Credentials."""

    def __init__(
        self,
        billing_project: str | None,
        *,
        client_factory: ClientFactory | None = None,
        max_attempts: int = 3,
        request_timeout_seconds: int = 30,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.max_attempts = max_attempts
        self.request_timeout_seconds = request_timeout_seconds
        factory = client_factory or (lambda project: bigquery.Client(project=project))
        try:
            self.client = factory(billing_project)
        except DefaultCredentialsError as error:
            raise AuthenticationError(
                "Application Default Credentials are unavailable. Run `gcloud auth "
                "application-default login` locally or configure GitHub OIDC."
            ) from error
        except google_exceptions.GoogleAPICallError as error:
            raise AuthenticationError("Could not initialize BigQuery with ADC") from error
        self.billing_project = billing_project or getattr(self.client, "project", None)
        if not self.billing_project:
            raise InputError(
                "warehouse.billing_project is required when ADC has no quota project"
            )
        self._cache: dict[tuple[str, str | None, str], DryRunEvidence] = {}
        self._cache_lock = threading.Lock()

    def dry_run(self, request: DryRunRequest) -> DryRunEvidence:
        key = (request.billing_project, request.location, request.sql_sha256)
        with self._cache_lock:
            cached = self._cache.get(key)
        if cached is not None:
            return cached
        evidence = self._request_with_retry(request)
        with self._cache_lock:
            self._cache.setdefault(key, evidence)
            return self._cache[key]

    def _request_with_retry(self, request: DryRunRequest) -> DryRunEvidence:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._single_dry_run(request)
            except google_exceptions.DeadlineExceeded as error:
                raise ProviderRequestError(
                    ReasonCode.PROVIDER_TIMEOUT, "BigQuery dry-run timed out after 30 seconds"
                ) from error
            except (google_exceptions.TooManyRequests, google_exceptions.ServerError) as error:
                if attempt == self.max_attempts:
                    code = (
                        ReasonCode.RATE_LIMIT_EXHAUSTED
                        if isinstance(error, google_exceptions.TooManyRequests)
                        else ReasonCode.PROVIDER_ERROR
                    )
                    raise ProviderRequestError(
                        code, "BigQuery transient failure exhausted three attempts"
                    ) from error
                delay = (2 ** (attempt - 1)) + secrets.randbelow(250) / 1000
                time.sleep(delay)
            except google_exceptions.BadRequest as error:
                raise ProviderRequestError(
                    ReasonCode.DRY_RUN_SYNTAX_ERROR,
                    "BigQuery rejected the compiled query; run dbt compile and inspect it locally",
                ) from error
            except google_exceptions.Unauthorized as error:
                raise ProviderRequestError(
                    ReasonCode.PERMISSION_DENIED,
                    "Refresh Application Default Credentials",
                    authentication=True,
                ) from error
            except google_exceptions.Forbidden as error:
                raise ProviderRequestError(
                    ReasonCode.PERMISSION_DENIED,
                    "Grant BigQuery Job User on the billing project and Data Viewer on "
                    "referenced datasets",
                    authentication=True,
                ) from error
            except google_exceptions.GoogleAPICallError as error:
                raise ProviderRequestError(
                    ReasonCode.PROVIDER_ERROR, "BigQuery dry-run failed"
                ) from error
        raise AssertionError("unreachable retry state")

    def _single_dry_run(self, request: DryRunRequest) -> DryRunEvidence:
        started = time.monotonic()
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        job_config.use_legacy_sql = False
        # SECURITY INVARIANT: this is the sole client.query call in the package.
        job = self.client.query(
            request.sql,
            job_config=job_config,
            location=request.location,
            timeout=self.request_timeout_seconds,
        )
        statement_type = getattr(job, "statement_type", None)
        location = getattr(job, "location", None) or request.location
        reasons: list[ReasonCode] = []
        status = ModelStatus.KNOWN
        if statement_type not in {None, "SELECT"}:
            reasons.append(ReasonCode.UNSUPPORTED_STATEMENT_TYPE)
            status = ModelStatus.UNSUPPORTED
        if request.location and location and request.location != location:
            reasons.append(ReasonCode.LOCATION_MISMATCH)
            status = ModelStatus.UNKNOWN
        referenced = getattr(job, "referenced_tables", None)
        table_count: int | None = None
        table_types: list[str] = []
        clustered = False
        metadata_complete = True
        if referenced is not None:
            distinct = {_table_ref_key(table) for table in referenced}
            table_count = len(distinct)
            for table_ref in referenced:
                try:
                    table = self.client.get_table(table_ref, timeout=self.request_timeout_seconds)
                except google_exceptions.GoogleAPICallError:
                    metadata_complete = False
                    continue
                table_type = str(getattr(table, "table_type", "UNKNOWN"))
                table_types.append(table_type)
                clustered = clustered or bool(getattr(table, "clustering_fields", None))
                properties = getattr(table, "_properties", {})
                if isinstance(properties, dict) and properties.get("externalDataConfiguration"):
                    table_types.append("EXTERNAL")
        raw_bytes = int(getattr(job, "total_bytes_processed", 0) or 0)
        if "EXTERNAL" in table_types or (raw_bytes == 0 and table_count not in {None, 0}):
            reasons.append(ReasonCode.EXTERNAL_SOURCE_ESTIMATE_UNAVAILABLE)
            status = ModelStatus.UNKNOWN
        if table_count is None:
            reasons.append(ReasonCode.REFERENCED_TABLE_COUNT_UNKNOWN)
        if not metadata_complete:
            reasons.append(ReasonCode.REFERENCED_TABLE_METADATA_UNAVAILABLE)
            status = ModelStatus.UNKNOWN
        if clustered:
            reasons.append(ReasonCode.CLUSTERED_TABLE_UPPER_BOUND)
        return DryRunEvidence(
            status=status,
            raw_bytes=raw_bytes,
            table_count=table_count,
            location=location,
            statement_type=statement_type,
            referenced_table_types=sorted(set(table_types)),
            clustered_table_detected=clustered,
            timestamp=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            latency_ms=round((time.monotonic() - started) * 1000),
            sql_sha256=request.sql_sha256,
            reason_codes=reasons,
        )


def _table_ref_key(table: Any) -> str:
    return ".".join(
        str(getattr(table, field, "")) for field in ("project", "dataset_id", "table_id")
    )

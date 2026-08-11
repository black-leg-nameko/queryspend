from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from queryspend.config import QuerySpendConfig, find_config, load_config, resolve_frequency
from queryspend.exceptions import InputError


def test_load_config_rejects_unquoted_decimal(tmp_path: Path) -> None:
    path = tmp_path / ".queryspend.yml"
    path.write_text(
        "version: 1\nwarehouse:\n  price_per_tib_usd: 6.25\n", encoding="utf-8"
    )
    with pytest.raises(InputError, match="quoted decimal"):
        load_config(path)


def test_load_config_rejects_unknown_keys_and_unsafe_provider(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.yml"
    unknown.write_text("version: 1\ntyop: true\n", encoding="utf-8")
    with pytest.raises(InputError, match="Extra inputs"):
        load_config(unknown)
    provider = tmp_path / "provider.yml"
    provider.write_text("version: 1\nwarehouse:\n  provider: snowflake\n", encoding="utf-8")
    with pytest.raises(InputError, match="bigquery"):
        load_config(provider)


def test_load_config_rejects_duplicate_keys_aliases_and_redacts_values(
    tmp_path: Path,
) -> None:
    duplicate = tmp_path / "duplicate.yml"
    duplicate.write_text("version: 1\nversion: 1\n", encoding="utf-8")
    with pytest.raises(InputError, match="read or parse"):
        load_config(duplicate)

    alias = tmp_path / "alias.yml"
    alias.write_text("version: &version 1\ncopy: *version\n", encoding="utf-8")
    with pytest.raises(InputError, match="read or parse"):
        load_config(alias)

    secret = tmp_path / "secret.yml"
    secret.write_text("version: 1\napi_key: TOPSECRET-DO-NOT-LOG\n", encoding="utf-8")
    with pytest.raises(InputError) as captured:
        load_config(secret)
    assert "TOPSECRET" not in str(captured.value)


def test_find_config_stops_at_git_root(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    config = tmp_path / ".queryspend.yml"
    config.write_text("version: 1\n", encoding="utf-8")
    child = tmp_path / "a" / "b"
    child.mkdir(parents=True)
    assert find_config(child) == config


def test_frequency_priority_and_meta_validation() -> None:
    config = QuerySpendConfig.model_validate(
        {
            "version": 1,
            "frequencies": {
                "default_runs_per_month": "1",
                "models": {"model.test.orders": "30"},
            },
        }
    )
    value, source, overridden = resolve_frequency(
        config,
        "model.test.orders",
        {"queryspend": {"runs_per_month": "20"}},
        None,
    )
    assert (value, source, overridden) == (Decimal(30), "config_model", True)
    value, source, overridden = resolve_frequency(config, "model.test.other", None, None)
    assert (value, source, overridden) == (Decimal(1), "config_default", False)
    with pytest.raises(InputError, match="quoted decimal"):
        resolve_frequency(
            QuerySpendConfig(),
            "model.test.other",
            {"queryspend": {"runs_per_month": 20}},
            None,
        )


@pytest.mark.parametrize(
    "body",
    [
        'version: 1\nwarehouse:\n  price_per_tib_usd: "0"\n',
        'version: 1\nwarehouse:\n  price_per_tib_usd: "NaN"\n',
        'version: 1\nwarehouse:\n  billing_project: ""\n',
        "version: 1\nfrequencies:\n  models: []\n",
        "version: 1\nfrequencies:\n  models:\n    x: 2\n",
        "version: 1\npolicy:\n  max_monthly_delta_bytes: -1\n",
        "version: 1\npolicy:\n  max_monthly_delta_bytes: true\n",
    ],
)
def test_config_rejects_invalid_boundaries(tmp_path: Path, body: str) -> None:
    path = tmp_path / "bad.yml"
    path.write_text(body, encoding="utf-8")
    with pytest.raises(InputError):
        load_config(path)


def test_config_read_errors_size_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    non_mapping = tmp_path / "list.yml"
    non_mapping.write_text("- item\n", encoding="utf-8")
    with pytest.raises(InputError, match="root must be a mapping"):
        load_config(non_mapping)
    invalid_yaml = tmp_path / "invalid.yml"
    invalid_yaml.write_text("version: [", encoding="utf-8")
    with pytest.raises(InputError, match="Could not read"):
        load_config(invalid_yaml)
    monkeypatch.setattr("queryspend.config.MAX_CONFIG_BYTES", 1)
    with pytest.raises(InputError, match="exceeds"):
        load_config(non_mapping)
    monkeypatch.setattr("queryspend.config.MAX_CONFIG_BYTES", 1024 * 1024)
    monkeypatch.setenv("QUERYSPEND_BILLING_PROJECT", "env-billing")
    monkeypatch.setenv("QUERYSPEND_LOCATION", "EU")
    config = load_config(None, search_from=tmp_path)
    assert config.warehouse.billing_project == "env-billing"
    assert config.warehouse.location == "EU"

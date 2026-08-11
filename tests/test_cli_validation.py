from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from queryspend.cli import app
from queryspend.exceptions import InputError
from queryspend.validation import evaluate_validation
from tests.helpers import manifest, model_node

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_demo_json_stdout_is_only_json(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    result = runner.invoke(app, ["demo", "--format", "json", "--output", str(output)])
    assert result.exit_code == 0, result.output
    parsed = json.loads(result.stdout)
    assert parsed["run"]["simulated"] is True
    assert json.loads(output.read_text(encoding="utf-8"))["policy"]["decision"] == "warn"


def test_render_does_not_echo_malformed_report_values(tmp_path: Path) -> None:
    report = tmp_path / "malformed.json"
    report.write_text('{"raw_sql":"select TOPSECRET"}', encoding="utf-8")
    result = runner.invoke(
        app, ["render", "--input", str(report), "--format", "markdown"]
    )
    assert result.exit_code == 2
    assert "TOPSECRET" not in result.output
    assert "does not match" in result.output


def test_check_empty_and_render_markdown(tmp_path: Path) -> None:
    same = manifest(
        tmp_path / "same.json",
        nodes={"model.test.orders": model_node("model.test.orders")},
    )
    output = tmp_path / "report.json"
    checked = runner.invoke(
        app,
        [
            "check",
            "--base",
            str(same),
            "--head",
            str(same),
            "--output",
            str(output),
            "--format",
            "json",
        ],
    )
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.stdout)["summary"]["affected_models"] == 0
    rendered = runner.invoke(
        app, ["render", "--input", str(output), "--format", "markdown"]
    )
    assert rendered.exit_code == 0
    assert "No cost-affecting model changes" in rendered.stdout


def test_check_unknown_policy_block_exits_three(tmp_path: Path) -> None:
    base = manifest(
        tmp_path / "base.json",
        nodes={
            "model.test.orders": model_node(
                "model.test.orders", materialized="view", sql="select 1"
            )
        },
    )
    head = manifest(
        tmp_path / "head.json",
        nodes={
            "model.test.orders": model_node(
                "model.test.orders",
                materialized="view",
                sql="select 2",
                checksum="changed",
            )
        },
    )
    config = tmp_path / "config.yml"
    config.write_text("version: 1\npolicy:\n  unknown_behavior: block\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "check",
            "--base",
            str(base),
            "--head",
            str(head),
            "--config",
            str(config),
            "--output",
            str(tmp_path / "blocked.json"),
        ],
    )
    assert result.exit_code == 3
    assert "Decision: BLOCK" in result.stdout


def test_validate_synthetic_corpus_and_schema() -> None:
    report = evaluate_validation(
        str(ROOT / "validation/predictions/*.json"),
        ROOT / "validation/observations.jsonl",
    )
    assert report.decision == "pass"
    assert report.metrics.eligible_ape_cases == 8
    assert report.metrics.false_blockers == 0
    assert report.metrics.unknown_prediction_cases == 1


def test_validate_rejects_empty_pattern(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "validate",
            "--predictions",
            str(tmp_path / "*.json"),
            "--observations",
            str(ROOT / "validation/observations.jsonl"),
        ],
    )
    assert result.exit_code == 2
    assert "matched no files" in result.output


def test_validation_reports_all_failed_gate_criteria(tmp_path: Path) -> None:
    source = json.loads(
        (ROOT / "validation/predictions/northstar-remove-partition-filter.json").read_text(
            encoding="utf-8"
        )
    )
    source["models"][0]["monthly_cost_delta_usd"] = "-620.000000"
    source["summary"]["known_monthly_delta_usd"] = "-620.000000"
    source["policy"]["decision"] = "block"
    source["policy"]["reason"] = "usd_threshold_exceeded"
    (tmp_path / "prediction.json").write_text(json.dumps(source), encoding="utf-8")
    observation = next(
        line
        for line in (ROOT / "validation/observations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if "northstar-remove-partition-filter" in line
    )
    observations = tmp_path / "observations.jsonl"
    observations.write_text(observation + "\n", encoding="utf-8")
    report = evaluate_validation(str(tmp_path / "*.json"), observations)
    assert report.decision == "fail"
    assert set(report.failed_criteria) == {
        "eligible_ape_sample_below_8",
        "median_ape_above_15_percent",
        "p90_ape_above_30_percent",
        "cost_weighted_attribution_below_80_percent",
        "false_blocker_above_5_percent_or_no_denominator",
    }


def test_validation_rejects_duplicate_case_and_invalid_observation(tmp_path: Path) -> None:
    source = ROOT / "validation/predictions/northstar-added-table.json"
    (tmp_path / "one.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "two.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(InputError, match="Duplicate prediction"):
        evaluate_validation(
            str(tmp_path / "*.json"), ROOT / "validation/observations.jsonl"
        )
    invalid = tmp_path / "invalid.jsonl"
    invalid.write_text('{"schema_version":1}\n', encoding="utf-8")
    with pytest.raises(InputError, match="Invalid observation"):
        evaluate_validation(str(tmp_path / "one.json"), invalid)

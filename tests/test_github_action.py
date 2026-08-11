from __future__ import annotations

import json
from pathlib import Path

import pytest

from queryspend.demo import build_demo_report
from queryspend.github_action import _finalize, _preflight, _request_json
from queryspend.renderers.json import JsonRenderer


def test_action_preflight_rejects_symlink_escape(
    tmp_path: Path, monkeypatch: object
) -> None:
    # pytest's monkeypatch fixture is intentionally accessed dynamically for a narrow env mutation.
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    inside = tmp_path / "inside.json"
    inside.write_text("{}", encoding="utf-8")
    assert _preflight([str(inside)], output=str(tmp_path / "report.json")) == 0
    inside_link = tmp_path / "inside-link.json"
    inside_link.symlink_to(inside)
    assert _preflight([str(inside_link)]) == 2
    outside = tmp_path.parent / "outside-queryspend.json"
    outside.write_text("{}", encoding="utf-8")
    link = tmp_path / "escape.json"
    link.symlink_to(outside)
    assert _preflight([str(link)]) == 2
    assert _preflight([str(inside)], output=str(outside)) == 2
    outside.unlink()


def test_action_preflight_rejects_stale_output_controls_and_missing_input(
    tmp_path: Path, monkeypatch: object
) -> None:
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    stale = tmp_path / "report.json"
    stale.write_text(JsonRenderer().render(build_demo_report()), encoding="utf-8")

    # A failed check must never finalize a pre-existing attacker-controlled report.
    assert _preflight([str(manifest)], output=str(stale)) == 2
    assert _preflight([str(tmp_path / "missing.json")]) == 2
    assert _preflight([str(manifest)], output=str(tmp_path / "bad\noutput.json")) == 2
    assert _preflight([str(manifest) + "\n"]) == 2


def test_action_finalize_writes_outputs_and_summary(
    tmp_path: Path, monkeypatch: object
) -> None:
    report_path = tmp_path / "report.json"
    report_path.write_text(JsonRenderer().render(build_demo_report()), encoding="utf-8")
    outputs = tmp_path / "outputs"
    summary = tmp_path / "summary"
    monkeypatch.setenv("GITHUB_OUTPUT", str(outputs))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    assert _finalize(report_path, comment=False) == 0
    assert "decision=warn" in outputs.read_text(encoding="utf-8")
    assert "queryspend cost estimate" in summary.read_text(encoding="utf-8")
    finalized = json.loads(report_path.read_text(encoding="utf-8"))
    assert finalized["events"][-1]["name"] == "comment_published"


def test_action_api_rejects_token_forwarding_to_untrusted_host(
    monkeypatch: object,
) -> None:
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    with pytest.raises(ValueError, match="trusted GitHub host"):
        _request_json("https://example.invalid/repos/o/r", "TOPSECRET")

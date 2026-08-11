"""GitHub Action preflight, output, summary, and best-effort comment adapter."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from queryspend.cli import _atomic_write
from queryspend.models import LocalEvent, QuerySpendReport
from queryspend.renderers.json import JsonRenderer
from queryspend.renderers.markdown import MARKER, MarkdownRenderer

MAX_EVENT_BYTES = 1024 * 1024
MAX_API_RESPONSE_BYTES = 8 * 1024 * 1024
REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
SHA_PATTERN = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("paths", nargs="+")
    preflight.add_argument("--output")
    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--report", required=True, type=Path)
    finalize.add_argument("--comment", choices=("true", "false"), default="true")
    arguments = parser.parse_args()
    if arguments.command == "preflight":
        return _preflight(arguments.paths, output=arguments.output)
    return _finalize(arguments.report, comment=arguments.comment == "true")


def _preflight(paths: list[str], *, output: str | None = None) -> int:
    try:
        workspace = Path(os.environ.get("GITHUB_WORKSPACE", Path.cwd())).resolve(strict=True)
    except (OSError, RuntimeError):
        print("queryspend: GITHUB_WORKSPACE is unavailable", file=sys.stderr)
        return 2
    for value in paths:
        if _has_control(value):
            print(
                "queryspend: Action input paths must not contain control characters",
                file=sys.stderr,
            )
            return 2
        unresolved = Path(value)
        if unresolved.is_symlink():
            print("queryspend: Action inputs must not be symbolic links", file=sys.stderr)
            return 2
        try:
            path = unresolved.resolve(strict=True)
        except (OSError, RuntimeError):
            print("queryspend: Action input path is unavailable", file=sys.stderr)
            return 2
        if not path.is_relative_to(workspace):
            print("queryspend: Action input path escapes GITHUB_WORKSPACE", file=sys.stderr)
            return 2
        if not path.is_file():
            print("queryspend: Action inputs must be regular files", file=sys.stderr)
            return 2
    if output is not None:
        if _has_control(output):
            print("queryspend: report_path must not contain control characters", file=sys.stderr)
            return 2
        output_path = Path(output)
        if output_path.exists() or output_path.is_symlink():
            print(
                "queryspend: report_path already exists; refusing stale or untrusted output",
                file=sys.stderr,
            )
            return 2
        resolved_output = (
            output_path.resolve()
            if output_path.exists()
            else output_path.parent.resolve() / output_path.name
        )
        if not resolved_output.is_relative_to(workspace):
            print("queryspend: report_path escapes GITHUB_WORKSPACE", file=sys.stderr)
            return 2
    return 0


def _has_control(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _finalize(report_path: Path, *, comment: bool) -> int:
    try:
        report = QuerySpendReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        print("queryspend: could not read the sanitized report artifact", file=sys.stderr)
        return 2
    markdown = MarkdownRenderer().render(report)
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as handle:
            handle.write(markdown)
    _write_outputs(report, report_path)
    comment_result = "skipped"
    if comment:
        try:
            comment_result = _publish_comment(markdown)
        except (OSError, ValueError, urllib.error.URLError) as error:
            status = getattr(error, "code", "unavailable")
            print(
                f"queryspend: warning: PR comment was not published (HTTP {status}); "
                "the evaluation and artifact remain valid",
                file=sys.stderr,
            )
            comment_result = "failed"
    report.events.append(
        LocalEvent(
            name="comment_published",
            properties={
                "same_repo": comment_result not in {"fork", "skipped"},
                "result": comment_result,
            },
        )
    )
    _atomic_write(report_path, JsonRenderer().render(report))
    return 0


def _write_outputs(report: QuerySpendReport, report_path: Path) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    values = {
        "decision": report.policy.decision.value,
        "known_monthly_delta_usd": report.summary.known_monthly_delta_usd or "",
        "confidence": report.summary.confidence.value,
        "report_path": str(report_path),
    }
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def _publish_comment(markdown: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    event_path = os.getenv("GITHUB_EVENT_PATH")
    repository = os.getenv("GITHUB_REPOSITORY")
    if not token or not event_path or not repository:
        return "skipped"
    event_file = Path(event_path)
    if event_file.stat().st_size > MAX_EVENT_BYTES:
        raise ValueError("GitHub event exceeds supported size")
    event = json.loads(event_file.read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if isinstance(pull_request, dict):
        head = pull_request.get("head", {})
        base = pull_request.get("base", {})
        if not isinstance(head, dict) or not isinstance(base, dict):
            return "skipped"
        head_repo = head.get("repo", {})
        base_repo = base.get("repo", {})
        if not isinstance(head_repo, dict) or not isinstance(base_repo, dict):
            return "skipped"
        head_repo_name = head_repo.get("full_name")
        base_repo_name = base_repo.get("full_name")
        number = pull_request.get("number")
        event_head_sha = head.get("sha")
    else:
        # Trusted workflow_run evaluators pass the verified upstream PR context explicitly.
        head_repo_name = os.getenv("QUERYSPEND_PR_HEAD_REPO")
        base_repo_name = os.getenv("QUERYSPEND_PR_BASE_REPO")
        number_text = os.getenv("QUERYSPEND_PR_NUMBER", "")
        number = int(number_text) if number_text.isdigit() else None
        event_head_sha = os.getenv("QUERYSPEND_PR_HEAD_SHA")
    if head_repo_name != base_repo_name or base_repo_name != repository:
        return "fork"
    if (
        not isinstance(repository, str)
        or REPOSITORY_PATTERN.fullmatch(repository) is None
        or not isinstance(number, int)
        or number <= 0
        or not isinstance(event_head_sha, str)
        or SHA_PATTERN.fullmatch(event_head_sha) is None
    ):
        return "skipped"
    api = os.getenv("GITHUB_API_URL", "https://api.github.com")
    current = _request_json(f"{api}/repos/{repository}/pulls/{number}", token)
    current_head = current.get("head", {}) if isinstance(current, dict) else {}
    if not isinstance(current_head, dict) or current_head.get("sha") != event_head_sha:
        return "stale_head"
    comments = _request_json(
        f"{api}/repos/{repository}/issues/{number}/comments?per_page=100", token
    )
    existing_id = None
    if isinstance(comments, list):
        for item in comments:
            if not isinstance(item, dict) or MARKER not in str(item.get("body", "")):
                continue
            user = item.get("user", {})
            if isinstance(user, dict) and user.get("type") == "Bot":
                existing_id = item.get("id")
                break
    payload = {"body": markdown}
    if isinstance(existing_id, int):
        _request_json(
            f"{api}/repos/{repository}/issues/comments/{existing_id}",
            token,
            method="PATCH",
            payload=payload,
        )
        return "updated"
    _request_json(
        f"{api}/repos/{repository}/issues/{number}/comments",
        token,
        method="POST",
        payload=payload,
    )
    return "created"


def _request_json(
    url: str,
    token: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> Any:
    parsed = urllib.parse.urlparse(url)
    server = urllib.parse.urlparse(
        os.getenv("GITHUB_SERVER_URL", "https://github.com")
    )
    expected_host = "api.github.com" if server.hostname == "github.com" else server.hostname
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.hostname != expected_host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("GitHub API URL is not bound to the trusted GitHub host")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(  # noqa: S310 - HTTPS validated above
        url,
        method=method,
        data=data,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "queryspend-action",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
        body = response.read(MAX_API_RESPONSE_BYTES + 1)
        if len(body) > MAX_API_RESPONSE_BYTES:
            raise ValueError("GitHub API response exceeds supported size")
        return json.loads(body.decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())

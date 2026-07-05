from __future__ import annotations

import json

from tools import github_launch_audit


def _repo_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "description": github_launch_audit.EXPECTED_DESCRIPTION,
        "homepage": github_launch_audit.EXPECTED_HOMEPAGE,
        "topics": sorted(github_launch_audit.EXPECTED_TOPICS),
    }
    payload.update(overrides)
    return payload


def _workflow_run(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": "completed",
        "conclusion": "success",
        "head_sha": "abc",
        "html_url": "https://github.com/LeoKemp223/NextBoard/actions/runs/1",
    }
    payload.update(overrides)
    return payload


def test_build_report_is_ok_when_remote_metadata_and_ci_match() -> None:
    report = github_launch_audit.build_report(
        owner="LeoKemp223",
        repo="NextBoard",
        branch="main",
        workflow="ci.yml",
        local_sha="abc",
        remote_sha="abc",
        repository=_repo_payload(),
        workflow_run=_workflow_run(),
        remote="origin",
    )

    assert report.status == "ok"
    assert {check.name for check in report.checks} == {
        "remote.head",
        "repo.description",
        "repo.homepage",
        "repo.topics",
        "ci.main",
    }
    assert all(check.next_action == "No action required." for check in report.checks)


def test_build_report_reports_push_metadata_and_ci_gaps() -> None:
    report = github_launch_audit.build_report(
        owner="LeoKemp223",
        repo="NextBoard",
        branch="main",
        workflow="ci.yml",
        local_sha="local",
        remote_sha="remote",
        repository=_repo_payload(description="old", homepage="", topics=["hardware"]),
        workflow_run=_workflow_run(status="completed", conclusion="failure"),
        remote="origin",
    )

    errors = {check.name: check for check in report.checks if check.status == "error"}

    assert report.status == "error"
    assert set(errors) == {"remote.head", "repo.description", "repo.homepage", "repo.topics", "ci.main"}
    assert "push is still required" in errors["remote.head"].message
    assert "git push origin main" in errors["remote.head"].next_action
    assert "GitHub About description" in errors["repo.description"].next_action
    assert "GitHub About homepage" in errors["repo.homepage"].next_action
    assert "stm32" in errors["repo.topics"].details["missing"]
    assert "stm32" in errors["repo.topics"].next_action
    assert "fix the failing CI" in errors["ci.main"].next_action


def test_build_report_reports_stale_ci_commit() -> None:
    report = github_launch_audit.build_report(
        owner="LeoKemp223",
        repo="NextBoard",
        branch="main",
        workflow="ci.yml",
        local_sha="new-sha",
        remote_sha="new-sha",
        repository=_repo_payload(),
        workflow_run=_workflow_run(head_sha="old-sha"),
        remote="origin",
    )

    errors = {check.name: check for check in report.checks if check.status == "error"}

    assert report.status == "error"
    assert set(errors) == {"ci.main"}
    assert "does not match expected commit" in errors["ci.main"].message
    assert errors["ci.main"].details["expected_sha"] == "new-sha"


def test_missing_workflow_run_is_error() -> None:
    check = github_launch_audit.check_workflow_run(None, workflow="ci.yml", branch="main")

    assert check.status == "error"
    assert "No ci.yml workflow run found" in check.message
    assert "wait for the ci.yml GitHub Actions run" in check.next_action


def test_workflow_run_must_match_expected_commit() -> None:
    check = github_launch_audit.check_workflow_run(
        _workflow_run(head_sha="old-sha"),
        workflow="ci.yml",
        branch="main",
        expected_sha="new-sha",
    )

    assert check.status == "error"
    assert "does not match expected commit" in check.message
    assert "new-sha" in check.next_action
    assert check.details["head_sha"] == "old-sha"
    assert check.details["expected_sha"] == "new-sha"


def test_human_report_prints_next_actions_for_errors(capsys) -> None:
    report = github_launch_audit.build_report(
        owner="LeoKemp223",
        repo="NextBoard",
        branch="main",
        workflow="ci.yml",
        local_sha="local",
        remote_sha="remote",
        repository=_repo_payload(description="old", homepage="", topics=["hardware"]),
        workflow_run=None,
        remote="origin",
    )

    github_launch_audit.print_report(report, as_json=False)

    output = capsys.readouterr().out
    assert "next: Push local commits with `git push origin main`" in output
    assert "next: Set the GitHub About description" in output
    assert "next: Add these GitHub repository topics" in output
    assert "Suggested GitHub CLI commands:" in output
    assert "gh repo edit LeoKemp223/NextBoard `" in output
    assert f'--description "{github_launch_audit.EXPECTED_DESCRIPTION}"' in output
    assert f'--homepage "{github_launch_audit.EXPECTED_HOMEPAGE}"' in output
    assert "--add-topic stm32" in output


def test_print_settings_does_not_contact_git_or_github(monkeypatch, capsys) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> object:
        raise AssertionError("offline settings output should not inspect git or GitHub")

    monkeypatch.setattr(github_launch_audit, "local_head", fail_if_called)
    monkeypatch.setattr(github_launch_audit, "remote_head", fail_if_called)
    monkeypatch.setattr(github_launch_audit, "fetch_repository", fail_if_called)
    monkeypatch.setattr(github_launch_audit, "fetch_latest_workflow_run", fail_if_called)

    exit_code = github_launch_audit.main(["--print-settings"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "GitHub launch settings: LeoKemp223/NextBoard" in output
    assert github_launch_audit.EXPECTED_DESCRIPTION in output
    assert github_launch_audit.EXPECTED_HOMEPAGE in output
    assert "Suggested GitHub CLI commands:" in output
    assert "--add-topic stm32" in output


def test_print_settings_json(monkeypatch, capsys) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> object:
        raise AssertionError("offline settings output should not inspect git or GitHub")

    monkeypatch.setattr(github_launch_audit, "local_head", fail_if_called)
    monkeypatch.setattr(github_launch_audit, "remote_head", fail_if_called)
    monkeypatch.setattr(github_launch_audit, "fetch_repository", fail_if_called)
    monkeypatch.setattr(github_launch_audit, "fetch_latest_workflow_run", fail_if_called)

    exit_code = github_launch_audit.main(["--print-settings", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["repository"] == "LeoKemp223/NextBoard"
    assert payload["description"] == github_launch_audit.EXPECTED_DESCRIPTION
    assert payload["homepage"] == github_launch_audit.EXPECTED_HOMEPAGE
    assert payload["topics"] == sorted(github_launch_audit.EXPECTED_TOPICS)
    assert any("--description" in command for command in payload["commands"])


def test_runtime_errors_are_structured_json(monkeypatch, capsys) -> None:
    def raise_network_error() -> str:
        raise RuntimeError("fatal: unable to access remote")

    monkeypatch.setattr(github_launch_audit, "local_head", raise_network_error)

    exit_code = github_launch_audit.main(["--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "error"
    assert payload["checks"][0]["name"] == "audit.runtime"
    assert "fatal: unable to access remote" in payload["checks"][0]["message"]
    assert "Check network access" in payload["checks"][0]["next_action"]


def test_workflow_404_is_treated_as_missing_run(monkeypatch) -> None:
    def raise_not_found(url: str, *, token: str | None = None) -> dict[str, object]:
        raise github_launch_audit.GitHubApiError(f"missing: {url}", status_code=404)

    monkeypatch.setattr(github_launch_audit, "_request_json", raise_not_found)

    run = github_launch_audit.fetch_latest_workflow_run("LeoKemp223", "NextBoard", "ci.yml", "main")

    assert run is None

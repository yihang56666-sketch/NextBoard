from __future__ import annotations

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


def test_missing_workflow_run_is_error() -> None:
    check = github_launch_audit.check_workflow_run(None, workflow="ci.yml", branch="main")

    assert check.status == "error"
    assert "No ci.yml workflow run found" in check.message
    assert "wait for the ci.yml GitHub Actions run" in check.next_action


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


def test_workflow_404_is_treated_as_missing_run(monkeypatch) -> None:
    def raise_not_found(url: str, *, token: str | None = None) -> dict[str, object]:
        raise github_launch_audit.GitHubApiError(f"missing: {url}", status_code=404)

    monkeypatch.setattr(github_launch_audit, "_request_json", raise_not_found)

    run = github_launch_audit.fetch_latest_workflow_run("LeoKemp223", "NextBoard", "ci.yml", "main")

    assert run is None

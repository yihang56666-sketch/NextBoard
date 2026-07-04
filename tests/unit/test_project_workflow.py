from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, "tools")

import project_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "cubemx-basic"
TMP = REPO_ROOT / "tests" / "tmp" / "project-workflow"


def copy_fixture(name: str) -> Path:
    target = TMP / name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(FIXTURE, target)
    return target


def test_collect_project_state_recommends_onboarding_when_reports_missing() -> None:
    project = copy_fixture("missing-reports")
    state = project_workflow.collect_project_state(project)

    assert state["status"] in {"needs-onboarding", "needs-safe-discovery"}
    assert state["backend"]["backend"] == "keil"
    assert state["next_step"]["id"] == "run-onboard"
    assert state["next_step"]["safe_by_default"] is True
    assert state["next_step"]["touches_hardware"] is False
    assert state["next_step"]["argv"][:3] == ["python", "tools/hardware_butler.py", "onboard"]


def test_write_project_state_persists_machine_readable_state() -> None:
    project = copy_fixture("write-state")
    state = project_workflow.collect_project_state(project)
    path = project_workflow.write_project_state(project, state)

    saved = json.loads(path.read_text(encoding="utf-8"))
    assert path == project / ".hardware-butler" / "project-state.json"
    assert saved["schema_version"] == 1
    assert saved["root"] == str(project.resolve())
    assert saved["next_step"]["id"] == "run-onboard"


def test_run_auto_invokes_safe_onboarding_runner_and_updates_state() -> None:
    project = copy_fixture("auto-run")
    called: dict[str, str] = {}

    def fake_onboard(root: Path, out_dir: Path) -> dict[str, object]:
        called["root"] = str(root)
        called["out_dir"] = str(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "onboarding-manifest.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "root": str(root.resolve()),
                    "discovery": {"summary": {"ok": 1, "error": 0, "timeout": 0}},
                }
            ),
            encoding="utf-8",
        )
        return {"status": "ready-for-config-review", "root": str(root), "out_dir": str(out_dir)}

    result = project_workflow.run_auto(project, out_dir=project / "reports", onboard_runner=fake_onboard)

    assert called["root"] == str(project.resolve())
    assert result["automation"]["ran"] == ["onboard"]
    assert Path(result["state_path"]).name == "project-state.json"
    assert Path(result["state_path"]).parent.name == ".hardware-butler"
    assert Path(result["state_path"]).exists()
    assert result["state"]["next_step"]["id"] in {
        "review-config",
        "run-onboard",
        "review-hardware-preferences",
    }


def test_build_workbench_connects_state_actions_reports_and_safety() -> None:
    project = copy_fixture("workbench")
    model = project_workflow.build_workbench(project)

    assert model["schema_version"] == 1
    assert model["app"] == "hardware-butler-workbench"
    assert model["project"]["root"] == str(project.resolve())
    assert model["state"]["root"] == str(project.resolve())
    assert model["primary_action"]["id"] == model["state"]["next_step"]["id"]
    assert [action["id"] for action in model["actions"]][:3] == ["refresh", "auto", "brain"]
    assert all(action["safe_by_default"] for action in model["actions"])
    assert all(action["touches_hardware"] is False for action in model["actions"])
    assert {report["id"] for report in model["reports"]} >= {"project_dossier", "build_plan", "config_proposal"}
    assert model["brain"]["app"] == "hardware-project-brain"
    assert model["brain"]["identity"]["mcu"]["name"] == "STM32F407VGTx"
    assert model["artifact_summary"]["has_cubemx"] is True
    assert any(artifact["id"] == "cubemx_ioc" for artifact in model["artifacts"])
    assert all({"id", "type", "role", "path", "size_bytes"} <= set(artifact) for artifact in model["artifacts"])
    assert model["safety"]["real_hardware_actions"] == "planned-gated"


def test_workflow_reports_describe_expected_outputs() -> None:
    project = copy_fixture("reports")
    reports = project_workflow.workflow_reports(project, project / "reports")

    project_dossier = next(report for report in reports if report["id"] == "project_dossier")
    assert project_dossier["title"] == "Project dossier"
    assert project_dossier["role"] == "Project overview"
    assert project_dossier["path"].endswith("project-dossier.md")
    assert project_dossier["exists"] is False

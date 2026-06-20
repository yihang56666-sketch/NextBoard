"""Unit tests for build_plan module."""

import sys

sys.path.insert(0, 'tools')
from pathlib import Path

import build_plan


def test_generate_plan_creates_steps(cubemx_basic_fixture: Path):
    """generate_plan should create build steps."""
    plan = build_plan.generate_plan(cubemx_basic_fixture)

    assert plan["schema_version"] == 1
    assert plan["backend"] in ["keil", "cmake", "eide", "makefile"]
    assert len(plan["steps"]) > 0


def test_build_steps_have_required_fields(cubemx_basic_fixture: Path):
    """Build steps should have all required fields."""
    plan = build_plan.generate_plan(cubemx_basic_fixture)

    for step in plan["steps"]:
        assert "phase" in step
        assert "name" in step
        assert "argv" in step
        assert "safe" in step
        assert isinstance(step["argv"], list)


def test_render_markdown_includes_commands(cubemx_basic_fixture: Path):
    """Markdown output should include command details."""
    plan = build_plan.generate_plan(cubemx_basic_fixture)
    markdown = build_plan.render_markdown(plan)

    assert "Build Plan" in markdown
    assert plan["backend"] in markdown

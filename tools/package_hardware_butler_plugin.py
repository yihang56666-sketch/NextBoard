"""Package the hardware butler runtime into the repo-local Codex plugin."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO_ROOT / "plugins" / "hardware-development-butler"
RUNTIME_ROOT = PLUGIN_ROOT / "scripts"

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".tmp-pytest",
    ".tmp-plugin-smoke",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
}
EXCLUDED_DOC_RUNTIME_DIRS = {"inspections", "chip"}
EXCLUDED_RUNTIME_PARTS = {("tests", "tmp")}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
MANAGED_RUNTIME_ITEMS = {
    ".codex",
    "AGENTS.md",
    "README.md",
    "agents",
    "conftest.py",
    "docs",
    "embeddedskills",
    "nextboard",
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements.txt",
    "tests",
    "tools",
}
MANAGED_PLUGIN_SKILLS = {
    "chip-bringup",
}


def should_ignore(path: Path) -> bool:
    if path.name in EXCLUDED_DIRS:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    return False


def copy_tree(src: Path, dst: Path) -> None:
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if (src.name, *rel.parts[:1]) in EXCLUDED_RUNTIME_PARTS:
            continue
        if src.name == "docs" and rel.parts and rel.parts[0] in EXCLUDED_DOC_RUNTIME_DIRS:
            continue
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if should_ignore(path):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def clear_managed_runtime_payload() -> None:
    for name in MANAGED_RUNTIME_ITEMS:
        target = RUNTIME_ROOT / name
        if target.is_dir():
            clear_runtime_directory(target)
        elif target.exists():
            target.unlink()


def clear_runtime_directory(path: Path) -> None:
    """Remove packaged files while leaving local test/cache state alone."""
    for child in path.iterdir():
        if should_ignore(child):
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def sync_project_skills() -> list[str]:
    copied = []
    for name in MANAGED_PLUGIN_SKILLS:
        src = REPO_ROOT / ".agents" / "skills" / name
        dst = PLUGIN_ROOT / "skills" / name
        if not src.exists():
            continue
        if dst.exists():
            shutil.rmtree(dst)
        copy_tree(src, dst)
        copied.append(f"skills/{name}/")
    return copied


def package_runtime() -> list[str]:
    copied: list[str] = []
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    clear_managed_runtime_payload()

    for name in ("tools", "tests", "agents", ".codex", "embeddedskills", "nextboard"):
        copy_tree(REPO_ROOT / name, RUNTIME_ROOT / name)
        copied.append(f"{name}/")

    docs_dst = RUNTIME_ROOT / "docs"
    docs_dst.mkdir(parents=True, exist_ok=True)
    for doc in sorted((REPO_ROOT / "docs").glob("*.md")):
        copy_file(doc, docs_dst / doc.name)
        copied.append(f"docs/{doc.name}")

    for name in ("README.md", "AGENTS.md", "pyproject.toml", "requirements.txt", "requirements-dev.txt", "conftest.py"):
        copy_file(REPO_ROOT / name, RUNTIME_ROOT / name)
        copied.append(name)

    copied.extend(sync_project_skills())
    return copied


def main() -> None:
    copied = package_runtime()
    print(f"Packaged runtime into {RUNTIME_ROOT}")
    for item in copied:
        print(f"- {item}")


if __name__ == "__main__":
    main()

"""Pytest configuration and fixtures."""

import sys
from pathlib import Path

import pytest

# Add tools and embeddedskills to path
REPO_ROOT = Path(__file__).parent
TOOLS_DIR = REPO_ROOT / "tools"

if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import runtime_context  # noqa: E402

EMBEDDED_DIR = runtime_context.embeddedskills_root()
if str(EMBEDDED_DIR) not in sys.path:
    sys.path.insert(0, str(EMBEDDED_DIR))


@pytest.fixture
def repo_root() -> Path:
    """Repository root directory."""
    return REPO_ROOT


@pytest.fixture
def tools_dir() -> Path:
    """Tools directory."""
    return TOOLS_DIR


@pytest.fixture
def test_fixture_dir() -> Path:
    """Test fixtures directory."""
    return REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def cubemx_basic_fixture(test_fixture_dir: Path) -> Path:
    """CubeMX basic test fixture."""
    fixture = test_fixture_dir / "cubemx-basic"
    if not fixture.exists():
        pytest.skip("CubeMX basic fixture not found")
    return fixture


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Temporary workspace for tests."""
    workspace = tmp_path / "test-workspace"
    workspace.mkdir()
    return workspace


def _pytest_embedded_installed() -> bool:
    """Return True when the pytest-embedded plugin is importable.

    pytest-embedded already registers ``--target`` and ``--port`` (and a real
    ``dut`` fixture). When it is present we must not re-register those options
    or pytest aborts with an argparse conflict; we only add our own
    ``--run-hardware`` gate. When it is absent we provide lightweight fallbacks
    so the hardware suite stays collectable.
    """
    import importlib.util

    return importlib.util.find_spec("pytest_embedded") is not None


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register opt-in switches for tests with physical side effects.

    ``pytest_addoption`` is only honoured in the rootdir ``conftest.py`` (or a
    plugin), so the hardware-bench options live here even though the matching
    fixtures live in ``tests/conftest.py``.
    """
    parser.addoption(
        "--run-hardware",
        action="store_true",
        default=False,
        help="Run tests marked hardware. These may require connected probes or boards.",
    )
    if _pytest_embedded_installed():
        # pytest-embedded owns --target/--port; re-registering them would make
        # pytest fail to start with an argparse conflict.
        return
    parser.addoption(
        "--target",
        action="store",
        default="stm32f407vgtx",
        help="Target MCU for hardware tests.",
    )
    parser.addoption(
        "--port",
        action="store",
        default=None,
        help="Serial port for hardware communication.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Keep normal test runs off real probes and boards unless explicitly requested."""
    if config.getoption("--run-hardware"):
        return

    skip_hardware = pytest.mark.skip(reason="requires --run-hardware")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip_hardware)

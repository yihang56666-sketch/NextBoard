"""LangChain integration for natural language hardware operations.

Wraps hardware_butler tools as LangChain tools for conversational AI.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    from langchain.agents import AgentType, Tool, initialize_agent  # type: ignore[attr-defined]
    from langchain.llms.base import BaseLLM
    from langchain_anthropic import ChatAnthropic
    LANGCHAIN_AVAILABLE = True
except ImportError:
    Tool = Any
    BaseLLM = Any
    ChatAnthropic = None
    initialize_agent = None
    AgentType = None
    LANGCHAIN_AVAILABLE = False

import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from langchain.llms.base import BaseLLM as LangChainBaseLLM
else:
    LangChainBaseLLM = Any


class HardwareButlerTools:
    """Hardware butler operations as LangChain tools."""

    def __init__(self, workspace_root: Path):
        """Initialize tools.

        Args:
            workspace_root: Hardware-agent workspace root
        """
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError("langchain not installed")

        self.workspace_root = workspace_root
        logger.info("HardwareButlerTools initialized")

    def _onboard_project(self, project_path: str) -> str:
        """Onboard a hardware project."""
        try:
            # Import here to avoid circular deps
            import hardware_butler_inspect

            result = hardware_butler_inspect.inspect_project(
                Path(project_path),
                self.workspace_root / "docs" / "inspections" / Path(project_path).name
            )
            return f"Project onboarded: {result['status']}"
        except Exception as e:
            return f"Error: {e}"

    def _flash_firmware(self, params: str) -> str:
        """Prepare a gated flash plan instead of touching real hardware.

        Args format: "firmware_path,target"
        """
        try:
            parts = params.split(',')
            if len(parts) != 2:
                return "Error: Use format 'firmware_path,target'"

            firmware_path, target = parts
            firmware_path = firmware_path.strip()
            target = target.strip()
            return (
                "FlashFirmware is planned-gated and did not execute real hardware. "
                "Use tools.hardware_action_plan to create a confirmed action package, "
                "then route execution through tools.hardware_action_executor after "
                f"bench validation. Requested firmware={firmware_path}, target={target}."
            )
        except Exception as e:
            return f"Error: {e}"

    def _query_chip_manual(self, question: str) -> str:
        """Query chip manual using RAG."""
        try:
            from backends.chip_manual_rag import ChipManualRAG

            # Assume docs in docs/chip/
            rag = ChipManualRAG(self.workspace_root / "docs" / "chip")
            result = rag.query(question)
            return str(result["answer"])
        except Exception as e:
            return f"Error: {e}"

    def _list_probes(self, _: str) -> str:
        """List connected debug probes."""
        try:
            from backends.pyocd_backend import PyOCDBackend

            backend = PyOCDBackend()
            probes = backend.list_probes()

            if not probes:
                return "No debug probes found"

            lines = [f"Found {len(probes)} probe(s):"]
            for probe in probes:
                lines.append(f"  - {probe.product_name} ({probe.unique_id})")

            return "\n".join(lines)
        except Exception as e:
            return f"Error: {e}"

    def _build_project(self, project_path: str) -> str:
        """Build project."""
        try:
            import build_plan

            plan = build_plan.generate_plan(Path(project_path))
            return f"Build plan generated: {len(plan['commands'])} steps"
        except Exception as e:
            return f"Error: {e}"

    def get_tools(self) -> list[Tool]:
        """Get LangChain tools list."""
        return [
            Tool(
                name="OnboardProject",
                func=self._onboard_project,
                description="Onboard a hardware project. Input: project path"
            ),
            Tool(
                name="FlashFirmware",
                func=self._flash_firmware,
                description="Flash firmware to target. Input: 'firmware_path,target' (e.g., 'fw.hex,stm32f407vgtx')"
            ),
            Tool(
                name="QueryChipManual",
                func=self._query_chip_manual,
                description="Query chip documentation. Input: question about chip"
            ),
            Tool(
                name="ListProbes",
                func=self._list_probes,
                description="List connected debug probes. Input: ignored"
            ),
            Tool(
                name="BuildProject",
                func=self._build_project,
                description="Generate build plan for project. Input: project path"
            ),
        ]


class HardwareAgent:
    """Conversational hardware development agent."""

    def __init__(
        self,
        workspace_root: Path,
        llm: LangChainBaseLLM | None = None,
        api_key: str | None = None,
    ):
        """Initialize agent.

        Args:
            workspace_root: Hardware-agent workspace
            llm: Optional LLM instance
            api_key: Optional Anthropic API key
        """
        if not LANGCHAIN_AVAILABLE:
            raise RuntimeError("langchain not installed")

        # Setup LLM
        if llm is None:
            import os
            api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")
            llm = ChatAnthropic(model="claude-sonnet-4-6", api_key=api_key)

        # Setup tools
        butler_tools = HardwareButlerTools(workspace_root)
        tools = butler_tools.get_tools()

        # Initialize agent
        self.agent = initialize_agent(
            tools,
            llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
        )

        logger.info("HardwareAgent initialized")

    def run(self, task: str) -> str:
        """Execute natural language task.

        Args:
            task: Task description in natural language

        Returns:
            Task result
        """
        try:
            result = self.agent.run(task)
            return str(result)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return f"Error: {e}"


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python langchain_agent.py '<task description>'")
        print("Example: python langchain_agent.py '列出连接的调试器'")
        sys.exit(1)

    workspace = Path(__file__).parent.parent.parent
    agent = HardwareAgent(workspace)

    task = " ".join(sys.argv[1:])
    result = agent.run(task)

    print("\nResult:")
    print(result)

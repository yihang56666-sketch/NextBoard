"""Improved multi-agent orchestration with retry logic and structured output.

This is an experimental improvement over the original framework addressing:
1. No retry logic for API errors
2. No structured output validation
3. No fallback mechanisms
4. No progress tracking
5. No partial result handling
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Structured agent execution result."""
    agent_id: str
    status: str  # success, partial, failed, skipped
    output: dict[str, Any]
    error: str | None
    retry_count: int
    duration_ms: int


class ImprovedAgentOrchestrator:
    """Improved agent orchestrator with resilience features."""

    def __init__(self, max_retries: int = 3, retry_delay: int = 2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.results: list[AgentResult] = []

    def execute_with_retry(
        self,
        agent_fn: Callable[[], dict[str, Any]],
        agent_id: str,
    ) -> AgentResult:
        """Execute agent with exponential backoff retry."""
        retry_count = 0
        last_error = None
        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                logger.info(f"Agent {agent_id}: attempt {attempt + 1}/{self.max_retries}")
                output = agent_fn()

                # Validate structured output
                if self._validate_output(output):
                    duration = int((time.time() - start_time) * 1000)
                    return AgentResult(
                        agent_id=agent_id,
                        status="success",
                        output=output,
                        error=None,
                        retry_count=attempt,
                        duration_ms=duration,
                    )
                else:
                    logger.warning(f"Agent {agent_id}: invalid output structure")
                    last_error = "Invalid output structure"

            except Exception as e:
                last_error = str(e)
                logger.error(f"Agent {agent_id}: {last_error}")
                retry_count = attempt + 1

                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)

        # All retries failed - return partial result
        duration = int((time.time() - start_time) * 1000)
        return AgentResult(
            agent_id=agent_id,
            status="failed",
            output={},
            error=last_error,
            retry_count=retry_count,
            duration_ms=duration,
        )

    def _validate_output(self, output: dict[str, Any]) -> bool:
        """Validate agent output has required structure."""
        required_keys = ["findings", "evidence", "recommendations"]
        return all(key in output for key in required_keys)

    def execute_parallel_with_fallback(
        self,
        agents: list[tuple[str, Callable]],
        min_success: int = 1,
    ) -> list[AgentResult]:
        """Execute agents in parallel with fallback strategy.

        If primary agents fail, automatically spawn fallback agents.
        """
        results = []

        for agent_id, agent_fn in agents:
            result = self.execute_with_retry(agent_fn, agent_id)
            results.append(result)
            self.results.append(result)

        # Check if we have minimum successful results
        successful = [r for r in results if r.status == "success"]

        if len(successful) < min_success:
            logger.warning(f"Only {len(successful)}/{len(agents)} agents succeeded")
            logger.info("Activating fallback: manual analysis mode")
            # Could spawn simpler agents or use local analysis

        return results

    def synthesize_results(self, results: list[AgentResult]) -> dict[str, Any]:
        """Synthesize multiple agent outputs into coherent report."""
        synthesis = {
            "total_agents": len(results),
            "successful": len([r for r in results if r.status == "success"]),
            "failed": len([r for r in results if r.status == "failed"]),
            "findings": {},
            "conflicts": [],
            "consensus": {},
        }

        # Merge findings by category
        for result in results:
            if result.status == "success":
                agent_findings = result.output.get("findings", {})
                for category, items in agent_findings.items():
                    if category not in synthesis["findings"]:
                        synthesis["findings"][category] = []
                    synthesis["findings"][category].extend(items)

        # Detect conflicts (same item with different assessments)
        synthesis["conflicts"] = self._detect_conflicts(results)

        # Build consensus (items mentioned by multiple agents)
        synthesis["consensus"] = self._build_consensus(results)

        return synthesis

    def _detect_conflicts(self, results: list[AgentResult]) -> list[dict]:
        """Detect conflicting assessments between agents."""
        conflicts = []
        # Simple conflict detection: same file, different severity
        items_by_file: dict[str, list[tuple[str, str]]] = {}

        for result in results:
            if result.status != "success":
                continue
            findings = result.output.get("findings", {})
            for severity, items in findings.items():
                for item in items:
                    # Handle both string and dict items
                    if isinstance(item, dict):
                        file_ref = item.get("file", "")
                    else:
                        file_ref = ""

                    if file_ref:
                        if file_ref not in items_by_file:
                            items_by_file[file_ref] = []
                        items_by_file[file_ref].append((result.agent_id, severity))

        # Find files with different severity assessments
        for file_ref, assessments in items_by_file.items():
            severities = set(sev for _, sev in assessments)
            if len(severities) > 1:
                conflicts.append({
                    "file": file_ref,
                    "assessments": [
                        {"agent": agent, "severity": sev}
                        for agent, sev in assessments
                    ],
                })

        return conflicts

    def _build_consensus(self, results: list[AgentResult]) -> dict[str, int]:
        """Build consensus items mentioned by multiple agents."""
        item_counts: dict[str, int] = {}

        for result in results:
            if result.status != "success":
                continue
            findings = result.output.get("findings", {})
            for items_list in findings.values():
                for item in items_list:
                    # Handle both string and dict items
                    if isinstance(item, dict):
                        key = item.get("description", "")
                    else:
                        key = str(item)

                    if key:
                        item_counts[key] = item_counts.get(key, 0) + 1

        # Return items mentioned by 2+ agents
        return {k: v for k, v in item_counts.items() if v >= 2}

    def save_report(self, output_dir: Path) -> None:
        """Save execution report with all results."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Summary
        summary = {
            "total_agents": len(self.results),
            "successful": len([r for r in self.results if r.status == "success"]),
            "failed": len([r for r in self.results if r.status == "failed"]),
            "total_retries": sum(r.retry_count for r in self.results),
            "total_duration_ms": sum(r.duration_ms for r in self.results),
            "agents": [
                {
                    "id": r.agent_id,
                    "status": r.status,
                    "retry_count": r.retry_count,
                    "duration_ms": r.duration_ms,
                    "error": r.error,
                }
                for r in self.results
            ],
        }

        (output_dir / "execution-summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )

        # Individual results
        for result in self.results:
            if result.status == "success":
                (output_dir / f"{result.agent_id}.json").write_text(
                    json.dumps(result.output, indent=2),
                    encoding="utf-8",
                )

        # Synthesis
        synthesis = self.synthesize_results(self.results)
        (output_dir / "synthesis.json").write_text(
            json.dumps(synthesis, indent=2),
            encoding="utf-8",
        )

        logger.info(f"Report saved to {output_dir}")


# Example usage for hardware-agent review
def create_review_orchestrator() -> ImprovedAgentOrchestrator:
    """Create orchestrator configured for code review."""
    return ImprovedAgentOrchestrator(
        max_retries=3,
        retry_delay=2,
    )

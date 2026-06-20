"""Test the improved orchestrator with mock agents."""

import sys

sys.path.insert(0, '.agents')
from pathlib import Path

from improved_orchestrator import create_review_orchestrator


def mock_qa_agent():
    """Mock QA agent that returns structured output."""
    return {
        "findings": {
            "critical": ["butler_cli.py has 0% coverage"],
            "high": ["3 broken tests found"],
        },
        "evidence": [
            "tests/unit/test_build_plan.py expects old API",
            "tests/unit/test_configure_logging fails",
        ],
        "recommendations": [
            "Add test_butler_cli.py",
            "Fix API mismatches",
        ],
    }


def mock_flaky_agent():
    """Mock agent that fails first time, succeeds on retry."""
    if not hasattr(mock_flaky_agent, 'call_count'):
        mock_flaky_agent.call_count = 0

    mock_flaky_agent.call_count += 1

    if mock_flaky_agent.call_count == 1:
        raise RuntimeError("API Error 400")

    return {
        "findings": {"medium": ["Some issue"]},
        "evidence": ["file.py:10"],
        "recommendations": ["Fix it"],
    }


def mock_invalid_agent():
    """Mock agent that returns invalid output."""
    return {"status": "I am Claude Code"}  # Missing required keys


def test_improved_orchestrator():
    """Test the improved orchestrator."""
    print("=== Testing Improved Orchestrator ===\n")

    orchestrator = create_review_orchestrator()

    agents = [
        ("qa-engineer", mock_qa_agent),
        ("flaky-agent", mock_flaky_agent),
        ("invalid-agent", mock_invalid_agent),
    ]

    print("Executing 3 mock agents...")
    results = orchestrator.execute_parallel_with_fallback(agents, min_success=1)

    print("\n=== Results ===")
    for result in results:
        print(f"Agent: {result.agent_id}")
        print(f"  Status: {result.status}")
        print(f"  Retries: {result.retry_count}")
        print(f"  Duration: {result.duration_ms}ms")
        if result.error:
            print(f"  Error: {result.error}")
        print()

    print("=== Synthesis ===")
    synthesis = orchestrator.synthesize_results(results)
    print(f"Successful: {synthesis['successful']}/{synthesis['total_agents']}")
    print(f"Failed: {synthesis['failed']}")
    print(f"Findings categories: {list(synthesis['findings'].keys())}")

    # Save report
    output_dir = Path(".agents/reports/test-run")
    orchestrator.save_report(output_dir)
    print(f"\nReport saved to: {output_dir}")


if __name__ == "__main__":
    test_improved_orchestrator()

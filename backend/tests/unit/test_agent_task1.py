"""Regression tests for Task 1: Call an LLM from Code.

Tests verify that agent.py:
1. Outputs valid JSON with required fields (answer, tool_calls)
2. Exits with code 0 on success
3. Handles command-line arguments correctly
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with answer and tool_calls fields."""
    # Run agent with a simple question
    result = subprocess.run(
        [sys.executable, "agent.py", "What is 2 + 2? Answer with just the number."],
        capture_output=True,
        text=True,
        timeout=60,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {result.stderr}"

    # Check stdout is not empty
    assert result.stdout.strip(), "Agent produced no output"

    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e

    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert len(data["answer"].strip()) > 0, "'answer' must not be empty"

    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be a list"
    assert len(data["tool_calls"]) == 0, "'tool_calls' must be empty for Task 1"


def test_agent_no_argument_exits_with_error():
    """Test that agent.py exits with error when no question is provided."""
    result = subprocess.run(
        [sys.executable, "agent.py"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    # Should exit with non-zero code
    assert result.returncode != 0, "Agent should exit with error when no argument provided"

    # Error message should go to stderr
    assert result.stderr.strip(), "Agent should print usage to stderr"

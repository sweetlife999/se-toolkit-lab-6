"""Regression tests for the System Agent (Task 3).
"""Regression tests for the Documentation Agent (Task 2).

Tests verify that agent.py:
1. Outputs valid JSON with required fields (answer, source, tool_calls)
2. Uses read_file tool for documentation questions
3. Uses list_files tool for directory exploration questions
4. Exits with code 0 on success
"""Regression test for Task 1: Call an LLM from Code.

Tests verify that agent.py:
1. Outputs valid JSON with required fields (answer, source, tool_calls)
2. Uses read_file tool for source code questions
3. Uses query_api tool for data questions
4. Uses list_files tool for directory exploration questions
5. Exits with code 0 on success
"""

import json
import subprocess
import sys


def run_agent(question: str, timeout: int = 120) -> tuple[dict, str]:
    """Run the agent with a question and return parsed output.
    
    Returns:
        Tuple of (parsed_json_dict, stderr_output)
    """
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    
    stderr = result.stderr
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {stderr}"
    
    # Check stdout is not empty
    assert result.stdout.strip(), f"Agent produced no output. Stderr: {stderr}"
    
def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with answer and tool_calls fields."""
    # Run agent with a simple question
    result = subprocess.run(
        [sys.executable, "agent.py", question],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    
    stderr = result.stderr
    
    # Check exit code
    assert result.returncode == 0, f"Agent exited with code {result.returncode}: {stderr}"
    
    # Check stdout is not empty
    assert result.stdout.strip(), f"Agent produced no output. Stderr: {stderr}"
    
    # Parse JSON
    try:
        data = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout[:200]}") from e
    
    return data, stderr


def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with answer, source, and tool_calls fields."""
    data, stderr = run_agent("What is 2 + 2? Answer with just the number.")
    

def test_agent_outputs_valid_json():
    """Test that agent.py outputs valid JSON with answer, source, and tool_calls fields."""
    data, stderr = run_agent("What is 2 + 2? Answer with just the number.")
    
    # Check required fields
    assert "answer" in data, "Missing 'answer' field in output"
    assert isinstance(data["answer"], str), "'answer' must be a string"
    assert len(data["answer"].strip()) > 0, "'answer' must not be empty"
    
    assert "source" in data, "Missing 'source' field in output"
    assert isinstance(data["source"], str), "'source' must be a string"
    
    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be a list"


def test_agent_read_file_tool():
    """Test that agent uses read_file tool for documentation questions.
    
    Question: "How do you resolve a merge conflict?"
    Expected: read_file in tool_calls, wiki/git-workflow.md in source
    """
    data, stderr = run_agent("How do you resolve a merge conflict?")
    
    # Check tool_calls is not empty
    tool_calls = data.get("tool_calls", [])
    assert len(tool_calls) > 0, "Expected tool_calls to be non-empty for documentation question"
    
    # Check that read_file was used
    tools_used = [tc.get("tool") for tc in tool_calls]
    assert "read_file" in tools_used, f"Expected 'read_file' in tool_calls, got: {tools_used}"
    
    # Check source contains wiki reference
    source = data.get("source", "")
    assert "wiki/" in source.lower() or "git" in source.lower(), \
        f"Expected wiki reference in source, got: {source}"


def test_agent_list_files_tool():
    """Test that agent uses list_files tool for directory exploration questions.
    
    Question: "What files are in the wiki?"
    Expected: list_files in tool_calls
    """
    data, stderr = run_agent("What files are in the wiki directory?")
    
    # Check tool_calls is not empty
    tool_calls = data.get("tool_calls", [])
    assert len(tool_calls) > 0, "Expected tool_calls to be non-empty for directory question"
    
    # Check that list_files was used
    tools_used = [tc.get("tool") for tc in tool_calls]
    assert "list_files" in tools_used, f"Expected 'list_files' in tool_calls, got: {tools_used}"


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

    assert "tool_calls" in data, "Missing 'tool_calls' field in output"
    assert isinstance(data["tool_calls"], list), "'tool_calls' must be a list"


def test_agent_read_file_for_source_code():
    """Test that agent uses read_file tool for source code questions.
    
    Question: "What Python web framework does the backend use?"
    Expected: read_file in tool_calls, FastAPI in answer
    """
    data, stderr = run_agent("What Python web framework does the backend use? Read the source code to find out.")
    
    # Check tool_calls is not empty
    tool_calls = data.get("tool_calls", [])
    assert len(tool_calls) > 0, "Expected tool_calls to be non-empty for source code question"
    
    # Check that read_file was used
    tools_used = [tc.get("tool") for tc in tool_calls]
    assert "read_file" in tools_used, f"Expected 'read_file' in tool_calls, got: {tools_used}"
    
    # Check answer contains FastAPI
    answer = data.get("answer", "").lower()
    assert "fastapi" in answer, f"Expected 'FastAPI' in answer, got: {data.get('answer')}"


def test_agent_query_api_for_data():
    """Test that agent uses query_api tool for data questions.
    
    Question: "How many items are in the database?"
    Expected: query_api in tool_calls, a number in answer
    """
    data, stderr = run_agent("How many items are currently stored in the database? Query the API to find out.")
    
    # Check tool_calls is not empty
    tool_calls = data.get("tool_calls", [])
    assert len(tool_calls) > 0, "Expected tool_calls to be non-empty for data question"
    
    # Check that query_api was used
    tools_used = [tc.get("tool") for tc in tool_calls]
    assert "query_api" in tools_used, f"Expected 'query_api' in tool_calls, got: {tools_used}"
    
    # Check answer contains a number
    answer = data.get("answer", "")
    import re
    numbers = re.findall(r'\d+', answer)
    assert len(numbers) > 0, f"Expected a number in answer, got: {answer}"


def test_agent_list_files_for_directory():
    """Test that agent uses list_files tool for directory exploration questions.
    
    Question: "What files are in the wiki directory?"
    Expected: list_files in tool_calls
    """
    data, stderr = run_agent("What files are in the wiki directory?")
    
    # Check tool_calls is not empty
    tool_calls = data.get("tool_calls", [])
    assert len(tool_calls) > 0, "Expected tool_calls to be non-empty for directory question"
    
    # Check that list_files was used
    tools_used = [tc.get("tool") for tc in tool_calls]
    assert "list_files" in tools_used, f"Expected 'list_files' in tool_calls, got: {tools_used}"


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

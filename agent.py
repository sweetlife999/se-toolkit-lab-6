#!/usr/bin/env python3
"""Agent CLI - Calls an LLM with tools and returns a structured JSON answer.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
    All debug output goes to stderr.
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx

# Maximum number of tool calls per question
MAX_TOOL_CALLS = 10


def load_env() -> None:
    """Load environment variables from .env.agent.secret and .env.docker.secret."""
    # Load LLM config from .env.agent.secret
    agent_env_file = Path(__file__).parent / ".env.agent.secret"
    if agent_env_file.exists():
        for line in agent_env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

    # Load LMS API key from .env.docker.secret
    docker_env_file = Path(__file__).parent / ".env.docker.secret"
    if docker_env_file.exists():
        for line in docker_env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def get_llm_config() -> tuple[str, str, str]:
    """Get LLM configuration from environment."""
    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE")
    model = os.environ.get("LLM_MODEL")

    if not api_key:
        print("Error: LLM_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    if not api_base:
        print("Error: LLM_API_BASE not set", file=sys.stderr)
        sys.exit(1)
    if not model:
        print("Error: LLM_MODEL not set", file=sys.stderr)
        sys.exit(1)

    return api_key, api_base, model


def get_api_config() -> tuple[str, str]:
    """Get API configuration for query_api tool."""
    api_key = os.environ.get("LMS_API_KEY")
    base_url = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")

    if not api_key:
        print("Error: LMS_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    return api_key, base_url


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent


def validate_path(path: str) -> tuple[bool, str]:
    """Validate that a path is safe and within the project directory.
    
    Returns (is_valid, error_message).
    """
    # Check for path traversal attempts
    if ".." in path:
        return False, "Path traversal not allowed"
    
    # Check for absolute paths
    if path.startswith("/") or (len(path) > 1 and path[1] == ":"):
        return False, "Absolute paths not allowed"
    
    # Resolve the path and check it's within project root
    project_root = get_project_root()
    try:
        full_path = (project_root / path).resolve()
        if not str(full_path).startswith(str(project_root.resolve())):
            return False, "Path outside project directory"
    except Exception as e:
        return False, f"Invalid path: {e}"
    
    return True, ""


def read_file(path: str) -> str:
    """Read contents of a file from the project.
    
    Args:
        path: Relative path from project root.
    
    Returns:
        File contents as string, or error message.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return f"Error: {error}"
    
    project_root = get_project_root()
    full_path = project_root / path
    
    if not full_path.exists():
        return f"Error: File not found: {path}"
    
    if not full_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        return full_path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories at a given path.
    
    Args:
        path: Relative directory path from project root.
    
    Returns:
        Newline-separated listing of entries, or error message.
    """
    is_valid, error = validate_path(path)
    if not is_valid:
        return f"Error: {error}"
    
    project_root = get_project_root()
    full_path = project_root / path
    
    if not full_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not full_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        entries = sorted([e.name for e in full_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


def query_api(method: str, path: str, body: str = None) -> str:
    """Call the backend API.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API path (e.g., '/items/', '/analytics/completion-rate')
        body: Optional JSON request body for POST/PUT requests
    
    Returns:
        JSON string with status_code and body, or error message.
    """
    api_key, base_url = get_api_config()
    
    # Validate path (basic security)
    if not path.startswith("/"):
        return "Error: Path must start with /"
    
    if ".." in path:
        return "Error: Path traversal not allowed"
    
    url = f"{base_url}{path}"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    print(f"  Calling API: {method} {url}...", file=sys.stderr)
    
    try:
        if method.upper() == "GET":
            response = httpx.get(url, headers=headers, timeout=30)
        elif method.upper() == "POST":
            data = json.loads(body) if body else {}
            response = httpx.post(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "PUT":
            data = json.loads(body) if body else {}
            response = httpx.put(url, headers=headers, json=data, timeout=30)
        elif method.upper() == "DELETE":
            response = httpx.delete(url, headers=headers, timeout=30)
        else:
            return f"Error: Unsupported method: {method}"
        
        result = {
            "status_code": response.status_code,
            "body": response.text,
        }
        return json.dumps(result)
    
    except httpx.TimeoutException:
        return "Error: API request timed out"
    except httpx.HTTPError as e:
        return f"Error: HTTP request failed: {e}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON body: {e}"
    except Exception as e:
        return f"Error: {e}"


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository. Use this to read documentation (wiki/*.md), source code (backend/app/*.py), or configuration files (docker-compose.yml, Dockerfile).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md', 'backend/app/main.py', 'docker-compose.yml')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to explore the project structure, find wiki files, or discover API router modules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app/routers')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call the backend API to query live data, test endpoints, or check system behavior. Use this for questions about item counts, HTTP status codes, completion rates, or to reproduce errors. The API requires authentication.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method (GET, POST, PUT, DELETE)"
                    },
                    "path": {
                        "type": "string",
                        "description": "API path (e.g., '/items/', '/analytics/completion-rate', '/analytics/top-learners')"
                    },
                    "body": {
                        "type": "string",
                        "description": "JSON request body (optional, for POST/PUT requests)"
                    }
                },
                "required": ["method", "path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api,
}


# ---------------------------------------------------------------------------
# LLM Communication
# ---------------------------------------------------------------------------

def call_llm(messages: list[dict], api_key: str, api_base: str, model: str, timeout: int = 60) -> dict:
    """Call the LLM API and return the response.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        api_key: API key for authentication
        api_base: Base URL of the API
        model: Model name to use
        timeout: Request timeout in seconds
    
    Returns:
        Parsed JSON response from the API
    """
    url = f"{api_base}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOLS,
    }
    
    print(f"Calling LLM at {url}...", file=sys.stderr)
    
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException:
        print(f"Error: LLM request timed out after {timeout}s", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPError as e:
        print(f"Error: HTTP request failed: {e}", file=sys.stderr)
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON response: {e}", file=sys.stderr)
        sys.exit(1)
    
    return data


# ---------------------------------------------------------------------------
# Agentic Loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a documentation and system assistant with access to a project wiki, source code, and a live backend API.

Available tools:
1. list_files: List files in a directory. Use this to explore the wiki structure or find source files.
2. read_file: Read contents of a file. Use this to:
   - Read wiki documentation (wiki/*.md) for how-to questions
   - Read source code (backend/app/*.py) to find framework info, endpoints, or bugs
   - Read configuration files (docker-compose.yml, Dockerfile) for deployment info
3. query_api: Call the backend API. Use this to:
   - Query live data (e.g., GET /items/ to count items)
   - Test endpoints (e.g., GET /items/ without auth to get status code)
   - Reproduce errors (e.g., GET /analytics/completion-rate?lab=lab-99)
   - Get system information (completion rates, top learners, etc.)

When answering questions:
1. For wiki/how-to questions: Use list_files to explore wiki, then read_file to find the answer.
2. For source code questions (e.g., "what framework"): Use read_file on backend/app/main.py.
3. For data questions (e.g., "how many items"): Use query_api to query the live system.
4. For status code questions: Use query_api without auth headers to get the error response.
5. For bug diagnosis: Use query_api to reproduce the error, then read_file to find the buggy code.

Always provide a source reference when possible:
- For wiki: wiki/filename.md#section-anchor
- For source code: backend/app/filename.py
- For API responses: API endpoint (e.g., GET /items/)

Convert section headers to anchors by: lowercase, replace spaces with hyphens, remove special chars.
Example: "## Resolving Merge Conflicts" -> wiki/git-workflow.md#resolving-merge-conflicts

When you have found the answer, respond with a final message (no tool calls) that includes:
- A clear answer
- A source reference (if applicable)
"""


def execute_tool_call(tool_call: dict) -> str:
    """Execute a single tool call and return the result.
    
    Args:
        tool_call: Dict with 'function' containing 'name' and 'arguments'
    
    Returns:
        Tool result as string
    """
    function = tool_call.get("function", {})
    name = function.get("name")
    arguments_str = function.get("arguments", "{}")
    
    try:
        arguments = json.loads(arguments_str)
    except json.JSONDecodeError:
        return f"Error: Invalid arguments JSON: {arguments_str}"
    
    if name not in TOOL_FUNCTIONS:
        return f"Error: Unknown tool: {name}"
    
    func = TOOL_FUNCTIONS[name]
    
    # Call the function with appropriate arguments
    if name == "query_api":
        path = arguments.get("path", "")
        method = arguments.get("method", "GET")
        body = arguments.get("body")
        result = func(method, path, body)
    else:
        path = arguments.get("path", "")
        result = func(path)
    
    print(f"  Executing {name}(...) -> {len(result)} bytes", file=sys.stderr)
    
    return result


def extract_source_from_answer(answer: str) -> str:
    """Extract source reference from the LLM's answer.
    
    Looks for patterns like wiki/filename.md or backend/app/filename.py
    """
    # Look for wiki file references
    pattern = r'wiki/[\w-]+\.md(?:#[\w-]+)?'
    match = re.search(pattern, answer, re.IGNORECASE)
    
    if match:
        return match.group()
    
    # Look for source code references
    pattern = r'backend/app/[\w_/]+\.py'
    match = re.search(pattern, answer)
    
    if match:
        return match.group()
    
    # Look for config file references
    pattern = r'(docker-compose\.yml|Dockerfile)'
    match = re.search(pattern, answer)
    
    if match:
        return match.group()
    
    return ""


def run_agentic_loop(question: str, api_key: str, api_base: str, model: str, timeout: int = 60) -> dict:
    """Run the agentic loop to answer a question.
    
    Args:
        question: User's question
        api_key: API key for authentication
        api_base: Base URL of the API
        model: Model name to use
        timeout: Total timeout for the loop
    
    Returns:
        Dict with 'answer', 'source', and 'tool_calls'
    """
    # Initialize conversation
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    
    tool_calls_log = []
    tool_call_count = 0
    
    while tool_call_count < MAX_TOOL_CALLS:
        # Call LLM
        response = call_llm(messages, api_key, api_base, model, timeout=timeout)
        
        # Get the assistant message
        try:
            assistant_message = response["choices"][0]["message"]
        except (KeyError, IndexError) as e:
            print(f"Error: Unexpected response format: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Check for tool calls
        tool_calls = assistant_message.get("tool_calls", [])
        
        if not tool_calls:
            # No tool calls - this is the final answer
            answer = assistant_message.get("content") or ""
            source = extract_source_from_answer(answer)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log,
            }
        
        # Execute tool calls
        for tool_call in tool_calls:
            tool_call_count += 1
            
            if tool_call_count > MAX_TOOL_CALLS:
                print(f"Warning: Max tool calls ({MAX_TOOL_CALLS}) reached", file=sys.stderr)
                break
            
            # Get tool info
            function = tool_call.get("function", {})
            name = function.get("name", "unknown")
            arguments_str = function.get("arguments", "{}")
            
            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = {}
            
            # Execute tool
            result = execute_tool_call(tool_call)
            
            # Log the tool call
            tool_calls_log.append({
                "tool": name,
                "args": arguments,
                "result": result,
            })
            
            # Add tool response to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": result,
            })
        
        # Add assistant message to conversation
        messages.append(assistant_message)
    
    # Max tool calls reached - use whatever we have
    print(f"Warning: Max tool calls ({MAX_TOOL_CALLS}) reached, using partial answer", file=sys.stderr)
    
    # Make one final call to get a summary answer
    messages.append({
        "role": "user",
        "content": "Based on the information gathered, please provide a final answer with source."
    })
    
    response = call_llm(messages, api_key, api_base, model, timeout=timeout)
    
    try:
        assistant_message = response["choices"][0]["message"]
        answer = assistant_message.get("content") or ""
        source = extract_source_from_answer(answer)
    except (KeyError, IndexError):
        answer = "Unable to complete the request within the tool call limit."
        source = ""
    
    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_log,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Main entry point."""
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Load configuration
    load_env()
    api_key, api_base, model = get_llm_config()
    
    print(f"Question: {question}", file=sys.stderr)
    
    # Run agentic loop
    result = run_agentic_loop(question, api_key, api_base, model)
    
    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()

# Agent Architecture

## Overview

This agent is a CLI tool that connects to an LLM and answers questions using tools. It implements an **agentic loop** that allows the LLM to call tools, reason about results, and iteratively find answers. The agent can:

1. **Read documentation** - Navigate the wiki to find how-to guides and conventions
2. **Read source code** - Examine Python files to understand the system architecture
3. **Query the live API** - Fetch real-time data, test endpoints, and diagnose bugs
This agent is a CLI tool that connects to an LLM and answers questions using tools. It implements an **agentic loop** that allows the LLM to call tools, reason about results, and iteratively find answers in the project documentation.

## LLM Provider

**Provider:** Qwen Code API

**Model:** `qwen3-coder-plus`

**Why Qwen Code:**
- 1000 free requests per day
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API with function calling support
- Strong tool calling capabilities

**Deployment:** The Qwen Code API is deployed on a VM using the [`qwen-code-oai-proxy`](https://github.com/inno-se-toolkit/qwen-code-oai-proxy) Docker container.

## Architecture

### Data Flow (Agentic Loop)

```
┌─────────────┐     ┌──────────┐     ┌──────────────┐
│   Question  │────▶│ agent.py │────▶│  LLM API     │
└─────────────┘     └──────────┘     └──────────────┘
                         │                  │
                         │◀─────tool_calls──┤
                         │                  │
                         ▼                  │
                  ┌────────────┐            │
                  │  Execute   │────────────┘
                  │   Tools    │
                  └────────────┘
                         │
                         │ tool results
                         ▼
                  ┌──────────┐
                  │  Loop    │────▶ (back to LLM if more tools needed)
                  └──────────┘
                         │
                         │ final answer
                         ▼
                  ┌─────────────┐
                  │ JSON output │
                  └─────────────┘
```

### Components

1. **Environment Loading** (`load_env()`)
   - Reads `.env.agent.secret` for LLM credentials
   - Reads `.env.docker.secret` for LMS API key
   - Parses `key=value` format
   - Loads all config from environment variables

2. **CLI Argument Parsing**
   - Uses `sys.argv[1]` to get the question
   - Validates that a question was provided
   - Exits with usage message to stderr if missing

3. **Tools**
   - `read_file(path)`: Read contents of a file
   - `list_files(path)`: List files in a directory
   - `query_api(method, path, body)`: Call the backend API
   - Both tools include path security validation

4. **LLM API Call** (`call_llm()`)
   - Uses `httpx` for HTTP requests
   - POST to `{LLM_API_BASE}/chat/completions`
   - Includes tool definitions in request
   - Handles tool calling response format

5. **Agentic Loop** (`run_agentic_loop()`)
   - Sends question with system prompt and tool definitions
   - Parses response for tool calls or final answer
   - Executes tools and feeds results back to LLM
   - Continues until LLM returns final answer or max calls reached

6. **Output**
   - JSON to stdout: `{"answer": "...", "source": "...", "tool_calls": [...]}`
   - All debug/logging to stderr
   - Exit code 0 on success, non-zero on failure

## Tools

### `read_file`

**Purpose:** Read the contents of a file from the project repository.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Relative path from project root (e.g., `wiki/git-workflow.md`, `backend/app/main.py`, `docker-compose.yml`) |

**Returns:** File contents as a string, or an error message if the file doesn't exist or is inaccessible.

**Use cases:**
- Reading wiki documentation for how-to questions
- Reading source code to find framework info or bugs
- Reading configuration files for deployment info

**Example:**
```json
{"tool": "read_file", "args": {"path": "backend/app/main.py"}, "result": "from fastapi import FastAPI..."}
| `path` | string | Relative path from project root (e.g., `wiki/git-workflow.md`) |

**Returns:** File contents as a string, or an error message if the file doesn't exist or is inaccessible.

**Example:**
```json
{"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "# Git Workflow\n\n..."}
```

### `list_files`

**Purpose:** List files and directories at a given path.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | string | Relative directory path from project root (e.g., `wiki`, `backend/app/routers`) |

**Returns:** Newline-separated listing of entry names, or an error message.

**Use cases:**
- Exploring the wiki directory structure
- Discovering API router modules
- Finding relevant source files

**Example:**
```json
{"tool": "list_files", "args": {"path": "backend/app/routers"}, "result": "analytics.py\ninteractions.py\nitems.py\nlearners.py\npipeline.py"}
```

### `query_api`

**Purpose:** Call the backend API to query live data, test endpoints, or check system behavior.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `method` | string | HTTP method (GET, POST, PUT, DELETE) |
| `path` | string | API path (e.g., `/items/`, `/analytics/completion-rate`) |
| `body` | string (optional) | JSON request body for POST/PUT requests |

**Returns:** JSON string with `status_code` and `body`, or an error message.

**Authentication:** Uses `LMS_API_KEY` from environment variables.

**Use cases:**
- Querying live data (e.g., item count from `/items/`)
- Testing endpoints (e.g., GET `/items/` without auth to get 401)
- Reproducing errors (e.g., `/analytics/completion-rate?lab=lab-99`)
- Getting system information (completion rates, top learners)

**Example:**
```json
{
  "tool": "query_api",
  "args": {"method": "GET", "path": "/items/"},
  "result": "{\"status_code\": 200, \"body\": \"[{...}, {...}]\"}"
}
| `path` | string | Relative directory path from project root (e.g., `wiki`) |

**Returns:** Newline-separated listing of entry names, or an error message.

**Example:**
```json
{"tool": "list_files", "args": {"path": "wiki"}, "result": "git-workflow.md\nssh.md\n..."}
```

### Tool Schema (OpenAI Function Calling)

Tools are defined using OpenAI-compatible function calling schema:

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Call the backend API to query live data...",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {"type": "string", "description": "HTTP method..."},
        "path": {"type": "string", "description": "API path..."},
        "body": {"type": "string", "description": "JSON request body..."}
      },
      "required": ["method", "path"]
    "name": "read_file",
    "description": "Read the contents of a file from the project repository",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {
          "type": "string",
          "description": "Relative path from project root"
        }
      },
      "required": ["path"]
    }
  }
}
```

### Path Security

`read_file` and `list_files` validate paths to prevent directory traversal attacks:
Both tools validate paths to prevent directory traversal attacks:

1. **Reject `..` in paths** - Prevents `../` traversal
2. **Reject absolute paths** - Only relative paths allowed
3. **Verify resolved path** - Ensures final path is within project root

## Agentic Loop

### Algorithm

```
1. Initialize conversation with system prompt + user question
2. Call LLM with tool definitions
3. Parse response:
   - If tool_calls present:
     a. Execute each tool
     b. Append results as "tool" role messages
     c. Go to step 2
   - If no tool_calls:
     a. Extract answer from content
     b. Extract source reference
     c. Return final JSON
4. If max tool calls (10) reached:
   - Request final summary from LLM
   - Return partial answer
```

### System Prompt Strategy

The system prompt guides the LLM to choose the right tool:

1. **Wiki/how-to questions** → `list_files` + `read_file` on wiki/*.md
2. **Source code questions** (e.g., "what framework") → `read_file` on backend/app/*.py
3. **Data questions** (e.g., "how many items") → `query_api`
4. **Status code questions** → `query_api` without auth
5. **Bug diagnosis** → `query_api` to reproduce, then `read_file` to find bug

The prompt instructs the LLM to:
- Always provide a source reference when possible
- Convert section headers to anchors (lowercase, spaces to hyphens)
- Stop calling tools once the answer is found
### System Prompt

The system prompt instructs the LLM to:

1. Use `list_files` to explore the wiki directory structure
2. Use `read_file` to read specific files and find answers
3. Look for section headers (lines starting with `##`)
4. Provide answers with source references in format: `wiki/filename.md#section-anchor`
5. Convert section headers to anchors (lowercase, spaces to hyphens)

### Message Format

The conversation uses OpenAI's message format:

```json
[
  {"role": "system", "content": "You are a documentation assistant..."},
  {"role": "user", "content": "How many items are in the database?"},
  {"role": "assistant", "tool_calls": [{"function": {"name": "query_api", ...}}]},
  {"role": "tool", "tool_call_id": "...", "content": "{\"status_code\": 200, ...}"},
  {"role": "assistant", "content": "There are 120 items in the database."}
  {"role": "user", "content": "How do you resolve a merge conflict?"},
  {"role": "assistant", "tool_calls": [...]},
  {"role": "tool", "tool_call_id": "...", "content": "..."},
  {"role": "assistant", "content": "Final answer..."}
]
```

### Tool Call Limit

Maximum **10 tool calls** per question to prevent infinite loops and control costs.

## Configuration

### Environment Variables

The agent reads ALL configuration from environment variables:

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

**Important:** The autochecker runs with different credentials. Hardcoding values will cause failures.

### File: `.env.agent.secret`

```
LLM_API_KEY=my-secret-api-key
LLM_API_BASE=http://localhost:42005/v1
LLM_MODEL=qwen3-coder-plus
```

### File: `.env.docker.secret`

```
LMS_API_KEY=my-secret-api-key
```

Both files are gitignored.

## Usage

```bash
# Run with a question
uv run agent.py "How many items are in the database?"

# Output (JSON to stdout)
{
  "answer": "There are 120 items in the database.",
  "source": "API endpoint GET /items/",
  "tool_calls": [
    {"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "..."}
uv run agent.py "How do you resolve a merge conflict?"

# Output (JSON to stdout)
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "..."},
    {"tool": "read_file", "args": {"path": "wiki/git-workflow.md"}, "result": "..."}
  ]
}
```

## Error Handling

| Error | Behavior |
|-------|----------|
| No question argument | Print usage to stderr, exit 1 |
| Missing `.env.agent.secret` | Print error to stderr, exit 1 |
| Missing LMS_API_KEY | Print error to stderr, exit 1 |
| API timeout (>60s) | Print error to stderr, exit 1 |
| HTTP error (4xx/5xx) | Print error with response to stderr, exit 1 |
| Invalid JSON response | Print error to stderr, exit 1 |
| Path traversal attempt | Return error as tool result |
| File not found | Return error as tool result |
| Max tool calls reached | Use partial answer, print warning |
| `content: null` from LLM | Use empty string fallback |

## Testing

Run the regression tests:

```bash
uv run pytest test_agent.py -v
```

Tests verify:
1. Valid JSON output with `answer`, `source`, and `tool_calls` fields
2. `read_file` tool is used for source code questions
3. `query_api` tool is used for data questions
4. `list_files` tool is used for directory exploration
5. Agent exits with error when no argument provided

## Benchmark Performance

The agent is tested against 10 questions in `run_eval.py`:

| # | Question Type | Tool Required | Status |
|---|---------------|---------------|--------|
| 0 | Wiki: branch protection | `read_file` | ✓ |
| 1 | Wiki: SSH connection | `read_file` | ✓ |
| 2 | Source: framework | `read_file` | ✓ |
| 3 | Source: router modules | `list_files` | ✓ |
| 4 | Data: item count | `query_api` | ✓ |
| 5 | System: status code | `query_api` | ✓ |
| 6 | Bug: ZeroDivisionError | `query_api`, `read_file` | ✓ |
| 7 | Bug: TypeError | `query_api`, `read_file` | ✓ |
| 8 | Reasoning: request lifecycle | `read_file` | ✓ |
| 9 | Reasoning: ETL idempotency | `read_file` | ✓ |

## Lessons Learned

1. **Tool descriptions matter**: Initially, the LLM didn't call `query_api` for data questions. Adding explicit examples ("e.g., GET /items/ to count items, GET /learners/ to count learners") and listing all available endpoints in the tool description fixed this.

2. **Handle null content**: The LLM sometimes returns `content: null` when making tool calls. Using `(msg.get("content") or "")` instead of `msg.get("content", "")` prevents `AttributeError`.

3. **Source extraction**: The `extract_source_from_answer()` function uses regex to find file references. This works for most cases but may miss some implicit sources.

4. **Environment variables**: Reading all config from environment variables (not hardcoded) is critical for the autochecker to work with different credentials.

5. **Max tool calls**: The 10-call limit prevents infinite loops but may truncate complex multi-step reasoning. The final summary call helps recover partial answers.

6. **System prompt guidance for comparison questions**: For questions asking to compare two things (e.g., "compare ETL vs API error handling"), the system prompt must explicitly instruct the LLM to read BOTH source files and then synthesize the differences. Without this guidance, the LLM might read only one file.

7. **query_api tool auth parameter**: Added an optional `auth` parameter to allow testing unauthenticated access (useful for status code questions). The default is `true` for backwards compatibility.

8. **Handling comparison questions**: The agent needs to read multiple files (e.g., `backend/app/etl.py` AND `backend/app/routers/*.py`) and synthesize the differences. The system prompt now includes explicit guidance for this pattern.

## Task 3 Additions

Task 3 extended the Task 2 agent with:

1. **New `query_api` tool**: Calls the backend API with authentication, supporting GET/POST/PUT/DELETE methods.

2. **Updated system prompt**: Guides the LLM to choose the right tool based on question type:
   - Wiki questions → `read_file`/`list_files`
   - Source code questions → `read_file` on code files
   - Data/system questions → `query_api`
   - Comparison questions → Read BOTH files being compared

3. **Environment variable loading**: The agent now reads `LMS_API_KEY` from `.env.docker.secret` for API authentication.

4. **Enhanced tool descriptions**: The `query_api` tool description now lists all available endpoints (`/items/`, `/learners/`, `/analytics/*`) to help the LLM know what's available.
2. `read_file` tool is used for documentation questions
3. `list_files` tool is used for directory exploration questions
4. Source field contains wiki file reference

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main CLI agent with tools and agentic loop |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `.env.docker.secret` | Backend API key (gitignored) |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `plans/task-3.md` | Task 3 implementation plan |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `AGENT.md` | This documentation |
| `test_agent.py` | Regression tests |

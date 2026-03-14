# Task 3: The System Agent

## Overview

Extend the Task 2 agent with a `query_api` tool that can call the deployed backend API. This enables the agent to answer questions about the running system (framework, ports, status codes) and data-dependent queries (item count, scores).

## New Tool: `query_api`

**Purpose:** Call the deployed backend API and return the response.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `method` | string | HTTP method (GET, POST, PUT, DELETE, etc.) |
| `path` | string | API path (e.g., `/items/`, `/analytics/completion-rate`) |
| `body` | string (optional) | JSON request body for POST/PUT requests |

**Returns:** JSON string with `status_code` and `body`.

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret` (not the LLM key).

**Headers:**
- `Authorization: Bearer {LMS_API_KEY}`
- `Content-Type: application/json`

## Tool Schema (OpenAI Function Calling)

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Call the backend API to query system data or test endpoints",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method (GET, POST, PUT, DELETE)"
        },
        "path": {
          "type": "string",
          "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "JSON request body (optional, for POST/PUT)"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

## Environment Variables

The agent reads ALL configuration from environment variables (not hardcoded):

| Variable | Purpose | Source |
|----------|---------|--------|
| `LLM_API_KEY` | LLM provider API key | `.env.agent.secret` |
| `LLM_API_BASE` | LLM API endpoint URL | `.env.agent.secret` |
| `LLM_MODEL` | Model name | `.env.agent.secret` |
| `LMS_API_KEY` | Backend API key for query_api auth | `.env.docker.secret` |
| `AGENT_API_BASE_URL` | Base URL for query_api | Optional, defaults to `http://localhost:42002` |

**Important:** The autochecker runs with different credentials. Hardcoding values will cause failures.

## System Prompt Updates

The system prompt must guide the LLM to choose the right tool:

1. **Wiki questions** (how to do something, project conventions) → `read_file`, `list_files`
2. **System questions** (framework, ports, status codes, data) → `query_api`
3. **Source code questions** (what framework, how code works) → `read_file` on code files

Updated instructions:
- Use `read_file` to read source code (e.g., `backend/app/main.py` for framework info)
- Use `query_api` to query live data (e.g., `/items/` for item count)
- Use `query_api` to test endpoints (e.g., GET `/items/` without auth to get 401)
- For bug diagnosis: use `query_api` to reproduce error, then `read_file` to find the bug

## Agentic Loop

The loop remains the same as Task 2:
1. Send question + all tool schemas to LLM
2. If LLM returns tool calls → execute and feed back
3. If LLM returns final answer → extract and output JSON
4. Max 10 tool calls

## Output Format

```json
{
  "answer": "There are 120 items in the database.",
  "source": "",  // Optional for system questions
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": [...]}"
    }
  ]
}
```

## Benchmark Questions

The `run_eval.py` script tests 10 questions:

| # | Question | Tool | Expected Answer |
|---|----------|------|-----------------|
| 0 | Branch protection steps | `read_file` | wiki/git-workflow.md |
| 1 | SSH connection steps | `read_file` | wiki/ssh.md |
| 2 | Python web framework | `read_file` | FastAPI (from backend/app/main.py) |
| 3 | API router modules | `list_files` | items, interactions, analytics, pipeline |
| 4 | Items in database | `query_api` | Number > 0 |
| 5 | Status code without auth | `query_api` | 401 or 403 |
| 6 | Completion-rate error | `query_api`, `read_file` | ZeroDivisionError |
| 7 | Top-learners crash | `query_api`, `read_file` | TypeError/NoneType |
| 8 | Request lifecycle | `read_file` | Caddy → FastAPI → auth → router → ORM → PostgreSQL |
| 9 | ETL idempotency | `read_file` | external_id check, duplicates skipped |

## Iteration Strategy

1. **First run:** `uv run run_eval.py` to get baseline score
2. **For each failure:**
   - Read the feedback hint
   - Check which tool was (not) called
   - Adjust system prompt or tool descriptions
   - Re-run and verify
3. **Common fixes:**
   - Tool not called → improve description
   - Wrong arguments → clarify parameter descriptions
   - Answer doesn't match → adjust phrasing in system prompt

## Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `plans/task-3.md` | Create | This plan |
| `agent.py` | Update | Add query_api tool, update system prompt |
| `.env.docker.secret` | Create (from example) | LMS_API_KEY for query_api |
| `AGENT.md` | Update | Document query_api and lessons learned |
| `test_agent.py` | Update | Add 2 system agent tests |

## Acceptance Criteria Checklist

- [ ] Plan created before code
- [ ] `query_api` tool implemented with auth
- [ ] Agent reads all config from environment variables
- [ ] System prompt guides tool selection
- [ ] `run_eval.py` passes all 10 questions
- [ ] 2 new regression tests pass
- [ ] `AGENT.md` updated (200+ words)
- [ ] Autochecker bot benchmark passes

## Initial Benchmark Score

**To run the benchmark:**

1. Ensure the backend is running on your VM:
   ```bash
   docker compose ps
   ```

2. Ensure the Qwen Code API is running:
   ```bash
   curl http://localhost:42005/v1/models
   ```

3. Run the evaluation:
   ```bash
   uv run run_eval.py
   ```

4. If tests fail, iterate:
   - Check which tool was (not) called
   - Adjust system prompt or tool descriptions
   - Re-run until all pass

- Score: _/10 (run `uv run run_eval.py` to get your score)
- First failures: [fill in after first run]
- Iteration strategy: [fill in after first run]

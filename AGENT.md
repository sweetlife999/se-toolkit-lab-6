# Agent Architecture

## Overview

This agent is a CLI tool that connects to an LLM and answers questions. It forms the foundation for the agentic system that will be extended with tools and an agentic loop in Tasks 2-3.

## LLM Provider

**Provider:** Qwen Code API

**Model:** `qwen3-coder-plus`

**Why Qwen Code:**
- 1000 free requests per day
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API
- Strong tool calling capabilities

**Deployment:** The Qwen Code API is deployed on a VM using the [`qwen-code-oai-proxy`](https://github.com/inno-se-toolkit/qwen-code-oai-proxy) Docker container.

## Architecture

### Data Flow

```
┌─────────────────┐     ┌──────────┐     ┌──────────────┐     ┌─────────────┐
│ Command line    │────▶│ agent.py │────▶│ LLM API      │────▶│ JSON output │
│ argument        │     │          │     │ (Qwen Code)  │     │ to stdout   │
└─────────────────┘     └──────────┘     └──────────────┘     └─────────────┘
```

### Components

1. **Environment Loading** (`load_env()`)
   - Reads `.env.agent.secret` from the project root
   - Parses `key=value` format
   - Loads `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **CLI Argument Parsing**
   - Uses `sys.argv[1]` to get the question
   - Validates that a question was provided
   - Exits with usage message to stderr if missing

3. **LLM API Call** (`call_llm()`)
   - Uses `httpx` for HTTP requests
   - POST to `{LLM_API_BASE}/chat/completions`
   - Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
   - Body: `{"model": model, "messages": [{"role": "user", "content": question}]}`
   - Timeout: 60 seconds

4. **Response Parsing**
   - Extracts `choices[0].message.content` from the API response
   - Handles errors: timeout, HTTP errors, invalid JSON, missing fields

5. **Output**
   - JSON to stdout: `{"answer": "...", "tool_calls": []}`
   - All debug/logging to stderr
   - Exit code 0 on success, non-zero on failure

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for LLM provider | `my-secret-api-key` |
| `LLM_API_BASE` | Base URL of LLM API | `http://localhost:42005/v1` |
| `LLM_MODEL` | Model name to use | `qwen3-coder-plus` |

### File: `.env.agent.secret`

```
LLM_API_KEY=my-secret-api-key
LLM_API_BASE=http://localhost:42005/v1
LLM_MODEL=qwen3-coder-plus
```

This file is gitignored and must be created from `.env.agent.example`.

## Usage

```bash
# Run with a question
uv run agent.py "What does REST stand for?"

# Output (JSON to stdout)
{"answer": "Representational State Transfer.", "tool_calls": []}
```

## Error Handling

| Error | Behavior |
|-------|----------|
| No question argument | Print usage to stderr, exit 1 |
| Missing `.env.agent.secret` | Print error to stderr, exit 1 |
| Missing environment variables | Print error to stderr, exit 1 |
| API timeout (>60s) | Print error to stderr, exit 1 |
| HTTP error (4xx/5xx) | Print error with response to stderr, exit 1 |
| Invalid JSON response | Print error to stderr, exit 1 |
| Missing answer in response | Print error to stderr, exit 1 |

## Testing

Run the regression test:

```bash
uv run pytest backend/tests/unit/test_agent_task1.py -v
```

The test:
1. Runs `agent.py` as a subprocess with a simple question
2. Parses the JSON output from stdout
3. Asserts `answer` field exists and is non-empty
4. Asserts `tool_calls` field exists and is an empty list

## Future Extensions (Tasks 2-3)

- **Task 2:** Add tools (e.g., `read_file`, `list_files`, `query_api`)
- **Task 3:** Implement agentic loop with tool calling and multi-step reasoning

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main CLI agent |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `plans/task-1.md` | Implementation plan |
| `AGENT.md` | This documentation |
| `backend/tests/unit/test_agent_task1.py` | Regression test |

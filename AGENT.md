# Agent Architecture

## Overview

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
   - Reads `.env.agent.secret` from the project root
   - Parses `key=value` format
   - Loads `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **CLI Argument Parsing**
   - Uses `sys.argv[1]` to get the question
   - Validates that a question was provided
   - Exits with usage message to stderr if missing

3. **Tools**
   - `read_file(path)`: Read contents of a file
   - `list_files(path)`: List files in a directory
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
| Missing environment variables | Print error to stderr, exit 1 |
| API timeout (>60s) | Print error to stderr, exit 1 |
| HTTP error (4xx/5xx) | Print error with response to stderr, exit 1 |
| Invalid JSON response | Print error to stderr, exit 1 |
| Path traversal attempt | Return error as tool result |
| File not found | Return error as tool result |
| Max tool calls reached | Use partial answer, print warning |

## Testing

Run the regression tests:

```bash
uv run pytest test_agent.py -v
```

Tests verify:
1. Valid JSON output with `answer`, `source`, and `tool_calls` fields
2. `read_file` tool is used for documentation questions
3. `list_files` tool is used for directory exploration questions
4. Source field contains wiki file reference

## Files

| File | Purpose |
|------|---------|
| `agent.py` | Main CLI agent with tools and agentic loop |
| `.env.agent.secret` | LLM credentials (gitignored) |
| `plans/task-1.md` | Task 1 implementation plan |
| `plans/task-2.md` | Task 2 implementation plan |
| `AGENT.md` | This documentation |
| `test_agent.py` | Regression tests |

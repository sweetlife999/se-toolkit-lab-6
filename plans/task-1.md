# Task 1: Call an LLM from Code

## LLM Provider and Model

**Provider:** Qwen Code API (deployed on VM)

**Model:** `qwen3-coder-plus`

**Why this choice:**
- 1000 free requests per day (sufficient for development and testing)
- Works from Russia without restrictions
- No credit card required
- Already set up on the VM at `http://localhost:42005/v1`
- Strong tool calling capabilities (needed for Tasks 2-3)

## Architecture

### Data Flow

```
Command line argument → agent.py → HTTP POST to LLM API → Parse response → JSON to stdout
```

### Components

1. **Environment Loading**
   - Read `.env.agent.secret` for `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Use `dotenv` or manual parsing

2. **CLI Argument Parsing**
   - Use `sys.argv[1]` to get the question
   - Validate that a question was provided
   - Exit with error message to stderr if missing

3. **LLM API Call**
   - Use `httpx` (already in dependencies) for async HTTP
   - POST to `{LLM_API_BASE}/chat/completions`
   - Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
   - Body: `{"model": LLM_MODEL, "messages": [{"role": "user", "content": question}]}`
   - Timeout: 60 seconds

4. **Response Parsing**
   - Extract `choices[0].message.content` from API response
   - Build output: `{"answer": <content>, "tool_calls": []}`

5. **Output**
   - JSON to stdout (single line)
   - All debug/logging to stderr
   - Exit code 0 on success

## Error Handling

| Error | Handling |
|-------|----------|
| No question argument | Print usage to stderr, exit 1 |
| API timeout | Print error to stderr, exit 1 |
| API error (4xx/5xx) | Print error to stderr, exit 1 |
| Invalid JSON response | Print error to stderr, exit 1 |
| Missing answer in response | Print error to stderr, exit 1 |

## Testing Strategy

**Test file:** `backend/tests/unit/test_agent_task1.py`

**Test case:**
1. Run `agent.py` with a simple question (e.g., "What is 2+2?")
2. Capture stdout
3. Parse JSON output
4. Assert `answer` field exists and is non-empty string
5. Assert `tool_calls` field exists and is empty list

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `plans/task-1.md` | Create | This plan |
| `.env.agent.secret` | Create | LLM credentials (from `.env.agent.example`) |
| `agent.py` | Create | Main CLI agent |
| `AGENT.md` | Create/Update | Documentation of agent architecture |
| `backend/tests/unit/test_agent_task1.py` | Create | Regression test |

## Acceptance Criteria Checklist

- [ ] Plan created before code
- [ ] `agent.py` outputs valid JSON with `answer` and `tool_calls`
- [ ] API key in `.env.agent.secret` (not hardcoded)
- [ ] Debug output goes to stderr
- [ ] 60 second timeout
- [ ] Exit code 0 on success
- [ ] 1 regression test passes
- [ ] `AGENT.md` documents the solution

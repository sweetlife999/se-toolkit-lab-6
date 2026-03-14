# Task 2: The Documentation Agent

## Overview

Extend the Task 1 agent with tools (`read_file`, `list_files`) and an agentic loop. The agent will now be able to navigate the wiki and find answers with source references.

## Tool Definitions

### `read_file`

**Purpose:** Read contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as a string, or error message if file doesn't exist.

**Security:** Reject paths containing `../` to prevent directory traversal.

### `list_files`

**Purpose:** List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries.

**Security:** Reject paths containing `../` to prevent directory traversal.

## Tool Schema (OpenAI Function Calling)

The tools will be defined using OpenAI-compatible function calling schema:

```json
{
  "name": "read_file",
  "description": "Read contents of a file from the project",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Relative path from project root"}
    },
    "required": ["path"]
  }
}
```

Similar schema for `list_files`.

## Agentic Loop

```
Question → LLM (with tool schemas) → Check response
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
              tool_calls?            final answer?       max calls (10)?
                  │                      │                    │
                 yes                    no                   yes
                  │                      │                    │
                  ▼                      ▼                    ▼
          Execute tools          Extract answer        Use current answer
          Append results         + source              + collected info
          Loop back              Output JSON           Output JSON
```

### Loop Steps

1. **Initialize:**
   - System prompt with instructions to use tools and cite sources
   - User question as first message
   - Empty `tool_calls` list
   - Counter for tool calls (max 10)

2. **Call LLM:**
   - Send all messages (conversation history)
   - Include tool definitions in request
   - Parse response for `tool_calls` or content

3. **If LLM returns tool calls:**
   - Increment counter
   - If counter > 10, stop and use current answer
   - Execute each tool call
   - Append tool results to conversation as `tool` role messages
   - Go to step 2

4. **If LLM returns content (no tool calls):**
   - Extract answer from content
   - Extract source (file path + optional anchor) from response
   - Build output JSON
   - Exit

## System Prompt Strategy

The system prompt will instruct the LLM to:

1. Use `list_files` to discover relevant wiki files
2. Use `read_file` to read specific files and find answers
3. Always include a `source` field with the file path that contains the answer
4. Use section anchors when possible (e.g., `wiki/git-workflow.md#resolving-merge-conflicts`)
5. Stop calling tools once the answer is found

Example system prompt:
```
You are a documentation assistant. You have access to a project wiki.

Available tools:
- list_files: List files in a directory
- read_file: Read contents of a file

When answering questions:
1. First use list_files to explore the wiki directory
2. Then use read_file to read relevant files
3. Find the exact section that answers the question
4. Provide the answer with a source reference (file path + section anchor)

Always cite your source. Format: wiki/filename.md#section-anchor
```

## Output Format

```json
{
  "answer": "Explanation of how to resolve merge conflicts...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n## Resolving Merge Conflicts..."
    }
  ]
}
```

## Security Considerations

- Validate all paths: reject `../`, absolute paths, paths starting with `/`
- Only allow paths within project root
- Use `Path.resolve()` to verify final path is within project directory

## Error Handling

| Error | Handling |
|-------|----------|
| File not found | Return error message as tool result |
| Path traversal attempt | Return security error |
| LLM returns invalid tool name | Skip and continue |
| Max tool calls reached | Use partial answer, note truncation |
| API timeout | Exit with error to stderr |

## Testing Strategy

**Test 1: read_file tool**
- Question: "How do you resolve a merge conflict?"
- Expected: `read_file` in tool_calls, `wiki/git-workflow.md` in source

**Test 2: list_files tool**
- Question: "What files are in the wiki?"
- Expected: `list_files` in tool_calls

## Files to Modify

| File | Action | Purpose |
|------|--------|---------|
| `plans/task-2.md` | Create | This plan |
| `agent.py` | Update | Add tools, agentic loop, source extraction |
| `AGENT.md` | Update | Document tools and loop |
| `test_agent.py` | Update | Add 2 new regression tests |

## Acceptance Criteria Checklist

- [ ] Plan created before code
- [ ] `read_file` and `list_files` tools implemented
- [ ] Tool schemas registered with LLM
- [ ] Agentic loop executes and feeds results back
- [ ] `tool_calls` populated in output
- [ ] `source` field correctly identifies wiki section
- [ ] Path security prevents traversal attacks
- [ ] Max 10 tool calls enforced
- [ ] 2 regression tests pass
- [ ] `AGENT.md` updated with tools documentation

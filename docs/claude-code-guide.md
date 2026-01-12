# Using ctxd with Claude Code

Complete guide for integrating ctxd with Claude Code, both with and without MCP.

## Overview

There are two ways to use ctxd with Claude Code:

1. **MCP Integration**: integration via Model Context Protocol
2. **Direct CLI Usage**: Claude calls ctxd commands directly via Bash tool

## Method 1: MCP Integration (Recommended)

### Setup Steps

#### 1. Index Your Project

```bash
cd /path/to/your/project
ctxd init
ctxd index
```

#### 2. Configure Claude Code MCP Settings

Edit `~/.config/claude-code/settings.json`:

```json
{
  "mcpServers": {
    "ctxd": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/absolute/path/to/your/project"]
    }
  }
}
```

**Important**: Replace `/absolute/path/to/your/project` with your actual project path.

**Example**:

```json
{
  "mcpServers": {
    "ctxd": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/Users/alice/projects/my-app"]
    }
  }
}
```

#### 3. Restart Claude Code

Exit and restart Claude Code completely.

#### 4. Verify Integration

Ask Claude:

```
Search for "database connection" in the codebase
```

Claude should automatically use the `ctx_search` tool.

### Using MCP Integration

Once configured, simply ask Claude questions about your code:

**Example Conversations**:

```
You: Find all authentication logic

Claude: [Uses ctx_search tool]
I found authentication logic in the following files:

1. src/auth/login.py:15-32 (score: 0.89)
   - authenticate_user() function
   - Handles password verification and session creation

2. src/middleware/auth.py:8-25 (score: 0.84)
   - AuthMiddleware class
   - Validates JWT tokens on incoming requests
...
```

```
You: How is the database connection established?

Claude: [Uses ctx_search with query "database connection"]
Based on the code, the database connection is established in...
```

```
You: Show me the index status

Claude: [Uses ctx_status tool]
The codebase index contains:
- 234 files indexed
- 1,842 code chunks
- Languages: Python (156 files), JavaScript (42 files)...
```

### Available Tools via MCP

1. **ctx_search** - Semantic code search
   - Query with natural language
   - Filter by language, directory, file extension
   - Returns ranked code snippets

2. **ctx_status** - Index information
   - Total files/chunks
   - Languages detected
   - Last indexed timestamp

3. **ctx_index** - Trigger re-indexing
   - Update index after code changes
   - Force full re-index if needed

### MCP Best Practices

1. **Keep index updated**: Run `ctxd watch &` during development
2. **Use semantic queries**: Ask "how is X done" not "find function X"
3. **Let Claude decide**: No need to explicitly say "use ctx_search"
4. **Check status occasionally**: Ask "show index status" to verify freshness

### Multiple Projects with MCP

Configure multiple projects:

```json
{
  "mcpServers": {
    "ctxd-backend": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/home/user/backend"]
    },
    "ctxd-frontend": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/home/user/frontend"]
    }
  }
}
```

Claude will have separate tools for each project.

## Method 2: Direct CLI Usage (Without MCP)

### Why Use Direct CLI?

- **No configuration needed**: Works immediately after ctxd installation
- **Simple**: Just call commands via Bash
- **Flexible**: Full control over search parameters
- **Portable**: Works in any shell, not just Claude Code

### Setup Steps

#### 1. Install and Index

```bash
cd /path/to/your/project
ctxd init
ctxd index
```

That's it! No MCP configuration needed.

### Using Direct CLI with Claude Code

Ask Claude to run ctxd commands for you using the Bash tool.

**Example Conversations**:

```
You: Search for "database connection" using ctxd

Claude: [Runs: ctxd search "database connection"]
I found these results:

Match 1 (Score: 0.87) - src/db/connection.py:12-28
[Shows code snippet]
...
```

```
You: Use ctxd to find error handling in Python files only

Claude: [Runs: ctxd search "error handling" --extension .py]
Here are the error handling implementations I found:
...
```

```
You: Check the ctxd index status

Claude: [Runs: ctxd status]
The index contains:
- 234 files indexed
- 1,842 chunks
...
```

### Available Commands for Direct CLI

#### Search Commands

**Basic search**:

```bash
ctxd search "your query here"
```

**With filters**:

```bash
# Filter by file extension
ctxd search "authentication" --extension .py

# Filter by directory
ctxd search "API endpoints" --directory src/api/

# Limit results
ctxd search "error handling" --limit 5

# Multiple filters
ctxd search "user validation" --extension .py --directory src/ --limit 3

# Search mode
ctxd search "exact_function_name" --mode fts
ctxd search "concept or description" --mode vector
ctxd search "anything" --mode hybrid

# Expand context
ctxd search "payment processing" --expand-context
```

#### Index Management

```bash
# Check index status
ctxd status

# Re-index after changes
ctxd index

# Force full re-index
ctxd index --force

# Index specific directory
ctxd index src/

# Watch for changes (auto-reindex)
ctxd watch
```

### Direct CLI Workflow Examples

#### Workflow 1: Understanding New Codebase

```
You: I'm new to this codebase. Use ctxd to help me understand the authentication flow.

Claude:
1. [Runs: ctxd search "authentication flow"]
2. Analyzes results
3. Explains the authentication architecture based on found code
```

#### Workflow 2: Finding Examples

```
You: Use ctxd to find examples of database queries

Claude: [Runs: ctxd search "database query" --limit 10]
I found 10 examples of database queries. Here are the main patterns:
...
```

#### Workflow 3: Locating Specific Functionality

```
You: Find all the API endpoints using ctxd, then list them

Claude:
1. [Runs: ctxd search "API endpoint" --chunk-type function]
2. Lists and categorizes found endpoints
```

#### Workflow 4: Code Review Preparation

```
You: Use ctxd to find all error handling code so I can review it

Claude:
1. [Runs: ctxd search "error handling" --mode hybrid --limit 20]
2. Organizes results by file/module
3. Highlights patterns and potential issues
```

### Direct CLI Best Practices

1. **Be specific in requests**: Tell Claude exactly what to search for
2. **Use filters**: Narrow results with --extension, --directory, etc.
3. **Keep index updated**: Remind Claude to run `ctxd index` periodically
4. **Combine with other tools**: Use ctxd search, then read specific files
5. **Adjust search mode**: Use --mode fts for exact matches, --mode vector for concepts

### Asking Claude to Use ctxd

**Good prompts**:

- "Use ctxd to search for [query]"
- "Run ctxd search to find [concept]"
- "Check the ctxd index status"
- "Re-index the codebase with ctxd"

**Claude will understand**:

- "Search the indexed code for [query]" (implies ctxd)
- "Find [concept] in the codebase using semantic search" (implies ctxd)

## Comparison: MCP vs Direct CLI

| Feature             | MCP Integration               | Direct CLI                      |
| ------------------- | ----------------------------- | ------------------------------- |
| **Setup**           | Requires settings.json config | None needed                     |
| **Usage**           | Automatic, seamless           | Manual commands via Bash        |
| **User Experience** | Claude decides when to search | User explicitly requests search |
| **Flexibility**     | Limited to tool parameters    | Full CLI options available      |
| **Results Format**  | Structured JSON               | Human-readable text             |
| **Multi-project**   | Separate tools per project    | Change directory or re-index    |
| **Best For**        | Regular use, primary workflow | Ad-hoc searches, exploration    |

## Hybrid Approach

You can use both methods:

1. **MCP for primary project**: Configure MCP for your main codebase
2. **CLI for others**: Use direct CLI for other projects or quick searches

Example:

```json
{
  "mcpServers": {
    "ctxd-main": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "/home/user/main-project"]
    }
  }
}
```

For other projects, just ask Claude: "Use ctxd to search /path/to/other/project"

## Keeping Index Current

Regardless of method, keep your index updated:

### Option 1: Auto-update with Watch

```bash
# Start in project directory
cd /path/to/project
ctxd watch &

# Runs in background, auto-updates on file changes
```

### Option 2: Manual Re-indexing

```bash
# After making code changes
ctxd index

# Or ask Claude (both methods):
# MCP: "Re-index the codebase"
# CLI: "Run ctxd index to update the index"
```

### Option 3: Pre-commit Hook

Add to `.git/hooks/post-commit`:

```bash
#!/bin/bash
cd /path/to/project
ctxd index --quiet &
```

Make executable:

```bash
chmod +x .git/hooks/post-commit
```

## Troubleshooting

### MCP Issues

**Claude doesn't see ctxd tools:**

```bash
# Verify ctxd-mcp is available
which ctxd-mcp

# Check settings.json syntax
cat ~/.config/claude-code/settings.json | jq .

# Restart Claude Code completely
```

**Tools exist but searches fail:**

```bash
# Check index exists
cd /path/to/project
ctxd status

# Re-index if needed
ctxd index
```

### Direct CLI Issues

**"ctxd: command not found":**

```bash
# Verify installation
pip show ctxd

# Activate virtual environment if needed
source .venv/bin/activate

# Or install globally
pip install -e /path/to/ctxd
```

**No results from search:**

```bash
# Check index status
ctxd status

# Verify you're in the right directory
pwd
ls -la .ctxd/

# Re-index
ctxd index
```

### General Issues

**Slow search performance:**

```toml
# Edit .ctxd/config.toml
[search]
enable_cache = true
cache_size = 200
mode = "hybrid"  # Usually fastest
```

**Memory issues during indexing:**

```toml
# Edit .ctxd/config.toml
[embeddings]
batch_size = 16  # Reduce from 32

[indexer]
parallel = true
max_workers = 2  # Reduce worker count
```

## Configuration Tips

Customize `.ctxd/config.toml` for better results:

### For Better Search Results

```toml
[search]
mode = "hybrid"              # Best of both worlds
default_limit = 20           # More results
expand_context = true        # Show surrounding code
context_lines_before = 5
context_lines_after = 5
deduplicate = true           # Remove overlaps
```

### For Faster Indexing

```toml
[indexer]
parallel = true
max_workers = 8              # Use all CPU cores
exclude_patterns = [
    "node_modules/**",
    "vendor/**",
    "dist/**",
    "*.min.js",
    "docs/**"                # Exclude docs if not needed
]

[embeddings]
batch_size = 64              # Larger batches
```

### For Privacy-Sensitive Projects

```toml
[indexer]
exclude_patterns = [
    "**/*.env",
    "**/secrets/**",
    "**/*credentials*",
    "**/*.key",
    "**/*.pem"
]
```

## Example Use Cases

### Use Case 1: Onboarding to New Codebase

**Setup**:

```bash
git clone https://github.com/company/project
cd project
ctxd init
ctxd index
```

**With MCP**:

```
You: How does this application handle user authentication?

Claude: [Uses ctx_search automatically]
The application uses JWT-based authentication. Here's how it works:
[Explains based on found code]
```

**With CLI**:

```
You: Use ctxd to search for authentication code, then explain the flow

Claude:
[Runs: ctxd search "authentication" --limit 10]
Based on the search results, I found...
```

### Use Case 2: Bug Investigation

**With MCP**:

```
You: There's a bug in payment processing. Search the codebase for payment logic.

Claude: [Uses ctx_search with "payment processing"]
I found the payment processing code. Let me analyze it for potential issues...
```

**With CLI**:

```
You: Search for "payment processing" with ctxd

Claude: [Runs: ctxd search "payment processing" --expand-context]
Found these payment-related functions. Let me examine them...
```

### Use Case 3: API Documentation

**With MCP**:

```
You: Generate documentation for all API endpoints

Claude:
[Uses ctx_search with "API endpoint" filter]
[Reads found endpoints]
[Generates comprehensive API docs]
```

**With CLI**:

```
You: Use ctxd to find all API endpoints, then create documentation

Claude:
[Runs: ctxd search "API endpoint" --chunk-type function]
[Processes results]
Here's the documentation...
```

### Use Case 4: Code Refactoring

**With MCP**:

```
You: I want to refactor the database connection logic. Show me all related code.

Claude:
[Searches for "database connection"]
[Searches for related terms]
Here's all the database connection code in your project...
```

**With CLI**:

```
You: Find all database connection code using ctxd

Claude:
[Runs: ctxd search "database connection" --limit 20]
Found 20 instances of database connection logic...
```

## Advanced Tips

### 1. Combine ctxd with File Reading

**MCP**:

```
You: Search for authentication code, then read the main auth file

Claude:
[Uses ctx_search]
[Uses Read tool on identified files]
[Provides comprehensive analysis]
```

**CLI**:

```
You: Use ctxd to find auth code, then read the top result file

Claude:
[Runs: ctxd search "authentication"]
[Runs: cat src/auth/login.py]
[Analyzes the code]
```

### 2. Iterative Search Refinement

**MCP**:

```
You: Find error handling code
Claude: [Searches, shows results]

You: Now only show error handling in the API layer
Claude: [Refines search with directory filter]
```

**CLI**:

```
You: Search for error handling with ctxd
Claude: [ctxd search "error handling"]

You: Now search only in the api/ directory
Claude: [ctxd search "error handling" --directory api/]
```

### 3. Cross-Reference Different Concepts

```
You: Find how authentication and database access interact

Claude:
[Searches for "authentication"]
[Searches for "database access"]
[Analyzes relationships between results]
```

## Best Practices Summary

### General

1. ✅ Keep index updated (use `ctxd watch` or periodic re-indexing)
2. ✅ Use semantic queries ("how to X" not "find_x_function")
3. ✅ Exclude irrelevant files in config (node_modules, vendor, etc.)
4. ✅ Configure expand_context for more code context
5. ✅ Use hybrid search mode for best results

### MCP-Specific

1. ✅ Configure for your primary project
2. ✅ Let Claude decide when to search (don't over-specify)
3. ✅ Use meaningful project names in settings.json
4. ✅ Restart Claude Code after config changes

### CLI-Specific

1. ✅ Be explicit when asking Claude to use ctxd
2. ✅ Use filters to narrow results
3. ✅ Combine with other tools (Grep, Read, etc.)
4. ✅ Ask Claude to summarize/analyze results

## Next Steps

- [Configuration Guide](configuration.md) - Customize ctxd behavior
- [MCP Integration Guide](mcp-integration.md) - Detailed MCP setup
- [Usage Guide](usage.md) - Complete CLI reference
- [Architecture Guide](architecture.md) - How ctxd works

## Quick Reference

### MCP Setup

```bash
# 1. Index project
cd /path/to/project && ctxd init && ctxd index

# 2. Edit ~/.config/claude-code/settings.json
# Add ctxd MCP server config

# 3. Restart Claude Code
```

### CLI Usage

```bash
# Search
ctxd search "query" [--options]

# Status
ctxd status

# Re-index
ctxd index

# Watch
ctxd watch &
```

### Common Filters

```bash
--extension .py          # Python files only
--directory src/         # src/ directory only
--limit 20              # Max 20 results
--mode hybrid           # Hybrid search
--expand-context        # Show surrounding code
```

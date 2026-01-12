# ctxd Semantic Code Search Skill

**Skill Name:** ctxd-search
**Purpose:** Use ctxd semantic code search to efficiently explore and understand codebases
**When Available:** When MCP tools prefixed with `mcp__ctxd_` are available

---

## When to Use This Skill

**USE ctxd when:**
- User asks "where is X?" or "find X" in the codebase
- You need to understand unfamiliar code or architecture
- Searching for implementation patterns or examples
- Locating functionality without knowing exact file locations
- User asks about "how X works" and you need to find relevant code
- Exploring large codebases to reduce context usage
- Finding semantically similar code (e.g., "error handling patterns")

**DO NOT use ctxd when:**
- You already know the exact file to read (use Read tool directly)
- Searching for exact strings in known files (use Grep instead)
- Listing files by pattern (use Glob instead)
- The project hasn't been indexed yet (check status first)
- You need to search file names, not contents (use Glob)

---

## Available Tools

When ctxd MCP is configured, you have three tools:

### 1. `mcp__ctxd_ctx_search`

Semantic search across the indexed codebase.

**Key Parameters:**
- `query` (required): Natural language or keyword query
- `limit`: Number of results (default: 10, increase for broader exploration)
- `extensions`: Filter by file types (e.g., `[".py", ".js"]`)
- `directories`: Filter by paths (e.g., `["src/", "lib/"]`)
- `chunk_types`: Filter by code structure (`["function", "class", "method"]`)
- `languages`: Filter by language (`["python", "javascript"]`)
- `mode`: "hybrid" (default, recommended), "vector" (semantic only), "fts" (keyword only)
- `expand_context`: Include surrounding lines (useful for understanding context)
- `deduplicate`: Remove overlapping chunks (default: true)

### 2. `mcp__ctxd_ctx_status`

Get index statistics. **Always check this first** if you're unsure whether the project is indexed.

**Returns:**
- Total files and chunks indexed
- Languages in codebase
- Last indexed timestamp
- Index location

### 3. `mcp__ctxd_ctx_index`

Trigger re-indexing.

**Parameters:**
- `path`: Specific path to index (optional)
- `force`: Force re-index all files (optional)

**Use when:**
- User mentions code is outdated
- Status shows index is stale
- User explicitly requests re-indexing

---

## Search Strategy

### Formulating Effective Queries

**Good Queries (concept-based):**
- "database connection pooling"
- "JWT token validation"
- "error logging middleware"
- "user authentication flow"
- "API rate limiting"
- "payment processing logic"

**Poor Queries (too vague/generic):**
- "code" (too broad)
- "function" (too generic)
- "error" (too common)
- "x" or "a" (meaningless)

### Search Modes

**Hybrid Mode (default, recommended):**
- Combines semantic similarity + keyword matching
- Best for most queries
- Use for general exploration

**Vector Mode:**
- Pure semantic search
- Use when searching by concept/meaning
- Example: "authentication workflow" when code might use terms like "login", "auth", "verify"

**FTS Mode:**
- Keyword-based search (BM25)
- Use for exact identifier searches
- Example: "AuthMiddleware" or "connect_db"

### Progressive Refinement

Start broad, then narrow:

```
1. Initial search: ctx_search("authentication")
2. Too many results? → ctx_search("authentication", extensions=[".py"])
3. Still broad? → ctx_search("authentication", extensions=[".py"], chunk_types=["function"])
4. Need specific area? → ctx_search("authentication", directories=["src/api/"], extensions=[".py"])
```

---

## Workflow Patterns

### Pattern 1: Understanding New Codebase

When user asks "How does X work?" or "Explain the architecture":

```
1. Check index status:
   mcp__ctxd_ctx_status()

2. Search for main concepts:
   ctx_search("main entry point", limit=5)
   ctx_search("configuration", limit=5)
   ctx_search("database setup", limit=5)

3. Search for specific user-mentioned features:
   ctx_search("[user's feature]", limit=10)

4. Read top result files with Read tool for detailed analysis

5. Synthesize findings into coherent explanation
```

### Pattern 2: Finding Specific Functionality

When user asks "Where is X implemented?":

```
1. Semantic search for the functionality:
   ctx_search("[functionality]", limit=5)

2. If results unclear, refine with filters:
   ctx_search("[functionality]",
              extensions=[".py"],  # if language known
              chunk_types=["function", "class"])

3. If multiple languages, search separately:
   ctx_search("[functionality]", languages=["python"])
   ctx_search("[functionality]", languages=["javascript"])

4. Read the most relevant files

5. Report findings with file:line references
```

### Pattern 3: Finding Code Patterns

When user asks "Show me all X" or "Find examples of Y":

```
1. Broad search with higher limit:
   ctx_search("[pattern]", limit=20)

2. Optionally expand context to see usage:
   ctx_search("[pattern]", expand_context=true, limit=15)

3. Group and categorize results

4. Read representative examples

5. Summarize common patterns
```

### Pattern 4: Debugging/Investigation

When user reports a bug or wants to investigate an issue:

```
1. Search for relevant code areas:
   ctx_search("[feature with bug]", limit=10)

2. Search for error handling in that area:
   ctx_search("error handling [feature]", limit=10)

3. Search for related tests:
   ctx_search("[feature] test", directories=["tests/"])

4. Read identified files

5. Analyze for potential issues
```

### Pattern 5: Cross-Reference Analysis

When analyzing relationships between components:

```
1. Search for first component:
   ctx_search("[component A]", limit=10)

2. Search for second component:
   ctx_search("[component B]", limit=10)

3. Search for integration/interaction:
   ctx_search("[component A] [component B]")

4. Read relevant files

5. Explain relationships
```

---

## Best Practices

### 1. Always Check Index Status First

Before searching, especially in new conversations:

```
Use ctx_status to verify:
- Index exists
- Index is recent
- Expected files are indexed

If no index or stale, inform user and suggest:
- Running `ctxd index` manually
- Or use ctx_index if appropriate
```

### 2. Set Appropriate Result Limits

- **Initial exploration:** limit=5-10
- **Comprehensive search:** limit=15-20
- **Finding all instances:** limit=30-50
- **Default:** 10 is usually sufficient

### 3. Use Filters Strategically

**When you know the language:**
```
extensions=[".py"]  # Faster, more relevant
```

**When you know the area:**
```
directories=["src/api/", "src/controllers/"]
```

**When looking for specific structures:**
```
chunk_types=["function"]  # Only functions
chunk_types=["class"]     # Only classes
```

### 4. Combine with Other Tools

ctxd is for **discovery**, not **detailed analysis**:

```
1. ctx_search → Find relevant files
2. Read → Get full file contents
3. Grep → Find exact string occurrences
4. Edit → Make changes
```

**Example workflow:**
```
ctx_search("authentication")
  → Identifies: src/auth/login.py:15-32
Read src/auth/login.py
  → Analyze full implementation
Grep "authenticate_user"
  → Find all call sites
```

### 5. Use expand_context Selectively

**Use expand_context=true when:**
- Need to understand surrounding code
- Want to see how function is called
- Understanding context is critical

**Use expand_context=false (default) when:**
- Just finding locations
- Reducing token usage
- Results are sufficient

### 6. Handle Multiple Languages

For multi-language projects:

```
1. Check status to see language distribution
2. Search by language if needed:
   ctx_search("auth", languages=["python"])
   ctx_search("auth", languages=["javascript"])
3. Compare implementations across languages
```

### 7. Iterate on Poor Results

If search returns irrelevant results:

```
1. Try different query phrasing:
   "user login" → "authentication flow"

2. Switch search modes:
   mode="hybrid" → mode="vector"

3. Add filters:
   Add extensions, directories, or chunk_types

4. Try related terms:
   "database" → "SQL queries" → "data persistence"
```

---

## Common Scenarios

### Scenario: User asks "Where is the database schema?"

```
1. ctx_search("database schema", limit=10)
2. If too broad: ctx_search("database schema", extensions=[".py", ".sql"])
3. If still unclear: ctx_search("database schema", chunk_types=["class"])
4. Read top results
5. Report: "Database schema is defined in [file:line]"
```

### Scenario: User asks "How does authentication work?"

```
1. ctx_status  # Verify index
2. ctx_search("authentication flow", limit=15, expand_context=true)
3. ctx_search("login", limit=10)
4. ctx_search("session management", limit=10)
5. Read key files identified
6. Explain the authentication architecture with code references
```

### Scenario: User asks "Find all API endpoints"

```
1. ctx_search("API endpoint", limit=30, chunk_types=["function"])
2. Alternatively: ctx_search("route handler", limit=30)
3. Read representative files
4. List and categorize endpoints:
   - GET /api/users → src/api/users.py:45
   - POST /api/auth → src/api/auth.py:23
   [etc.]
```

### Scenario: User asks "Show me error handling patterns"

```
1. ctx_search("error handling", limit=20, mode="hybrid")
2. ctx_search("exception handling", limit=15)
3. ctx_search("try except", limit=10, extensions=[".py"])
4. Analyze results and group by pattern:
   - Try/except blocks
   - Error middleware
   - Custom exceptions
5. Provide examples from code
```

### Scenario: User is new to codebase

```
1. ctx_status  # Show codebase composition
2. ctx_search("main entry point", limit=5)
3. ctx_search("configuration", limit=5)
4. ctx_search("core functionality", limit=10)
5. Offer overview: "This is a [type] project with [languages], organized as..."
6. Ask what specific area they want to explore
```

### Scenario: Code has changed, index might be stale

```
1. ctx_status  # Check last indexed time
2. If stale (> 1 day or user mentions recent changes):
   Inform user: "The index was last updated [timestamp].
   You may want to run 'ctxd index' or I can trigger re-indexing."
3. If user approves: ctx_index()
4. Wait for completion, then proceed with search
```

---

## Performance Optimization

### Reduce Token Usage

```
1. Use appropriate limits (don't over-fetch)
2. Use filters to narrow results
3. deduplicate=true (default) to avoid overlaps
4. Only use expand_context when necessary
```

### Faster Searches

```
1. Use hybrid mode (default, usually fastest)
2. Add filters upfront (extensions, directories)
3. Use specific queries, not vague ones
4. Leverage ctxd's built-in caching (repeat queries are fast)
```

---

## Error Handling

### No MCP Tools Available

If `mcp__ctxd_*` tools don't exist:

```
1. Inform user: "ctxd is not configured via MCP"
2. Suggest: "You can run ctxd commands directly via Bash:
   - ctxd search 'query'
   - ctxd status
   - ctxd index"
3. Or direct them to setup guide
```

### No Index Found

If ctx_status shows no index:

```
1. Inform user: "No ctxd index found in this project"
2. Suggest: "Run these commands to set up ctxd:
   cd /path/to/project
   ctxd init
   ctxd index"
3. Or offer: "I can trigger indexing with ctx_index if you'd like"
```

### No Results

If search returns empty results:

```
1. Try broader query
2. Remove filters
3. Try different search mode (vector vs hybrid vs fts)
4. Check if index is up to date (ctx_status)
5. Inform user: "No results found for '[query]'. The code might use different terminology, or the index may need updating."
```

### Stale Index

If last_indexed timestamp is old:

```
1. Inform user: "Index was last updated [timestamp], which may be outdated"
2. Offer: "Would you like me to re-index? (ctx_index)"
3. If user approves, run ctx_index(force=false)
```

---

## Communication with User

### Report Search Process

Be transparent about searches:

```
Good: "I'll search the codebase for authentication logic..."
[Performs search]
"Found 8 relevant code chunks. The main authentication is in src/auth/login.py:15-42"

Avoid: Just showing results without context
```

### Reference Code Locations

Always use file:line format:

```
"The database connection is established in src/db/connection.py:23-45"
"User authentication happens in src/auth/login.py:78"
```

### Summarize Findings

Don't just dump search results:

```
Good:
"I found 3 main areas handling payments:
1. src/payments/processor.py:45 - Main payment processing
2. src/api/payment_routes.py:12 - API endpoints
3. src/models/payment.py:8 - Payment data model"

Avoid:
[Shows raw search results without synthesis]
```

### Suggest Next Steps

After searching, guide the user:

```
"I found the authentication code in src/auth/. Would you like me to:
- Explain how it works?
- Read the full file for detailed analysis?
- Search for related security code?"
```

---

## Integration with Other Skills

### With File Operations

```
ctxd search → Read → Edit
Example: Find function → Read full file → Make changes
```

### With Git Operations

```
ctxd search → Read → Edit → Commit
Example: Find outdated code → Update → Commit changes
```

### With Testing

```
ctxd search "test [feature]" → Read tests → Run tests
Example: Find tests for feature → Read test file → Execute pytest
```

### With Documentation

```
ctxd search [feature] → Read code → Generate docs
Example: Find all API routes → Analyze → Create API documentation
```

---

## Checklist for Using ctxd

Before searching:
- [ ] Verify MCP tools are available (`mcp__ctxd_*` prefix)
- [ ] Check index status with ctx_status
- [ ] Formulate clear, concept-based query
- [ ] Determine appropriate filters (extensions, directories, etc.)

During search:
- [ ] Start with appropriate limit (5-15 for exploration)
- [ ] Use hybrid mode unless specific need for vector/fts
- [ ] Set deduplicate=true to avoid redundant results
- [ ] Use expand_context only when context is needed

After search:
- [ ] Analyze results for relevance
- [ ] Read full files for detailed understanding
- [ ] Report findings with file:line references
- [ ] Suggest next steps to user

---

## Quick Reference

### Most Common Patterns

**Find implementation:**
```
ctx_search("[feature name]", limit=10)
```

**Find by language:**
```
ctx_search("[concept]", extensions=[".py"], limit=10)
```

**Find in specific area:**
```
ctx_search("[concept]", directories=["src/api/"], limit=10)
```

**Find functions only:**
```
ctx_search("[concept]", chunk_types=["function"], limit=10)
```

**Comprehensive exploration:**
```
ctx_search("[concept]", limit=20, expand_context=true)
```

**Check status:**
```
ctx_status
```

**Re-index:**
```
ctx_index()
```

---

## Summary

**Remember:**
1. ctxd is for **discovery** and **exploration**, not detailed analysis
2. Always check index status in new conversations
3. Use semantic queries, not exact identifiers
4. Start broad, refine with filters
5. Combine with Read tool for deep analysis
6. Report findings clearly with file:line references
7. Guide users on next steps

**Key Principle:**
Think of ctxd as your **code navigation system** - it tells you WHERE to look, then you use other tools to examine WHAT you found.

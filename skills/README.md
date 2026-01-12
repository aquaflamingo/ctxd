# ctxd Skills for Claude Code

This directory contains skill templates that teach Claude Code agents how to effectively use ctxd for semantic code search.

## Available Skills

### ctxd-search

**File:** `ctxd-search.md`

**Purpose:** Teaches Claude agents how to use ctxd MCP tools for semantic code search, codebase exploration, and understanding.

**What it teaches:**
- When to use ctxd vs other tools (Grep, Glob, Read)
- How to formulate effective semantic queries
- Search strategies and progressive refinement
- Workflow patterns for common scenarios
- Best practices for combining ctxd with other tools
- Error handling and troubleshooting

## How to Use These Skills

### Option 1: Direct Reference (Recommended)

Include the skill content in your project's `.claude/` directory so Claude Code loads it automatically:

```bash
# From the ctxd repository root
cp skills/ctxd-search.md /path/to/your/project/.claude/instructions/

# Or create a symlink for automatic updates
ln -s $(pwd)/skills/ctxd-search.md /path/to/your/project/.claude/instructions/
```

Claude Code will automatically load any markdown files in `.claude/instructions/` as context.

### Option 2: Include in CLAUDE.md

Add a reference to the skill in your project's `CLAUDE.md`:

```markdown
# Project Instructions

## Code Search with ctxd

When searching the codebase, use ctxd for semantic search.
See the complete guide in `.claude/instructions/ctxd-search.md`.
```

### Option 3: Paste into Conversation

For one-off usage, paste the relevant sections from `ctxd-search.md` into your conversation with Claude.

### Option 4: Reference in Prompts

Include skill instructions when invoking Claude:

```
Using the ctxd-search skill, find all authentication-related code in this project.
```

## Prerequisites

Before using the ctxd-search skill, ensure:

1. **ctxd is installed:**
   ```bash
   pip install ctxd
   # or
   uv pip install ctxd
   ```

2. **Your project is indexed:**
   ```bash
   cd /path/to/your/project
   ctxd init
   ctxd index
   ```

3. **MCP is configured** (in `~/.config/claude-code/settings.json`):
   ```json
   {
     "mcpServers": {
       "ctxd": {
         "command": "ctxd-mcp",
         "args": ["--project-root", "/absolute/path/to/project"]
       }
     }
   }
   ```

4. **Claude Code is restarted** after MCP configuration

## Verifying the Skill is Active

Start a conversation with Claude Code and ask:

```
Do you have access to ctxd tools?
```

Claude should recognize the `mcp__ctxd_ctx_search`, `mcp__ctxd_ctx_status`, and `mcp__ctxd_ctx_index` tools.

## Example Usage

Once the skill is loaded, Claude will automatically know how to use ctxd effectively:

**Example 1: Finding Code**
```
User: Where is the authentication logic?

Claude: [Uses ctx_search effectively]
I'll search for authentication logic in the codebase...
[Performs semantic search with appropriate parameters]
Found authentication in src/auth/login.py:23-45...
```

**Example 2: Understanding Architecture**
```
User: Explain how the database layer works

Claude: [Uses ctx_search with multiple queries]
Let me search for database-related code...
[Searches for "database", "connection", "models"]
The database layer is organized as follows:
- Connection pooling: src/db/pool.py:12
- Models: src/models/*.py
- Migrations: db/migrations/
```

**Example 3: Debugging**
```
User: There's a bug in payment processing, help me find the code

Claude: [Uses progressive search refinement]
I'll search for payment processing code...
[Starts broad, then narrows with filters]
Found the payment processing in these files:
1. src/payments/processor.py:45-89 - Main processing logic
2. src/api/payment_routes.py:23-56 - API endpoints
Would you like me to analyze these for potential issues?
```

## Customizing the Skill

You can customize `ctxd-search.md` for your team's needs:

1. **Add project-specific patterns:**
   ```markdown
   ### Our Project Structure

   In this project:
   - API routes are in `src/routes/`
   - Business logic is in `src/services/`
   - Always search both when investigating features
   ```

2. **Add team conventions:**
   ```markdown
   ### Team Conventions

   - We use `_handler` suffix for API handlers
   - Tests are colocated with code (same directory)
   - Search for `[feature]_handler` and `test_[feature]` together
   ```

3. **Add common queries:**
   ```markdown
   ### Common Searches for This Project

   - Authentication: Search "auth middleware" or "login handler"
   - Database: Search "database session" or "SQLAlchemy models"
   - API: Search "route handler" or "API endpoint"
   ```

## Sharing with Your Team

### For Open Source Projects

Include in your repository:

```bash
# In your project root
mkdir -p .claude/instructions/
cp /path/to/ctxd/skills/ctxd-search.md .claude/instructions/
git add .claude/instructions/ctxd-search.md
git commit -m "Add ctxd-search skill for Claude Code"
```

### For Private Teams

1. **Add to team docs:**
   - Put skill in team wiki or docs repository
   - Link from main README

2. **Include in onboarding:**
   - Add setup instructions to onboarding docs
   - Include in developer environment setup script

3. **Create setup script:**
   ```bash
   #!/bin/bash
   # setup-claude.sh

   # Copy skills to project
   mkdir -p .claude/instructions
   curl -o .claude/instructions/ctxd-search.md \
     https://raw.githubusercontent.com/yourteam/ctxd-skills/main/ctxd-search.md

   echo "✓ Claude Code skills installed"
   ```

## Troubleshooting

### Claude isn't using ctxd effectively

**Problem:** Claude uses Grep instead of ctxd for semantic searches

**Solution:**
1. Verify skill is in `.claude/instructions/`
2. Check that MCP tools are available (ask "what tools do you have?")
3. Explicitly mention: "Use ctxd to search for..."

### Claude can't find ctxd tools

**Problem:** Error: "ctxd tools not available"

**Solution:**
1. Check MCP configuration in settings.json
2. Verify `ctxd-mcp` is in PATH: `which ctxd-mcp`
3. Restart Claude Code completely
4. Check project is indexed: `ctxd status`

### Skills not loading

**Problem:** Claude doesn't seem aware of skill instructions

**Solution:**
1. Verify file is in `.claude/instructions/` directory
2. Check file has `.md` extension
3. Restart Claude Code or start new conversation
4. Try pasting skill content directly into conversation

## Contributing

To improve these skills:

1. Fork the ctxd repository
2. Edit `skills/ctxd-search.md`
3. Test with real Claude Code usage
4. Submit PR with improvements

### Improvement Ideas

- Add more scenario examples
- Include project-specific patterns
- Add troubleshooting for common issues
- Create language-specific search patterns
- Add integration patterns with other tools

## Related Documentation

- [ctxd README](../README.md) - Overview and installation
- [Claude Code Guide](../docs/claude-code-guide.md) - User-facing guide
- [MCP Integration](../docs/mcp-integration.md) - MCP setup details
- [Configuration](../docs/configuration.md) - ctxd configuration

## License

Same as ctxd main project.

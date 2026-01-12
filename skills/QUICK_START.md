# ctxd Skill Quick Start

Get Claude Code agents using ctxd effectively in 2 minutes.

## What This Is

A skill template that teaches Claude Code how to use ctxd for semantic code search - just like how Claude knows how to use git commands.

## Installation (3 steps)

### 1. Install ctxd (if not already installed)

```bash
pip install ctxd
# or
uv pip install ctxd
```

### 2. Index your project

```bash
cd /path/to/your/project
ctxd init
ctxd index
```

### 3. Install the skill

```bash
cd /path/to/ctxd
./skills/install-skill.sh /path/to/your/project
```

That's it! The skill is now installed.

## Verify It Works

Start Claude Code in your project and ask:

```
Do you have access to ctxd tools?
```

Claude should confirm it has `ctx_search`, `ctx_status`, and `ctx_index` tools.

Then try:

```
Where is the authentication logic?
```

Claude will automatically use ctxd to semantically search your codebase!

## What Changes?

### Before (without skill)

Claude uses:
- **Grep** for keyword search (many false positives)
- **Read** to scan entire files (wastes tokens)
- **Glob** to guess file names (might miss code)

Results: Inefficient, high token usage, might miss relevant code.

### After (with skill)

Claude uses:
- **ctxd semantic search** to find code by meaning
- **Ranked results** with relevance scores
- **Specific line ranges** instead of full files
- **Progressive refinement** for better results

Results: Efficient, low token usage, finds all relevant code.

## Example Workflow

**You:** "Explain how authentication works in this codebase"

**Claude (with skill):**
1. Checks index status
2. Searches for "authentication flow"
3. Searches for "login logic"
4. Searches for "session management"
5. Analyzes ranked results
6. Explains architecture with file:line references
7. Asks if you want deeper analysis

All while using minimal tokens!

## What the Skill Teaches Claude

### When to Use ctxd
- Finding code by concept ("error handling patterns")
- Exploring unfamiliar codebases
- Locating functionality without knowing file names
- Understanding architecture
- Debugging ("find all payment processing code")

### When NOT to Use ctxd
- Reading known specific files (use Read)
- Searching for exact strings (use Grep)
- Listing files by pattern (use Glob)

### How to Search Effectively
- Semantic queries: "database connection pooling" ✓
- Not keyword queries: "db_conn" ✗
- Progressive refinement: broad → narrow
- Smart filtering: by language, directory, file type
- Result ranking: relevance scores

### Best Practices
- Check index status first
- Combine with other tools (ctxd → Read → Edit)
- Use appropriate result limits
- Report findings with file:line references
- Guide users on next steps

## Files Created

```
skills/
├── README.md              # Full documentation
├── QUICK_START.md         # This file
├── EXAMPLES.md            # Before/after examples
├── ctxd-search.md         # The actual skill (loaded by Claude)
└── install-skill.sh       # Installation script
```

## Directory Structure After Install

```
your-project/
├── .claude/
│   └── instructions/
│       └── ctxd-search.md    # Skill loaded by Claude Code
├── .ctxd/
│   ├── config.toml           # ctxd configuration
│   └── data.lance/           # Vector database
├── src/
│   └── [your code]
└── [other files]
```

## Customization

Edit `.claude/instructions/ctxd-search.md` to add project-specific patterns:

```markdown
### Our Project Patterns

In this project:
- API routes are in `src/routes/`
- Business logic is in `src/services/`
- Always search both when investigating features
```

## Sharing with Your Team

### Add to Git

```bash
git add .claude/instructions/ctxd-search.md
git commit -m "Add ctxd skill for Claude Code"
git push
```

Now everyone on your team gets the skill when they clone!

### Company-Wide Deployment

1. Fork this repo
2. Customize `skills/ctxd-search.md` for your patterns
3. Add to onboarding docs:
   ```bash
   # In new project setup
   /path/to/ctxd/skills/install-skill.sh .
   ```

## Troubleshooting

### "ctxd tools not available"

1. Check MCP config: `cat ~/.config/claude-code/settings.json`
2. Verify ctxd-mcp exists: `which ctxd-mcp`
3. Restart Claude Code completely
4. Check index: `ctxd status`

### Skill not loading

1. Verify file exists: `ls .claude/instructions/ctxd-search.md`
2. Restart Claude Code or start new conversation
3. Try asking: "What instructions do you have about ctxd?"

### Claude still using Grep

1. Verify skill is in `.claude/instructions/`
2. Explicitly say: "Use ctxd to search for..."
3. Check that MCP tools are available

## Next Steps

1. **Read examples**: See `EXAMPLES.md` for detailed comparisons
2. **Customize**: Edit the skill for your project's patterns
3. **Share**: Add to git so your team benefits
4. **Iterate**: Improve the skill based on usage

## Learn More

- [Skill Documentation](README.md) - Complete guide
- [Before/After Examples](EXAMPLES.md) - See the difference
- [Main ctxd README](../README.md) - ctxd overview
- [Claude Code Guide](../docs/claude-code-guide.md) - User guide

## Support

- Issues: Open on GitHub
- Questions: Check docs/ directory
- Improvements: PRs welcome!

---

**You're done!** Claude now knows how to use ctxd effectively. Try it out!

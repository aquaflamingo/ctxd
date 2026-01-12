#!/bin/bash
# Install ctxd-search skill for Claude Code
# Usage: ./install-skill.sh [project-path]
#
# This script installs the ctxd-search skill instructions for Claude Code
# so that Claude agents know how to effectively use ctxd for semantic code search.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get project path from argument or use current directory
PROJECT_PATH="${1:-.}"

# Resolve to absolute path
PROJECT_PATH=$(cd "$PROJECT_PATH" && pwd)

echo -e "${BLUE}Installing ctxd-search skill for Claude Code${NC}"
echo -e "Target project: ${GREEN}$PROJECT_PATH${NC}"
echo

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SKILL_FILE="$SCRIPT_DIR/ctxd-search.md"

# Verify skill file exists
if [ ! -f "$SKILL_FILE" ]; then
    echo -e "${RED}Error: ctxd-search.md not found at $SKILL_FILE${NC}"
    exit 1
fi

# Create .claude/instructions directory
INSTRUCTIONS_DIR="$PROJECT_PATH/.claude/instructions"
echo -e "${BLUE}Creating instructions directory...${NC}"
mkdir -p "$INSTRUCTIONS_DIR"

# Copy skill file
DEST_FILE="$INSTRUCTIONS_DIR/ctxd-search.md"
echo -e "${BLUE}Copying skill file...${NC}"
cp "$SKILL_FILE" "$DEST_FILE"

echo -e "${GREEN}✓${NC} Skill installed to: $DEST_FILE"
echo

# Check if .gitignore exists and .claude is not ignored
if [ -f "$PROJECT_PATH/.gitignore" ]; then
    if grep -q "^\.claude" "$PROJECT_PATH/.gitignore"; then
        echo -e "${YELLOW}Warning: .claude is in .gitignore${NC}"
        echo -e "Consider sharing the skill with your team by removing .claude from .gitignore"
        echo
    fi
fi

# Check if ctxd is indexed
if [ ! -d "$PROJECT_PATH/.ctxd" ]; then
    echo -e "${YELLOW}⚠ ctxd not initialized in this project${NC}"
    echo -e "To use ctxd, run:"
    echo -e "  ${BLUE}cd $PROJECT_PATH${NC}"
    echo -e "  ${BLUE}ctxd init${NC}"
    echo -e "  ${BLUE}ctxd index${NC}"
    echo
fi

# Check if MCP is configured
MCP_CONFIG="$HOME/.config/claude-code/settings.json"
if [ ! -f "$MCP_CONFIG" ]; then
    echo -e "${YELLOW}⚠ Claude Code MCP settings not found${NC}"
    echo -e "To configure ctxd with Claude Code, create:"
    echo -e "  ${BLUE}$MCP_CONFIG${NC}"
    echo
    echo -e "With content:"
    echo -e "${BLUE}"
    cat <<EOF
{
  "mcpServers": {
    "ctxd": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "$PROJECT_PATH"]
    }
  }
}
EOF
    echo -e "${NC}"
else
    echo -e "${GREEN}✓${NC} Claude Code MCP settings found"

    # Check if ctxd is configured
    if grep -q "ctxd" "$MCP_CONFIG"; then
        echo -e "${GREEN}✓${NC} ctxd appears to be configured in MCP"
    else
        echo -e "${YELLOW}⚠ ctxd not found in MCP configuration${NC}"
        echo -e "Add to ${BLUE}$MCP_CONFIG${NC}:"
        echo -e "${BLUE}"
        cat <<EOF
{
  "mcpServers": {
    "ctxd": {
      "command": "ctxd-mcp",
      "args": ["--project-root", "$PROJECT_PATH"]
    }
  }
}
EOF
        echo -e "${NC}"
    fi
fi

echo
echo -e "${GREEN}Installation complete!${NC}"
echo
echo -e "Next steps:"
echo -e "  1. Ensure ctxd is indexed: ${BLUE}cd $PROJECT_PATH && ctxd index${NC}"
echo -e "  2. Configure MCP in ${BLUE}~/.config/claude-code/settings.json${NC}"
echo -e "  3. Restart Claude Code"
echo -e "  4. Ask Claude: ${BLUE}\"Do you have access to ctxd tools?\"${NC}"
echo
echo -e "The skill will teach Claude how to effectively use ctxd for:"
echo -e "  • Semantic code search"
echo -e "  • Codebase exploration"
echo -e "  • Finding implementations"
echo -e "  • Understanding architecture"
echo

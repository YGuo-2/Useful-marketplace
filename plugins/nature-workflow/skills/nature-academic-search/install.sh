#!/usr/bin/env bash
# Academic Search Skill + MCP Server Installer for Claude Code
# Usage: bash install.sh [PUBMED_EMAIL]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
MCP_TARGET="${CLAUDE_DIR}/mcp_servers/academic-search"
SKILL_TARGET="${CLAUDE_DIR}/skills/academic-search"
MCP_JSON="${CLAUDE_DIR}/.mcp.json"

PUBMED_EMAIL="${1:-user@example.com}"

echo "=== Academic Search Installer ==="
echo "Target: ${CLAUDE_DIR}"
echo "PubMed email: ${PUBMED_EMAIL}"
echo

required_paths=(
    "README.md"
    "SKILL.md"
    "manifest.yaml"
    "static"
    "references"
    "scripts"
    "config"
    "mcp-server"
)

missing_paths=()
for relpath in "${required_paths[@]}"; do
    if [ ! -e "${SCRIPT_DIR}/${relpath}" ]; then
        missing_paths+=("${relpath}")
    fi
done

if [ "${#missing_paths[@]}" -gt 0 ]; then
    echo "ERROR: incomplete nature-academic-search skill directory." >&2
    echo "Missing required path(s):" >&2
    for relpath in "${missing_paths[@]}"; do
        echo "  - ${SCRIPT_DIR}/${relpath}" >&2
    done
    echo "Install the full skills/nature-academic-search folder and retry." >&2
    exit 1
fi

# 1. Check for uv (deps are installed on demand by `uv run --with`)
echo "[1/5] Checking uv..."
if command -v uv >/dev/null 2>&1; then
    echo "  uv found; Python dependencies will be resolved on demand via 'uv run --with'."
else
    echo "  WARNING: uv not found. The academic-search MCP server starts with 'uv run'."
    echo "    Install uv first: https://docs.astral.sh/uv/getting-started/installation/"
fi

# 2. Copy MCP server
echo "[2/5] Copying MCP server..."
mkdir -p "${MCP_TARGET}"
cp -r "${SCRIPT_DIR}/mcp-server/"* "${MCP_TARGET}/"

# 3. Copy Skill
echo "[3/5] Copying Skill..."
mkdir -p "${SKILL_TARGET}"
cp "${SCRIPT_DIR}/README.md" "${SKILL_TARGET}/"
cp "${SCRIPT_DIR}/SKILL.md" "${SKILL_TARGET}/"
cp "${SCRIPT_DIR}/manifest.yaml" "${SKILL_TARGET}/"
cp -r "${SCRIPT_DIR}/static" "${SKILL_TARGET}/"
cp -r "${SCRIPT_DIR}/references" "${SKILL_TARGET}/"
cp -r "${SCRIPT_DIR}/scripts" "${SKILL_TARGET}/"
cp -r "${SCRIPT_DIR}/config" "${SKILL_TARGET}/"

# 4. Merge .mcp.json
echo "[4/5] Configuring .mcp.json..."
if [ -f "${MCP_JSON}" ]; then
    # Check if academic-search already exists
    if grep -q '"academic-search"' "${MCP_JSON}" 2>/dev/null; then
        echo "  academic-search already in .mcp.json, skipping merge."
    else
        # Inject into existing mcpServers object
        python3 -c "
import json, sys
with open('${MCP_JSON}', 'r') as f:
    cfg = json.load(f)
cfg.setdefault('mcpServers', {})['academic-search'] = {
    'command': 'uv',
    'args': [
        'run', '--no-project',
        '--directory', '${MCP_TARGET}',
        '--with', 'mcp>=1.0.0,<2.0.0',
        '--with', 'requests>=2.28.0,<3.0.0',
        '--with', 'toml>=0.10.2,<2.0.0',
        '--with', 'lxml>=4.9.0,<6.0.0',
        '--with', 'defusedxml>=0.7.0',
        '--with', 'pybliometrics>=4.4.1,<5.0.0',
        'python', 'academic_search_server.py'
    ],
    'env': {'PUBMED_EMAIL': '${PUBMED_EMAIL}'}
}
with open('${MCP_JSON}', 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
print('  Merged academic-search into existing .mcp.json')
"
    fi
else
    cat > "${MCP_JSON}" <<MCPJSON
{
  "mcpServers": {
    "academic-search": {
      "command": "uv",
      "args": [
        "run",
        "--no-project",
        "--directory",
        "${MCP_TARGET}",
        "--with",
        "mcp>=1.0.0,<2.0.0",
        "--with",
        "requests>=2.28.0,<3.0.0",
        "--with",
        "toml>=0.10.2,<2.0.0",
        "--with",
        "lxml>=4.9.0,<6.0.0",
        "--with",
        "defusedxml>=0.7.0",
        "--with",
        "pybliometrics>=4.4.1,<5.0.0",
        "python",
        "academic_search_server.py"
      ],
      "env": {
        "PUBMED_EMAIL": "${PUBMED_EMAIL}"
      }
    }
  }
}
MCPJSON
    echo "  Created new .mcp.json"
fi

# 5. Enable in settings.json
echo "[5/5] Enabling in settings.json..."
SETTINGS_JSON="${CLAUDE_DIR}/settings.json"
if [ -f "${SETTINGS_JSON}" ]; then
    python3 -c "
import json
with open('${SETTINGS_JSON}', 'r') as f:
    cfg = json.load(f)
enabled = cfg.setdefault('enabledMcpjsonServers', [])
if 'academic-search' not in enabled:
    enabled.append('academic-search')
    with open('${SETTINGS_JSON}', 'w') as f:
        json.dump(cfg, f, indent=2)
        f.write('\n')
    print('  Added academic-search to enabledMcpjsonServers')
else:
    print('  academic-search already enabled')
"
else
    echo '  WARNING: settings.json not found. Manually add "academic-search" to enabledMcpjsonServers.'
fi

echo
echo "=== Done ==="
echo
echo "Installed:"
echo "  MCP server : ${MCP_TARGET}/"
echo "  Skill      : ${SKILL_TARGET}/"
echo
echo "Next steps:"
echo "  1. Restart Claude Code (or /clear)"
echo "  2. Set your PubMed email in config.toml or PUBMED_EMAIL env var"
echo "  3. (Optional) Add NCBI_API_KEY for higher rate limits"
echo "  4. Test: ask Claude 'search papers about CRISPR'"
echo
echo "Optional: copy triggers to your data/triggers.toml"
echo "  See: config/triggers-academic-search.toml"

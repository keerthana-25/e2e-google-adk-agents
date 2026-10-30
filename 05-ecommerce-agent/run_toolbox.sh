#!/usr/bin/env bash
# Starts MCP Toolbox for Databases on :5000 with the shop tools.
set -euo pipefail
cd "$(dirname "$0")"

export DB_HOST="${DB_HOST:-127.0.0.1}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-shopdb}"
export DB_USER="${DB_USER:-postgres}"
export DB_PASSWORD="${DB_PASSWORD:-postgres}"

npx -y @toolbox-sdk/server@1.15.0 --config mcp-toolbox/tools.yaml --port 5000

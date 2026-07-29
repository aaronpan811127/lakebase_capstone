#!/usr/bin/env bash
# Build the React frontend AND stage the compiled bundle so the git-source app
# deploys the current UI.
#
# WHY THIS EXISTS: the built bundle lives in `backend/static/` (outside
# `frontend/`), and Vite's `emptyOutDir` renames hashed files on every build.
# `git add frontend/` does NOT stage those outputs, so it's easy to commit source
# changes while the deployed app keeps serving a stale bundle. Always build via
# this script (or `npm run build:deploy`) before committing UI changes.
#
# Usage:  cd capstone-scaffold/app && ./build.sh
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR/frontend"

echo "→ building frontend…"
npm run build

echo "→ staging built bundle (backend/static)…"
# -A picks up renamed/deleted hashed assets too.
git -C "$APP_DIR" add -A backend/static

echo "✓ built and staged. Deployed UI will match source once you commit + push + bundle run."
git -C "$APP_DIR" status --short backend/static | head

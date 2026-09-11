#!/usr/bin/env bash
# Runs once, when the devcontainer is first created.
# Everything here must work with no API key. Network is used only to install
# pinned dependencies; the demos themselves never need it.
set -euo pipefail

echo "node:   $(node --version)   (expected v24.12.0)"
echo "npm:    $(npm --version)"
echo "python: $(python3 --version)   (expected 3.13.x)"

# Pinned dev dependencies for the lectures that have code.
for dir in 00-setup 01-variance 02-mcp-server; do
  if [ -f "$dir/package.json" ]; then
    echo "--- npm ci in $dir"
    (cd "$dir" && npm ci --no-audit --no-fund)
  fi
done

echo
echo "Готово. Следваща стъпка: cd 00-setup && npm run check"

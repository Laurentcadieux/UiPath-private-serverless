#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SETUP_SCRIPT="$REPO_ROOT/OUTPUT_Setup/install.sh"

if [ -f "$SETUP_SCRIPT" ]; then
  exec bash "$SETUP_SCRIPT"
fi

REPO_URL="${REPO_URL:-https://github.com/Laurentcadieux/UiPath-private-serverless.git}"
BRANCH="${BRANCH:-main}"

if command -v curl >/dev/null 2>&1; then
  curl -fsSL "$REPO_URL/raw/$BRANCH/OUTPUT_Setup/install.sh" | bash
  exit $?
fi

echo "ERROR: OUTPUT_Setup/install.sh was not found beside OUTPUT_Product." >&2
echo "Run the setup script from the repository root instead:" >&2
echo "  sudo -E bash OUTPUT_Setup/install.sh" >&2
echo "Or install curl and fetch: $REPO_URL/raw/$BRANCH/OUTPUT_Setup/install.sh" >&2
exit 2

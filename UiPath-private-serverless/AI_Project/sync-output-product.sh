#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 /path/to/public-product-repo" >&2
  exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$1"

if [ ! -f "$PROJECT_ROOT/OUTPUT_Product/pyproject.toml" ]; then
  echo "ERROR: OUTPUT_Product does not look like a Python product folder." >&2
  exit 2
fi

if [ ! -f "$PROJECT_ROOT/OUTPUT_Setup/install.sh" ]; then
  echo "ERROR: OUTPUT_Setup does not contain install.sh." >&2
  exit 2
fi

mkdir -p "$TARGET_DIR"
rsync -a --delete --delete-excluded \
  --exclude ".git/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  --include "/README.md" \
  --include "/OUTPUT_Product/***" \
  --include "/OUTPUT_Setup/***" \
  --exclude "*" \
  "$PROJECT_ROOT/" "$TARGET_DIR/"

echo "Synced README.md, OUTPUT_Setup, and OUTPUT_Product to $TARGET_DIR"

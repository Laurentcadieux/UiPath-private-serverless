#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 /path/to/public-product-repo" >&2
  exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="$PROJECT_ROOT/OUTPUT_Product"
TARGET_DIR="$1"

if [ ! -f "$OUTPUT_DIR/pyproject.toml" ]; then
  echo "ERROR: OUTPUT_Product does not look like a Python product folder." >&2
  exit 2
fi

mkdir -p "$TARGET_DIR"
rsync -a --delete \
  --exclude ".git/" \
  --exclude "__pycache__/" \
  --exclude "*.pyc" \
  "$OUTPUT_DIR/" "$TARGET_DIR/"

echo "Synced OUTPUT_Product to $TARGET_DIR"

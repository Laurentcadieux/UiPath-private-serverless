#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${CONFIG_PATH:-/etc/uipath-runtime/config.yaml}"
SECRETS_PATH="${SECRETS_PATH:-/etc/uipath-runtime/secrets.env}"
COUNT="${COUNT:-1}"
TARGET="${TARGET:-uipath-robot}"
IMAGE_TAR="${IMAGE_TAR:-}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root, for example: sudo -E bash OUTPUT_Setup/init-product.sh" >&2
  exit 3
fi

if [ ! -f "$CONFIG_PATH" ]; then
  echo "ERROR: missing config at $CONFIG_PATH. Run OUTPUT_Setup/install.sh first." >&2
  exit 2
fi

if [ -f "$SECRETS_PATH" ]; then
  set -a
  . "$SECRETS_PATH"
  set +a
fi

command_args=(
  init
  "$TARGET"
  --config "$CONFIG_PATH"
  --count "$COUNT"
  --auto-install-host-deps
)

if [ -n "$IMAGE_TAR" ]; then
  command_args+=(--image-tar "$IMAGE_TAR")
fi

uipath-runtime "${command_args[@]}"

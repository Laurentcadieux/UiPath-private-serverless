#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${CONFIG_PATH:-/etc/uipath-runtime/config.yaml}"
SECRETS_PATH="${SECRETS_PATH:-/etc/uipath-runtime/secrets.env}"
COUNT="${COUNT:-1}"
TARGET="${TARGET:-uipath-robot}"
IMAGE_TAR="${IMAGE_TAR:-}"
PULL_IMAGE="${PULL_IMAGE:-1}"
RECREATE="${RECREATE:-0}"

runtime_image_from_config() {
  awk '
    /^runtime:/ { in_runtime = 1; next }
    /^[^[:space:]]/ { in_runtime = 0 }
    in_runtime && /^[[:space:]]+image:/ {
      sub(/^[[:space:]]+image:[[:space:]]*/, "")
      gsub(/^"|"$/, "")
      print
      exit
    }
  ' "$CONFIG_PATH"
}

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

RUNTIME_IMAGE="$(runtime_image_from_config)"

if [ -n "$IMAGE_TAR" ]; then
  if [ ! -f "$IMAGE_TAR" ]; then
    echo "ERROR: IMAGE_TAR was set, but the file does not exist: $IMAGE_TAR" >&2
    exit 2
  fi
elif [ -n "$RUNTIME_IMAGE" ] && ! docker image inspect "$RUNTIME_IMAGE" >/dev/null 2>&1; then
  if [ "$PULL_IMAGE" = "1" ]; then
    echo "UiPath Robot image missing locally; pulling $RUNTIME_IMAGE"
    docker pull "$RUNTIME_IMAGE"
  else
    echo "ERROR: UiPath Robot image is not available locally." >&2
    echo "Required image: $RUNTIME_IMAGE" >&2
    echo >&2
    echo "Load the image before running init:" >&2
    echo "  docker load --input /path/to/uipath-robot-image.tar" >&2
    echo >&2
    echo "Or allow init-product.sh to pull it:" >&2
    echo "  PULL_IMAGE=1 bash OUTPUT_Setup/init-product.sh" >&2
    echo >&2
    echo "You can also pass an archive directly to this script:" >&2
    echo "  IMAGE_TAR=/path/to/uipath-robot-image.tar bash OUTPUT_Setup/init-product.sh" >&2
    exit 2
  fi
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

if [ "$RECREATE" = "1" ]; then
  command_args+=(--recreate)
fi

uipath-runtime "${command_args[@]}"

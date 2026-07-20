#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Laurentcadieux/UiPath-private-serverless.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/UiPath-private-serverless}"
CONFIG_PATH="${CONFIG_PATH:-/etc/uipath-runtime/config.yaml}"
SECRETS_PATH="${SECRETS_PATH:-/etc/uipath-runtime/secrets.env}"
COUNT="${COUNT:-1}"
RUN_INIT="${RUN_INIT:-0}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root, for example: sudo -E bash scripts/bootstrap-live-host.sh" >&2
  exit 3
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y \
  ca-certificates \
  curl \
  git \
  gnupg \
  openssl \
  python3 \
  python3-venv

if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y docker.io docker-compose-v2 || apt-get install -y docker.io
fi

systemctl enable --now docker

if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" fetch --depth 1 origin "$BRANCH"
  git -C "$INSTALL_DIR" checkout "$BRANCH"
  git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
else
  rm -rf "$INSTALL_DIR"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
fi

"$INSTALL_DIR/scripts/install.sh"

mkdir -p /etc/uipath-runtime
if [ ! -f "$CONFIG_PATH" ]; then
  cp "$INSTALL_DIR/config/config.example.yaml" "$CONFIG_PATH"
  chmod 644 "$CONFIG_PATH"
  echo "Created default config at $CONFIG_PATH. Edit orchestrator.url and runtime.image before init."
fi

if [ -n "${UIPATH_MACHINE_KEY:-}" ]; then
  umask 077
  printf 'UIPATH_MACHINE_KEY=%s\n' "$UIPATH_MACHINE_KEY" > "$SECRETS_PATH"
  chown root:root "$SECRETS_PATH"
  chmod 600 "$SECRETS_PATH"
fi

echo "Installed uipath-runtime from $REPO_URL ($BRANCH)"
echo "Config: $CONFIG_PATH"
echo "Secrets: $SECRETS_PATH"
echo "Docker: $(docker --version)"
echo "Next command:"
echo "  uipath-runtime init --config $CONFIG_PATH --count $COUNT --auto-install-host-deps"

if [ "$RUN_INIT" = "1" ]; then
  uipath-runtime init --config "$CONFIG_PATH" --count "$COUNT" --auto-install-host-deps
fi

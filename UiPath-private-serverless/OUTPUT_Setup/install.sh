#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Laurentcadieux/UiPath-private-serverless.git}"
BRANCH="${BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-/opt/UiPath-private-serverless}"
PRODUCT_SUBDIR="${PRODUCT_SUBDIR:-OUTPUT_Product}"
CONFIG_PATH="${CONFIG_PATH:-/etc/uipath-runtime/config.yaml}"
SECRETS_PATH="${SECRETS_PATH:-/etc/uipath-runtime/secrets.env}"
COUNT="${COUNT:-1}"
RUN_INIT="${RUN_INIT:-0}"

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: run as root, for example: sudo -E bash OUTPUT_Setup/install.sh" >&2
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
  python3-pip \
  python3-venv

if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y docker.io docker-compose-v2 || apt-get install -y docker.io
fi

systemctl enable --now docker

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CANDIDATE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$CANDIDATE_ROOT/$PRODUCT_SUBDIR/pyproject.toml" ]; then
  REPO_ROOT="$CANDIDATE_ROOT"
else
  if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" fetch --depth 1 origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" reset --hard "origin/$BRANCH"
  else
    rm -rf "$INSTALL_DIR"
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi
  REPO_ROOT="$INSTALL_DIR"
fi

PRODUCT_DIR="$REPO_ROOT/$PRODUCT_SUBDIR"
SETUP_DIR="$REPO_ROOT/OUTPUT_Setup"

if [ ! -f "$PRODUCT_DIR/pyproject.toml" ]; then
  echo "ERROR: product folder not found at $PRODUCT_DIR" >&2
  exit 2
fi

bash "$PRODUCT_DIR/scripts/install.sh"

mkdir -p "$(dirname "$CONFIG_PATH")"
if [ ! -f "$CONFIG_PATH" ]; then
  cp "$PRODUCT_DIR/config/config.example.yaml" "$CONFIG_PATH"
  chmod 644 "$CONFIG_PATH"
  echo "Created default config at $CONFIG_PATH. Edit orchestrator.url and runtime.image before init."
fi

if [ -n "${UIPATH_MACHINE_KEY:-}" ]; then
  umask 077
  printf 'UIPATH_MACHINE_KEY=%s\n' "$UIPATH_MACHINE_KEY" > "$SECRETS_PATH"
  chown root:root "$SECRETS_PATH"
  chmod 600 "$SECRETS_PATH"
fi

echo "Installed UiPath private serverless runtime."
echo "Repository: $REPO_ROOT"
echo "Product folder: $PRODUCT_DIR"
echo "Config: $CONFIG_PATH"
echo "Secrets: $SECRETS_PATH"
echo "Docker: $(docker --version)"
echo
echo "Next step:"
echo "  sudo -E bash $SETUP_DIR/init-product.sh"

if [ "$RUN_INIT" = "1" ]; then
  COUNT="$COUNT" CONFIG_PATH="$CONFIG_PATH" SECRETS_PATH="$SECRETS_PATH" bash "$SETUP_DIR/init-product.sh"
fi

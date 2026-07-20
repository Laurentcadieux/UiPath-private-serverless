#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="${SOURCE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
VENV_DIR="${VENV_DIR:-/opt/uipath-runtime-venv}"

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install "$SOURCE_DIR"
ln -sfn "$VENV_DIR/bin/uipath-runtime" /usr/local/bin/uipath-runtime
mkdir -p /etc/uipath-runtime /etc/uipath-runtime/certs /var/lib/uipath-runtime/packages /var/lib/uipath-runtime/nuget /var/log/uipath-runtime
chmod 755 /etc/uipath-runtime /etc/uipath-runtime/certs /var/lib/uipath-runtime /var/log/uipath-runtime
chmod 750 /var/lib/uipath-runtime/packages

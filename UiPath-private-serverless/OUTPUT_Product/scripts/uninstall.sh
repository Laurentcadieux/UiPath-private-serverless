#!/usr/bin/env bash
set -euo pipefail

rm -f /usr/local/bin/uipath-runtime
rm -rf /opt/uipath-runtime-venv
echo "Runtime data under /etc/uipath-runtime, /var/lib/uipath-runtime, and /var/log/uipath-runtime was left in place."

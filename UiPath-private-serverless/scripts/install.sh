#!/usr/bin/env bash
set -euo pipefail

python3 -m venv /opt/uipath-runtime-venv
/opt/uipath-runtime-venv/bin/pip install --upgrade pip
/opt/uipath-runtime-venv/bin/pip install /opt/uipath-runtime-provisioner
ln -sfn /opt/uipath-runtime-venv/bin/uipath-runtime /usr/local/bin/uipath-runtime
mkdir -p /etc/uipath-runtime /etc/uipath-runtime/certs /var/lib/uipath-runtime/packages /var/lib/uipath-runtime/nuget /var/log/uipath-runtime
chmod 755 /etc/uipath-runtime /etc/uipath-runtime/certs /var/lib/uipath-runtime /var/log/uipath-runtime
chmod 750 /var/lib/uipath-runtime/packages

# UiPath Private Serverless

Production-oriented Python CLI for provisioning a local Ubuntu host as a private UiPath Linux Robot container runtime.

## Purpose

- Initialize Ubuntu 22.04/24.04 amd64 hosts for UiPath Linux Robot containers.
- Create deterministic local Docker containers from a preloaded UiPath Robot image.
- Keep image handling local-only: the MVP never runs `docker pull`.
- Connect containers to an on-premises UiPath Orchestrator via machine key.
- Support configurable DNS, package feeds, shared package cache, optional private CA, labels, logs, status, and drift detection.

## Layout

- `config/` - example runtime and secret configuration
- `src/` - Python package source code
- `deploy/` - deployment scripts, infrastructure notes, packaging output
- `docs/` - architecture, runbooks, and UiPath design notes
- `scripts/` - install/uninstall helpers
- `systemd/` - service unit template
- `tests/` - smoke tests and regression checks

## Usage

Install Python dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

Prepare configuration:

```bash
sudo mkdir -p /etc/uipath-runtime
sudo cp config/config.example.yaml /etc/uipath-runtime/config.yaml
export UIPATH_MACHINE_KEY="machine-template-key"
```

Run initialization:

```bash
sudo --preserve-env=UIPATH_MACHINE_KEY \
  uipath-runtime init uipath-robot \
  --config /etc/uipath-runtime/config.yaml \
  --count 10
```

Short form:

```bash
sudo --preserve-env=UIPATH_MACHINE_KEY uipath-runtime init --count 10
```

Check managed containers:

```bash
uipath-runtime status --config /etc/uipath-runtime/config.yaml
```

## Safety Rules

- Machine keys are read from environment or root-only secret file, never from YAML.
- Machine keys are masked in output.
- The configured UiPath image must exist locally; automatic image pull is out of scope.
- Containers are managed only through `com.uipath.runtime.*` labels.
- Existing drifted containers are reported, not recreated, unless `--recreate` is supplied.
- Decreasing desired count never removes containers in MVP 1.

## Current Status

- MVP CLI source created.
- Unit tests cover config validation, naming, secret masking, CA validation failures, deterministic CA image tags, drift detection, reconciliation, and exit-code mapping.
- No public endpoint is exposed.

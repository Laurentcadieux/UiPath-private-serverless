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
- `docs/` - architecture, runbooks, and UiPath design notes
- `scripts/` - install/uninstall helpers
- `systemd/` - service unit template
- `tests/` - smoke tests and regression checks

## Usage

Bootstrap a raw Ubuntu host from the repository:

```bash
export REPO_URL="https://github.com/Laurentcadieux/UiPath-private-serverless.git"
export BRANCH="main"
export UIPATH_MACHINE_KEY="machine-template-key"
curl -fsSL "$REPO_URL/raw/$BRANCH/scripts/bootstrap-live-host.sh" | sudo -E bash
```

If this product is still inside the AI builder repository, use the product subfolder path:

```bash
export PRODUCT_SUBDIR="OUTPUT_Product"
curl -fsSL "$REPO_URL/raw/$BRANCH/OUTPUT_Product/scripts/bootstrap-live-host.sh" | sudo -E bash
```

See `docs/live-host-bootstrap.md` for the live-host runbook.

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

Check whether idle excess containers are eligible to stop:

```bash
# Report only. This never stops containers.
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml

# Stop eligible idle containers, but never below scaling.minimum_count.
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml --apply

# Run the same guard continuously every scaling.poll_interval_seconds.
uipath-runtime scale-watch --config /etc/uipath-runtime/config.yaml --apply
```

## Idle Scaling

Use the `scaling` block in `/etc/uipath-runtime/config.yaml` to define the steady-state minimum, burst ceiling, idle window, polling interval, and active-job probe:

```yaml
scaling:
  minimum_count: 1
  burst_max_count: 5
  idle_minutes_before_stop: 30
  poll_interval_seconds: 60
  state_path: "/var/lib/uipath-runtime/scaling-state.json"
  active_job_probe:
    command:
      - "/bin/sh"
      - "-lc"
      - "pgrep -af 'UiPath.Executor|UiRobot|UiPath.Robot.Executor' >/dev/null"
```

`scale-check` executes the configured probe inside every managed Robot container. Probe exit code `0` means active, `1` means idle, and any other result is treated conservatively as unknown and kept running. Idle timestamps are persisted in `state_path`, so a container is only eligible after it has been idle for the configured number of minutes.

Before turning off or shrinking a host, run:

```bash
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml
```

Only use `--apply` when you want the tool to stop excess idle containers above `minimum_count`.

## Safety Rules

- Machine keys are read from environment or root-only secret file, never from YAML.
- Machine keys are masked in output.
- The configured UiPath image must exist locally; automatic image pull is out of scope.
- Containers are managed only through `com.uipath.runtime.*` labels.
- Existing drifted containers are reported, not recreated, unless `--recreate` is supplied.
- Decreasing desired count never removes containers in MVP 1.
- Idle scaling is conservative: report-only by default, keeps `minimum_count`, and treats unknown probes as active.

## Current Status

- MVP CLI source created.
- Unit tests cover config validation, naming, secret masking, CA validation failures, deterministic CA image tags, drift detection, reconciliation, exit-code mapping, health log evidence, and idle scaling decisions.
- Live host `67.205.173.227` verified with one connected Robot, scale-up to five connected Robots, idempotent rerun, scale-down back to one, and live `scale-check`/`scale-watch` smoke tests.
- No public endpoint is exposed.

# UiPath Private Serverless

Production-oriented Python CLI for provisioning a local Ubuntu host as a private UiPath Linux Robot container runtime.

## Purpose

- Initialize Ubuntu 22.04/24.04 amd64 hosts for UiPath Linux Robot containers.
- Create deterministic local Docker containers from a preloaded UiPath Robot image.
- Pull the configured UiPath Robot image during setup init when it is missing, with an offline `IMAGE_TAR` path available.
- Connect containers to UiPath Orchestrator via machine key.
- Support configurable DNS, package feeds, shared package cache, optional private CA, labels, logs, status, and drift detection.

## Layout

- `config/` - example runtime and secret configuration
- `src/` - Python package source code
- `docs/` - architecture, runbooks, and UiPath design notes
- `scripts/` - install/uninstall helpers
- `systemd/` - service unit template
- `tests/` - smoke tests and regression checks

## Usage

From the repository root, run setup and then initialize the product:

```bash
sudo -E bash OUTPUT_Setup/install.sh
sudo -E bash OUTPUT_Setup/init-product.sh
```

Bootstrap a raw Ubuntu host from the repository:

```bash
export REPO_URL="https://github.com/Laurentcadieux/UiPath-private-serverless.git"
export BRANCH="main"
export UIPATH_MACHINE_KEY="machine-template-key"
curl -fsSL "$REPO_URL/raw/$BRANCH/OUTPUT_Setup/install.sh" | sudo -E bash
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
      - "pgrep -af 'UiPath.Executor|UiPath.Robot.Executor' >/dev/null"
```

`scale-check` executes the configured probe inside every managed Robot container. Probe exit code `0` means active, `1` means idle, and any other result is treated conservatively as unknown and kept running. Idle timestamps are persisted in `state_path`, so a container is only eligible after it has been idle for the configured number of minutes.

Before turning off or shrinking a host, run:

```bash
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml
```

Only use `--apply` when you want the tool to stop excess idle containers above `minimum_count`.

## VM Autoscaling

VM autoscaling is disabled by default and is separate from local container idle scaling.
When enabled, `autoscale-check` monitors local Robot container usage and decides whether
to add or remove a tagged cloud VM. It is report-only unless `--apply` is supplied.

```yaml
autoscaling:
  enabled: false
  provider: "digitalocean"
  min_vms: 1
  max_vms: 3
  scale_up_active_ratio: 0.8
  scale_down_active_ratio: 0.1
  scale_down_idle_minutes: 30
  protected_vm_names: []
  digitalocean:
    token_env: "DIGITALOCEAN_TOKEN"
    region: "nyc1"
    size: "s-2vcpu-2gb"
    image: "ubuntu-24-04-x64"
    ssh_keys: []
    tags:
      - "uipath-runtime"
    name_prefix: "uipath-runtime-worker"
    user_data_path: null
```

Dry-run a VM autoscaling decision:

```bash
uipath-runtime autoscale-check --config /etc/uipath-runtime/config.yaml
```

Apply one decision:

```bash
export DIGITALOCEAN_TOKEN="dop_v1_..."
uipath-runtime autoscale-check --config /etc/uipath-runtime/config.yaml --apply
```

Run continuously:

```bash
uipath-runtime autoscale-watch --config /etc/uipath-runtime/config.yaml --apply
```

The DigitalOcean provider lists Droplets by the first configured tag, creates workers
with the configured region/size/image/SSH keys/user data, and deletes only matching
managed VMs that are not in `protected_vm_names`.

## Safety Rules

- Machine keys are read from environment or root-only secret file, never from YAML.
- Machine keys are masked in output.
- `init-product.sh` pulls the configured image when it is missing unless `PULL_IMAGE=0` is set.
- Containers are managed only through `com.uipath.runtime.*` labels.
- Existing drifted containers are reported, not recreated, unless `--recreate` is supplied.
- Decreasing desired count never removes containers in MVP 1.
- Idle scaling is conservative: report-only by default, keeps `minimum_count`, and treats unknown probes as active.
- VM autoscaling is off by default, report-only without `--apply`, and needs a cloud API token before changing VMs.

## Current Status

- MVP CLI source created.
- Unit tests cover config validation, naming, secret masking, CA validation failures, deterministic CA image tags, drift detection, reconciliation, exit-code mapping, health log evidence, idle scaling decisions, and VM autoscaling decisions.
- Live host `67.205.173.227` verified with one connected Robot, scale-up to five connected Robots, idempotent rerun, scale-down back to one, and live `scale-check`/`scale-watch` smoke tests.
- No public endpoint is exposed.

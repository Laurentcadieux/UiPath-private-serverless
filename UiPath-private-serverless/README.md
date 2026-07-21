# UiPath Private Serverless

Deploy a private UiPath Linux Robot runtime on an Ubuntu VM using Docker.

The goal is a simple, repeatable path from a fresh VM to a connected UiPath Robot:

```bash
git clone https://github.com/Laurentcadieux/UiPath-private-serverless.git
cd UiPath-private-serverless
sudo -E bash OUTPUT_Setup/install.sh
sudo -E bash OUTPUT_Setup/init-product.sh
```

## What This Does

- Installs required Ubuntu packages, Docker, Python tooling, and the product CLI.
- Pulls or loads the configured UiPath Robot runtime image.
- Creates one or more managed UiPath Robot Docker containers.
- Connects the Robot container to UiPath Orchestrator with a machine key.
- Stores secrets outside YAML in a root-only `/etc/uipath-runtime/secrets.env` file.
- Provides status, recreate, idle container scale-down, and optional VM autoscaling commands.

## Repository Layout

```text
UiPath-private-serverless/
├── README.md
├── OUTPUT_Setup/
│   ├── README.md
│   ├── install.sh
│   └── init-product.sh
└── OUTPUT_Product/
    ├── README.md
    ├── README-LIVE-HOST.md
    ├── config/
    ├── docs/
    ├── scripts/
    ├── src/
    ├── systemd/
    └── tests/
```

- `OUTPUT_Setup/` is the host setup and product initialization layer.
- `OUTPUT_Product/` is the deployable Python CLI, product config, docs, source, and tests.

## Fresh VM Quick Start

Use Ubuntu 22.04 or 24.04 on amd64.

```bash
git clone https://github.com/Laurentcadieux/UiPath-private-serverless.git
cd UiPath-private-serverless
sudo -E bash OUTPUT_Setup/install.sh
```

Edit the active runtime config:

```bash
sudo nano /etc/uipath-runtime/config.yaml
```

Set the Orchestrator URL to the full tenant/service URL:

```yaml
orchestrator:
  url: "https://cloud.uipath.com/<account>/<tenant>/"
  authentication:
    type: "machine_key"
    machine_key_env: "UIPATH_MACHINE_KEY"
```

Store the machine key in the root-only secret file:

```bash
sudo mkdir -p /etc/uipath-runtime
sudo bash -c 'umask 077; cat > /etc/uipath-runtime/secrets.env' <<'EOF'
UIPATH_MACHINE_KEY=<real-machine-key>
EOF
sudo chown root:root /etc/uipath-runtime/secrets.env
sudo chmod 600 /etc/uipath-runtime/secrets.env
```

Initialize the product:

```bash
sudo CONFIG_PATH=/etc/uipath-runtime/config.yaml bash OUTPUT_Setup/init-product.sh
```

Check status:

```bash
uipath-runtime status --config /etc/uipath-runtime/config.yaml
```

Expected healthy status:

```text
uipath-robot-001 running connected ...
```

## Image Handling

By default, `OUTPUT_Setup/init-product.sh` pulls the configured Robot image if it is missing locally:

```yaml
runtime:
  image: "uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10"
```

Offline install from a tar archive:

```bash
IMAGE_TAR=/path/to/uipath-robot-image.tar \
  sudo CONFIG_PATH=/etc/uipath-runtime/config.yaml bash OUTPUT_Setup/init-product.sh
```

Disable automatic pull:

```bash
PULL_IMAGE=0 sudo CONFIG_PATH=/etc/uipath-runtime/config.yaml bash OUTPUT_Setup/init-product.sh
```

## Recreate After Config Changes

Container environment values are fixed when the container is created. After changing `/etc/uipath-runtime/config.yaml`, recreate the managed containers:

```bash
RECREATE=1 sudo CONFIG_PATH=/etc/uipath-runtime/config.yaml bash OUTPUT_Setup/init-product.sh
```

## Container Count

For a small 2 vCPU / 2 GB test VM, start with one Robot container:

```yaml
runtime:
  count: 1
scaling:
  minimum_count: 1
  burst_max_count: 1
```

To create two containers on a larger VM:

```yaml
runtime:
  count: 2
scaling:
  minimum_count: 1
  burst_max_count: 2
```

Then recreate:

```bash
RECREATE=1 COUNT=2 sudo CONFIG_PATH=/etc/uipath-runtime/config.yaml bash OUTPUT_Setup/init-product.sh
```

## Local Container Idle Scaling

Container scaling is local to one VM. It does not create cloud VMs.

Dry-run idle scale-down decisions:

```bash
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml
```

Stop eligible idle excess containers:

```bash
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml --apply
```

Run continuously:

```bash
uipath-runtime scale-watch --config /etc/uipath-runtime/config.yaml --apply
```

The active-job probe watches executor processes and avoids matching the always-running Robot service:

```yaml
scaling:
  active_job_probe:
    command:
      - "/bin/sh"
      - "-lc"
      - "pgrep -af '[U]iPath.Executor|[U]iPath.Robot.Executor' >/dev/null"
```

## Optional VM Autoscaling

VM autoscaling is available but disabled by default. It is dry-run unless `--apply` is used.

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

Dry-run VM autoscaling:

```bash
uipath-runtime autoscale-check --config /etc/uipath-runtime/config.yaml
```

Apply one scale decision:

```bash
export DIGITALOCEAN_TOKEN="dop_v1_..."
uipath-runtime autoscale-check --config /etc/uipath-runtime/config.yaml --apply
```

Run continuously:

```bash
uipath-runtime autoscale-watch --config /etc/uipath-runtime/config.yaml --apply
```

Safety defaults:

- `autoscaling.enabled` is `false` by default.
- No VM is created or deleted unless `--apply` is passed.
- DigitalOcean calls require `DIGITALOCEAN_TOKEN`.
- Scale-down only targets matching managed VMs and skips names in `protected_vm_names`.

## Useful Commands

Show CLI help:

```bash
uipath-runtime --help
```

Show Robot status:

```bash
uipath-runtime status --config /etc/uipath-runtime/config.yaml
```

Inspect the Docker container:

```bash
docker ps --filter "label=com.uipath.runtime.managed=true"
docker logs --tail 100 uipath-robot-001
```

Verify image availability:

```bash
docker image inspect uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10 >/dev/null && echo image-ready
```

## Development And Tests

Run product tests:

```bash
cd OUTPUT_Product
python3 tests/run_unit.py
```

Install the CLI from source:

```bash
cd OUTPUT_Product
bash scripts/install.sh
uipath-runtime --help
```

## Troubleshooting

`Machine key not found in environment variable ...`

- `orchestrator.authentication.machine_key_env` must be the variable name, usually `UIPATH_MACHINE_KEY`.
- The real key belongs in `/etc/uipath-runtime/secrets.env`.

`Orchestrator connection: RUNNING_NOT_CONFIRMED`

- Check that `orchestrator.url` includes the full UiPath Cloud tenant path, for example `https://cloud.uipath.com/<account>/<tenant>/`.
- Recreate containers after URL changes with `RECREATE=1`.
- Check container logs for `Successfully connected to Orchestrator` and `HeartbeatV2 Status:OK`.

`Configured image is missing locally`

- Let init pull the image, or pass `IMAGE_TAR=/path/to/image.tar`.

`autoscale-check` says autoscaling is disabled

- This is expected unless `autoscaling.enabled: true` is set in `/etc/uipath-runtime/config.yaml`.

## Safety Notes

- Do not put machine keys directly in YAML.
- Keep `/etc/uipath-runtime/secrets.env` owned by root and mode `600`.
- Start with `runtime.count: 1` on small test VMs.
- Use dry-run commands before any `--apply`.
- VM autoscaling can create/delete cloud resources and may incur cost when enabled.

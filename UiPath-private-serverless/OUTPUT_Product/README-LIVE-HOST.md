# Live Host Usage

This guide bootstraps an Ubuntu 24.04 amd64 host as a local UiPath Linux Robot container host.

## Tested Live Command Flow

Run as root on the target host.

```bash
apt-get update
apt-get install -y ca-certificates curl git gnupg openssl python3 python3-venv docker.io
systemctl enable --now docker
```

Clone the repository:

```bash
rm -rf /opt/uipath-private-serverless-repo
git clone --depth 1 https://github.com/Laurentcadieux/UiPath-private-serverless.git /opt/uipath-private-serverless-repo
cd /opt/uipath-private-serverless-repo/OUTPUT_Product
```

Install the CLI:

```bash
bash scripts/install.sh
uipath-runtime --help
```

Prepare configuration:

```bash
mkdir -p /etc/uipath-runtime
cp config/config.example.yaml /etc/uipath-runtime/config.yaml
nano /etc/uipath-runtime/config.yaml
```

Required values to review:

- `orchestrator.url`
- `runtime.image`
- `docker.dns`
- optional `tls.ca_certificate`

Store the machine key outside YAML:

```bash
cat >/etc/uipath-runtime/secrets.env <<'EOF'
UIPATH_MACHINE_KEY=replace-with-machine-template-key
EOF
chown root:root /etc/uipath-runtime/secrets.env
chmod 600 /etc/uipath-runtime/secrets.env
```

Pull the public UiPath Robot image manually:

```bash
docker pull uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10
```

Initialize one Robot container:

```bash
uipath-runtime init --config /etc/uipath-runtime/config.yaml --count 1 --auto-install-host-deps
```

Check status:

```bash
uipath-runtime status --config /etc/uipath-runtime/config.yaml
docker ps --filter 'label=com.uipath.runtime.managed=true'
```

Expected healthy result:

```text
uipath-robot-001 running connected uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10
```

## Notes

- The MVP does not auto-pull the UiPath image during `init`; pull or load it first.
- `CONNECTED` is reported only when logs show successful Orchestrator connection or heartbeat evidence.
- Start with `--count 1` on a new host, then scale after verifying memory, disk, and Orchestrator behavior.
- Use `--recreate` only when intentionally replacing drifted containers.

## Idle Scale Check

The scaler is report-only by default. It runs a configurable command inside each managed container to decide whether a Robot appears active.

Config:

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

Check without stopping anything:

```bash
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml
```

Use this as the pre-shutdown check before turning off or shrinking a host. Review `ACTIVE`, `IDLE_MIN`, and `ACTION`; do not shut down the host while any required container is active.

Stop only idle excess containers above `minimum_count` after the configured idle window:

```bash
uipath-runtime scale-check --config /etc/uipath-runtime/config.yaml --apply
```

Run continuously every `poll_interval_seconds`:

```bash
uipath-runtime scale-watch --config /etc/uipath-runtime/config.yaml --apply
```

For a bounded smoke test:

```bash
uipath-runtime scale-watch --config /etc/uipath-runtime/config.yaml --iterations 1
```

Output fields:

- `ACTIVE`: `active`, `idle`, or `unknown`.
- `IDLE_MIN`: minutes since the last active probe for that container.
- `ELIGIBLE`: whether the container has passed the idle window.
- `ACTION`: `keep`, `stop`, or `stopped`.

Unknown probe results are kept running. This avoids stopping a Robot when the tool cannot prove it is idle.

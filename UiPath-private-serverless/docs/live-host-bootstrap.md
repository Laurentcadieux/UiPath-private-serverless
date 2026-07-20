# Live Host Bootstrap

Target host tested on 2026-07-20:

- Ubuntu 24.04 amd64
- 1 CPU
- 458 MiB RAM
- Docker not installed initially

The host is supported by OS and architecture, but memory is very small for UiPath Robot containers.

## One-Time Bootstrap From Repo

Run as root on the Ubuntu host:

```bash
export REPO_URL="https://github.com/Laurentcadieux/UiPath-private-serverless.git"
export BRANCH="main"
export UIPATH_MACHINE_KEY="machine-template-key"
curl -fsSL "$REPO_URL/raw/$BRANCH/scripts/bootstrap-live-host.sh" | bash
```

If the repository is private, clone with a deploy key or run the script from an authenticated checkout instead:

```bash
git clone git@github.com:Laurentcadieux/UiPath-private-serverless.git /opt/UiPath-private-serverless
cd /opt/UiPath-private-serverless
UIPATH_MACHINE_KEY="machine-template-key" bash scripts/bootstrap-live-host.sh
```

## Configure

Edit:

```bash
nano /etc/uipath-runtime/config.yaml
```

Required live values:

- `orchestrator.url`
- `runtime.image`
- `docker.dns`
- optional `tls.ca_certificate`

The UiPath machine key is stored separately in:

```bash
/etc/uipath-runtime/secrets.env
```

The secret file must stay root-only:

```bash
chown root:root /etc/uipath-runtime/secrets.env
chmod 600 /etc/uipath-runtime/secrets.env
```

## Load UiPath Image

The MVP does not pull the UiPath Robot image. Load it first:

```bash
docker load --input /path/to/uipath-runtime.tar
docker image inspect uipathprod.azurecr.io/robot/uiautomation-runtime:latest24.10
```

## Initialize

For one test container:

```bash
uipath-runtime init --config /etc/uipath-runtime/config.yaml --count 1 --auto-install-host-deps
```

For ten containers:

```bash
uipath-runtime init --config /etc/uipath-runtime/config.yaml --count 10 --auto-install-host-deps
```

On the current 512 MB host, start with `--count 1`. Larger counts need a bigger host.

## Status

```bash
uipath-runtime status --config /etc/uipath-runtime/config.yaml
```

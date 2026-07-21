# OUTPUT_Setup

Initial setup layer for installing host dependencies, installing the product, and starting initialization.

## Goal

Clone the repository, run setup, then initialize `OUTPUT_Product`.

```bash
git clone https://github.com/Laurentcadieux/UiPath-private-serverless.git
cd UiPath-private-serverless
sudo -E bash OUTPUT_Setup/install.sh
sudo -E bash OUTPUT_Setup/init-product.sh
```

`init-product.sh` checks that the configured UiPath Robot image exists locally before it starts containers. If the image is missing, it pulls the configured image by default.

## One-Step Host Bootstrap

Use this when starting from a fresh Ubuntu host:

```bash
export REPO_URL="https://github.com/Laurentcadieux/UiPath-private-serverless.git"
export BRANCH="main"
export UIPATH_MACHINE_KEY="machine-template-key"
curl -fsSL "$REPO_URL/raw/$BRANCH/OUTPUT_Setup/install.sh" | sudo -E bash
```

To install and immediately run initialization:

```bash
export RUN_INIT=1
export COUNT=10
curl -fsSL "$REPO_URL/raw/$BRANCH/OUTPUT_Setup/install.sh" | sudo -E bash
```

## Image Step

The setup installs Docker and the product CLI. `init-product.sh` pulls the configured UiPath Robot image when it is missing:

```bash
sudo -E bash OUTPUT_Setup/init-product.sh
```

If the VM has no registry access, pass a local image archive instead:

```bash
IMAGE_TAR=/path/to/uipath-robot-image.tar sudo -E bash OUTPUT_Setup/init-product.sh
```

To require a preloaded image and fail instead of pulling:

```bash
PULL_IMAGE=0 sudo -E bash OUTPUT_Setup/init-product.sh
```

## Environment

- `REPO_URL` - repository to clone when setup is run from a raw URL
- `BRANCH` - branch to clone or update; default: `main`
- `INSTALL_DIR` - clone/update target; default: `/opt/UiPath-private-serverless`
- `PRODUCT_SUBDIR` - product folder; default: `OUTPUT_Product`
- `CONFIG_PATH` - runtime config path; default: `/etc/uipath-runtime/config.yaml`
- `SECRETS_PATH` - root-only machine-key env file; default: `/etc/uipath-runtime/secrets.env`
- `UIPATH_MACHINE_KEY` - optional machine key written to `SECRETS_PATH`
- `COUNT` - container count for initialization; default: `1`
- `RUN_INIT=1` - run `init-product.sh` after install
- `IMAGE_TAR` - optional local UiPath Robot image archive used by `init-product.sh`
- `PULL_IMAGE` - pull the configured Robot image when missing; default: `1`

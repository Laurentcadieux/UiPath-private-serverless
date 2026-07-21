# UiPath Private Serverless Builder

This repository is the AI-assisted build workspace for the UiPath Linux Robot container provisioner.

The root output is split into two folders:

```text
OUTPUT_Setup/
OUTPUT_Product/
```

- `OUTPUT_Setup/` prepares a host after cloning the repo.
- `OUTPUT_Product/` contains the deployable tool, product docs, source, config, and tests.

The intended first-run flow is:

```bash
git clone https://github.com/Laurentcadieux/UiPath-private-serverless.git
cd UiPath-private-serverless
sudo -E bash OUTPUT_Setup/install.sh
sudo -E bash OUTPUT_Setup/init-product.sh
```

## Setup Folder

```text
OUTPUT_Setup/
├── README.md
├── install.sh
└── init-product.sh
```

- `install.sh` installs Ubuntu dependencies, Docker, Python tooling, and the `OUTPUT_Product` CLI.
- `init-product.sh` runs `uipath-runtime init` after config and secrets are prepared.

Fresh host bootstrap:

```bash
export REPO_URL="https://github.com/Laurentcadieux/UiPath-private-serverless.git"
export BRANCH="main"
export UIPATH_MACHINE_KEY="machine-template-key"
curl -fsSL "$REPO_URL/raw/$BRANCH/OUTPUT_Setup/install.sh" | sudo -E bash
```

Install and initialize in one pass:

```bash
export RUN_INIT=1
export COUNT=10
curl -fsSL "$REPO_URL/raw/$BRANCH/OUTPUT_Setup/install.sh" | sudo -E bash
```

## Product Folder

```text
OUTPUT_Product/
├── README.md
├── README-LIVE-HOST.md
├── config/
├── docs/
├── scripts/
├── src/
├── systemd/
└── tests/
```

Run product tests from the output folder:

```bash
cd OUTPUT_Product
python3 tests/run_unit.py
```

Install the product CLI directly from the product folder:

```bash
cd OUTPUT_Product
bash scripts/install.sh
uipath-runtime --help
```

## Local Project-Only Files

- `AGENTS.md` - local agent guidance for this builder workspace.
- `AI_Project/` - local AI/testing support files and archived subtree guidance that are not part of the product output.
- `.secrets/` - local secret material; ignored and never copied to product repos.
- `.omx/` - local OMX workflow state.

## Publish Product Snapshot

The public-facing repository shape should include `OUTPUT_Setup/`, `OUTPUT_Product/`, and the root README.

Do not copy `.secrets/`, `.omx/`, `AI_Project/`, or local workspace files into a public product snapshot.

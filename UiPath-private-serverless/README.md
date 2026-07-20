# UiPath Private Serverless Builder

This repository is the AI-assisted build workspace for the UiPath Linux Robot container provisioner.

The deployable public product is kept in:

```text
OUTPUT_Product/
```

Use `OUTPUT_Product/` as the source for any separate public-facing product repository. The workspace root can keep AI project files, local notes, live-test artifacts, and build workflow context that should not be copied into the public product.

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

## Local Project-Only Files

- `AGENTS.md` - local agent guidance for this builder workspace.
- `AI_Project/` - local AI/testing support files and archived subtree guidance that are not part of the product output.
- `.secrets/` - local secret material; ignored and never copied to product repos.
- `.omx/` - local OMX workflow state.

## Build And Test Product

Run product tests from the output folder:

```bash
cd OUTPUT_Product
python3 tests/run_unit.py
```

Install the product CLI from the output folder:

```bash
cd OUTPUT_Product
bash scripts/install.sh
uipath-runtime --help
```

## Publish Product Snapshot

To refresh a separate public product repository, copy the contents of `OUTPUT_Product/` into that repository root, then commit there:

```bash
AI_Project/sync-output-product.sh /path/to/public-product-repo
```

Do not copy `.secrets/`, `.omx/`, `AI_Project/`, or workspace-level files into the public product repository.

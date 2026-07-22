# UiPath Private Serverless Workspace

This repository contains two things:

- the deployable UiPath private Robot runtime project
- the agent/workspace context used to design, test, document, and maintain that project

If you only want to install the runtime on a VM, start here:

[UiPath-private-serverless/README.md](UiPath-private-serverless/README.md)

## Main Project

`UiPath-private-serverless/` is the actual product workspace. It contains the setup scripts, Python product code, configuration examples, docs, and tests for running UiPath Linux Robot containers on a private Ubuntu VM.

The important split is:

- `UiPath-private-serverless/OUTPUT_Setup/` gets the operating system ready to host the product. It installs host dependencies, Docker, Python tooling, product files, config defaults, and runs product initialization.
- `UiPath-private-serverless/OUTPUT_Product/` is the product itself. It contains the `uipath-runtime` Python CLI, runtime config model, Docker/container reconciliation logic, status checks, idle scale-down, optional VM autoscaling, docs, and tests.

Fresh VM flow:

```bash
git clone https://github.com/Laurentcadieux/UiPath-private-serverless.git
cd UiPath-private-serverless/UiPath-private-serverless
sudo -E bash OUTPUT_Setup/install.sh
sudo -E bash OUTPUT_Setup/init-product.sh
```

## Repository Layout

```text
.
├── README.md
├── .omx/
├── memory/
├── skills/
├── AGENTS.md
├── IDENTITY.md
├── USER.md
└── UiPath-private-serverless/
    ├── README.md
    ├── AGENTS.md
    ├── AI_Project/
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

## Agent And Workspace Support

These folders are not the runtime product. They exist so the repo can preserve development context and repeatable agent workflows:

- `.omx/` stores oh-my-codex workspace/runtime metadata such as setup scope and HUD configuration.
- `memory/` stores durable notes from prior work sessions.
- `skills/` stores reusable OpenClaw/OMX skills and workflow instructions used by the coding agent.
- `AGENTS.md` contains repository-level agent instructions.
- `IDENTITY.md`, `USER.md`, `SOUL.md`, and `TOOLS.md` are OpenClaw workspace files for the local assistant environment.
- `UiPath-private-serverless/AI_Project/` contains project-side agent guidance and synchronization helpers used while building the output product.

The public runtime documentation should live under `UiPath-private-serverless/`, especially `OUTPUT_Setup/` and `OUTPUT_Product/`. The root README is intentionally broader because the repository also carries the agent workspace that produced the runtime.

## Product Summary

The runtime turns an Ubuntu 22.04 or 24.04 amd64 VM into a managed UiPath Linux Robot host using Docker.

Current product capabilities:

- install host dependencies and Docker
- pull or load the configured UiPath Robot runtime image
- create managed UiPath Robot containers
- connect containers to UiPath Orchestrator with a machine key
- keep machine keys out of YAML by using a root-only secrets file
- report runtime/container status
- recreate containers after config changes
- scale down idle excess local containers
- optionally monitor VM usage and create/delete DigitalOcean workers when autoscaling is enabled and `--apply` is used

Autoscaling is off by default and dry-run by default.

## Where To Work

- To deploy or operate the runtime, use [UiPath-private-serverless/README.md](UiPath-private-serverless/README.md).
- To understand host bootstrap scripts, use [UiPath-private-serverless/OUTPUT_Setup/README.md](UiPath-private-serverless/OUTPUT_Setup/README.md).
- To understand the product CLI and tests, use [UiPath-private-serverless/OUTPUT_Product/README.md](UiPath-private-serverless/OUTPUT_Product/README.md).

Run product tests from the product folder:

```bash
cd UiPath-private-serverless/OUTPUT_Product
python3 tests/run_unit.py
```

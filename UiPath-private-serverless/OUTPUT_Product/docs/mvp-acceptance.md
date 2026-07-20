# MVP Acceptance Map

This project implements the first-pass MVP as a Python CLI named `uipath-runtime`.

## Implemented

- Ubuntu 22.04/24.04 amd64 validation.
- Config file parsing and strict validation.
- Secure machine-key resolution from environment or `/etc/uipath-runtime/secrets.env`.
- Secret masking.
- Docker SDK wrapper with local-image inspection and no automatic pull.
- Optional `--image-tar` load followed by configured-image verification.
- Dedicated Docker bridge network reconciliation.
- Configurable DNS on managed containers.
- NuGet package-source generation for UiPath official feed.
- Shared host package cache mount.
- Optional PEM CA validation, fingerprinting, host install, and deterministic derived-image tag/build.
- Deterministic container naming.
- Managed labels for isolation from unrelated Docker containers.
- Idempotent create/start/unchanged reconciliation.
- Drift detection without automatic recreation.
- `init` and `status` commands.
- Structured JSON provisioner logging.
- Deterministic exit-code mapping.

## Partially Implemented

- Container Orchestrator connection health is conservative. It reports `RUNNING_NOT_CONFIRMED` unless log evidence indicates a successful connection.
- Temporary-container DNS/TLS validation hooks are represented by host validation and Docker API structure; full integration tests require Docker and a local test image.

## Explicitly Not Implemented

- Kubernetes.
- Multi-host provisioning.
- Dynamic autoscaling.
- Automatic UiPath image download.
- Orchestrator API machine/folder/user provisioning.
- Automatic count reduction/removal.
- Insecure TLS bypass.

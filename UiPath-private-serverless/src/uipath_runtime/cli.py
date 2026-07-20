from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import DEFAULT_CONFIG_PATH, load_config, resolve_secrets
from .derived_image import DerivedImageManager
from .docker_manager import DockerManager
from .exceptions import ExitCode, ImageNotFoundError, RuntimeProvisionerError
from .host import HostManager
from .logging_config import configure_logging
from .network import NetworkValidator
from .packages import ensure_nuget_config
from .reconciliation import Reconciler
from .scaling import ScaleChecker
from .tls import CertificateManager


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            return init_command(args)
        if args.command == "status":
            return status_command(args)
        if args.command == "scale-check":
            return scale_check_command(args)
        if args.command == "scale-watch":
            return scale_watch_command(args)
        parser.print_help()
        return int(ExitCode.INVALID_CONFIGURATION)
    except RuntimeProvisionerError as exc:
        print(f"ERROR: {exc.message}", file=sys.stderr)
        if exc.details:
            print(exc.details, file=sys.stderr)
        return int(exc.exit_code)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return int(ExitCode.GENERAL_FAILURE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="uipath-runtime")
    sub = parser.add_subparsers(dest="command")
    init = sub.add_parser("init")
    init.add_argument("target", nargs="?", default="uipath-robot")
    init.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG_PATH)
    init.add_argument("--count", type=int)
    init.add_argument("--image-tar", type=Path)
    init.add_argument("--recreate", action="store_true")
    init.add_argument("--auto-install-host-deps", action="store_true")
    init.add_argument("--skip-host-prep", action="store_true", help="For tests/dev only; skips root and system mutation checks")
    status = sub.add_parser("status")
    status.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG_PATH)
    scale_check = sub.add_parser("scale-check")
    scale_check.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG_PATH)
    scale_check.add_argument("--apply", action="store_true", help="Stop eligible idle excess containers")
    scale_watch = sub.add_parser("scale-watch")
    scale_watch.add_argument("--config", "-c", type=Path, default=DEFAULT_CONFIG_PATH)
    scale_watch.add_argument("--apply", action="store_true", help="Stop eligible idle excess containers")
    scale_watch.add_argument("--iterations", type=int, help="Run a bounded number of checks; omit to run until interrupted")
    return parser


def init_command(args) -> int:
    config = load_config(args.config, count_override=args.count)
    logger = configure_logging(config.logs.host_path / "provisioner.log")
    secrets = resolve_secrets(config)

    host = HostManager()
    if not args.skip_host_prep:
        host.ensure_root()
        host.validate_platform()
        host.ensure_dependencies(auto_install=args.auto_install_host_deps)
        host.prepare_directories(config)
        host.ensure_docker_service()

    docker_manager = DockerManager()
    if args.image_tar:
        docker_manager.load_image_archive(args.image_tar)
    image_meta = docker_manager.image_metadata(config.runtime.image)
    docker_manager.ensure_network(config.docker.network_name)
    ensure_nuget_config(config.packages)

    ca_status = "NOT CONFIGURED"
    ca_fingerprint = None
    effective_image = config.runtime.image
    if config.tls.ca_certificate is not None:
        cert_manager = CertificateManager()
        cert = cert_manager.validate_certificate(config.tls.ca_certificate)
        ca_fingerprint = cert.fingerprint
        ca_status = "LOADED"
        if config.tls.install_on_host and not args.skip_host_prep:
            cert_manager.install_host_certificate(cert)
        effective_image = DerivedImageManager().ensure_ca_image(
            docker_manager,
            config.runtime.image,
            image_meta.image_id,
            cert,
            config.tls.derived_image_prefix,
        )

    validator = NetworkValidator()
    hostname, port = validator.endpoint_parts(config.orchestrator.url)
    validator.resolve_host(hostname)
    validator.test_tcp_connection(hostname, port, config.health.connection_timeout_seconds)
    validator.test_tls_connection(config.orchestrator.url, config.health.connection_timeout_seconds)

    specs = Reconciler().build_specs(
        config,
        secrets,
        effective_image=effective_image,
        base_image=config.runtime.image,
        ca_fingerprint=ca_fingerprint,
    )
    report = Reconciler().reconcile(docker_manager, specs, recreate=args.recreate)
    logger.info("initialization completed", extra={"operation": "init", "result": "success"})

    print("Host validation: PASSED")
    print("Docker service: RUNNING")
    print("UiPath image: FOUND LOCALLY")
    print(f"Custom CA certificate: {ca_status}")
    print(f"Machine key: {secrets.masked_machine_key}")
    print(f"Requested containers: {report.requested}")
    print(f"Created containers: {report.created}")
    print(f"Running containers: {report.running}")
    print("Orchestrator connection: RUNNING_NOT_CONFIRMED")
    print("Result: SUCCESS" if report.failed == 0 else "Result: PARTIAL_FAILURE")
    return int(ExitCode.SUCCESS if report.failed == 0 else ExitCode.PARTIAL_INITIALIZATION)


def status_command(args) -> int:
    config = load_config(args.config)
    try:
        docker_manager = DockerManager()
    except RuntimeProvisionerError as exc:
        raise exc
    if not docker_manager.image_exists(config.runtime.image):
        raise ImageNotFoundError(f"Configured image is missing locally: {config.runtime.image}")
    statuses = docker_manager.status()
    print("NAME STATE HEALTH IMAGE")
    for status in statuses:
        print(f"{status.name} {status.docker_state} {status.health.value.lower()} {status.image}")
    print(f"Summary: Existing: {len(statuses)} Running: {sum(1 for item in statuses if item.docker_state == 'running')}")
    print(f"Custom CA: {'configured' if config.tls.ca_certificate else 'not configured'}")
    print(f"Effective image: {config.runtime.image}")
    return int(ExitCode.SUCCESS)


def scale_check_command(args) -> int:
    config = load_config(args.config)
    docker_manager = DockerManager()
    decisions = ScaleChecker().check(config, docker_manager, apply=args.apply)
    _print_scale_decisions(config, decisions, applied=args.apply)
    return int(ExitCode.SUCCESS)


def scale_watch_command(args) -> int:
    config = load_config(args.config)
    docker_manager = DockerManager()
    iterations = 0
    while True:
        decisions = ScaleChecker().check(config, docker_manager, apply=args.apply)
        _print_scale_decisions(config, decisions, applied=args.apply)
        iterations += 1
        if args.iterations is not None and iterations >= args.iterations:
            return int(ExitCode.SUCCESS)
        time.sleep(config.scaling.poll_interval_seconds)


def _print_scale_decisions(config, decisions, *, applied: bool) -> None:
    print("NAME STATE HEALTH ACTIVE IDLE_MIN ELIGIBLE ACTION")
    for decision in decisions:
        print(
            f"{decision.name} {decision.docker_state} {decision.health.value.lower()} "
            f"{decision.active_state} {decision.idle_minutes:.1f} "
            f"{str(decision.eligible_to_stop).lower()} {decision.action}"
        )
    print(f"Minimum: {config.scaling.minimum_count}")
    print(f"Burst maximum: {config.scaling.burst_max_count}")
    print(f"Idle minutes before stop: {config.scaling.idle_minutes_before_stop}")
    print(f"Poll interval seconds: {config.scaling.poll_interval_seconds}")
    print(f"Applied: {str(applied).lower()}")


if __name__ == "__main__":
    raise SystemExit(main())

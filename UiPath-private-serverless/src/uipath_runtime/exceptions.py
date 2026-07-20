from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_FAILURE = 1
    INVALID_CONFIGURATION = 2
    UNSUPPORTED_HOST = 3
    DOCKER_UNAVAILABLE = 4
    IMAGE_NOT_FOUND = 5
    DNS_FAILURE = 6
    TCP_FAILURE = 7
    TLS_FAILURE = 8
    ORCHESTRATOR_CONNECTION_FAILURE = 9
    PARTIAL_INITIALIZATION = 10
    INVALID_CA_CERTIFICATE = 11
    DERIVED_IMAGE_BUILD_FAILURE = 12
    PACKAGE_CONFIGURATION_FAILURE = 13
    CONFIGURATION_DRIFT = 14


class RuntimeProvisionerError(Exception):
    exit_code = ExitCode.GENERAL_FAILURE

    def __init__(self, message: str, *, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidConfigurationError(RuntimeProvisionerError):
    exit_code = ExitCode.INVALID_CONFIGURATION


class UnsupportedHostError(RuntimeProvisionerError):
    exit_code = ExitCode.UNSUPPORTED_HOST


class DockerUnavailableError(RuntimeProvisionerError):
    exit_code = ExitCode.DOCKER_UNAVAILABLE


class ImageNotFoundError(RuntimeProvisionerError):
    exit_code = ExitCode.IMAGE_NOT_FOUND


class NetworkValidationError(RuntimeProvisionerError):
    exit_code = ExitCode.DNS_FAILURE


class TLSValidationError(RuntimeProvisionerError):
    exit_code = ExitCode.TLS_FAILURE


class InvalidCertificateError(RuntimeProvisionerError):
    exit_code = ExitCode.INVALID_CA_CERTIFICATE


class PackageConfigurationError(RuntimeProvisionerError):
    exit_code = ExitCode.PACKAGE_CONFIGURATION_FAILURE


class DriftError(RuntimeProvisionerError):
    exit_code = ExitCode.CONFIGURATION_DRIFT

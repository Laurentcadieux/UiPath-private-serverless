from __future__ import annotations


def instance_id(index: int) -> str:
    if index < 1:
        raise ValueError("index must be >= 1")
    return f"{index:03d}"


def container_name(prefix: str, index: int) -> str:
    return f"{prefix}-{instance_id(index)}"

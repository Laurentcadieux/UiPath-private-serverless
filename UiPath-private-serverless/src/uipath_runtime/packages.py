from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from .exceptions import PackageConfigurationError
from .models import PackagesConfig


def ensure_nuget_config(config: PackagesConfig) -> Path:
    if not config.official_feed.enabled:
        raise PackageConfigurationError("The official UiPath package feed must be enabled for MVP 1.")
    if not config.nuget_config_path.is_absolute() or not config.cache_path.is_absolute():
        raise PackageConfigurationError("Package paths must be absolute.")
    config.nuget_config_path.parent.mkdir(parents=True, exist_ok=True)
    config.cache_path.mkdir(parents=True, exist_ok=True)
    content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<configuration>\n"
        "  <packageSources>\n"
        "    <clear />\n"
        f'    <add key="{escape(config.official_feed.name)}" value="{escape(config.official_feed.url)}" protocolVersion="3" />\n'
        "  </packageSources>\n"
        "</configuration>\n"
    )
    if not config.nuget_config_path.exists() or config.nuget_config_path.read_text(encoding="utf-8") != content:
        config.nuget_config_path.write_text(content, encoding="utf-8")
    return config.nuget_config_path

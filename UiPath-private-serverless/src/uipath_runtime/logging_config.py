from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "severity": record.levelname,
            "message": record.getMessage(),
        }
        for key in ("operation", "container_name", "instance_number", "result", "error_code"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, sort_keys=True)


def configure_logging(log_path: Path | None) -> logging.Logger:
    logger = logging.getLogger("uipath_runtime")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler: logging.Handler
    if log_path:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(log_path, encoding="utf-8")
        except PermissionError:
            handler = logging.StreamHandler()
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger

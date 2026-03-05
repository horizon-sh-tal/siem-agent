"""Configuration loading and validation utilities."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigError(ValueError):
    """Raised when configuration is invalid."""


REQUIRED_TOP_LEVEL_KEYS = {
    "machine_id",
    "machine_type",
    "kafka_broker",
    "log_collection",
    "encryption",
    "resilience",
}


def load_config(path: str) -> Dict[str, Any]:
    """Load and validate a JSON configuration file."""
    if not os.path.exists(path):
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config: {exc}") from exc

    _validate_config(config)
    logger.debug("Loaded config for %s", config.get("machine_id"))
    return config


def _validate_config(config: Dict[str, Any]) -> None:
    """Validate required keys and basic types."""
    missing = REQUIRED_TOP_LEVEL_KEYS - set(config.keys())
    if missing:
        raise ConfigError(f"Missing required config keys: {sorted(missing)}")

    if not isinstance(config["log_collection"], dict):
        raise ConfigError("log_collection must be an object")
    if not isinstance(config["encryption"], dict):
        raise ConfigError("encryption must be an object")
    if not isinstance(config["resilience"], dict):
        raise ConfigError("resilience must be an object")

    if "interval_seconds" not in config["log_collection"]:
        raise ConfigError("log_collection.interval_seconds is required")
    if "logs" not in config["log_collection"]:
        raise ConfigError("log_collection.logs is required")

    if "public_key_path" not in config["encryption"]:
        raise ConfigError("encryption.public_key_path is required")

    if "checkpoint_file" not in config["resilience"]:
        raise ConfigError("resilience.checkpoint_file is required")

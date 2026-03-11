"""Machine ID resolution for SIEM agents.

Resolution order:
1. Config override  – if config.json sets machine_id to anything other than
                      "auto", use it verbatim.
2. Auto-detect      – use the system hostname, sanitised to lowercase.

To set a custom name, edit machine_id in config.json, e.g.:
    "machine_id": "kshit-windows"
"""

from __future__ import annotations

import logging
import socket

logger = logging.getLogger(__name__)

_AUTO_SENTINEL = "auto"


def resolve(config_value: str) -> str:
    """Return the effective machine ID string."""
    if config_value and config_value.strip().lower() != _AUTO_SENTINEL:
        logger.info("Machine ID from config: %s", config_value.strip())
        return config_value.strip()

    machine_id = _get_hostname().lower().replace(" ", "-")
    logger.info("Auto-detected machine ID: %s", machine_id)
    return machine_id


def _get_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "unknown-host"

"""Machine ID resolution for SIEM agents.

Resolution order:
1. Config override  – if config.json sets machine_id to anything other than
                      "auto", use it verbatim.
2. Interactive mode – if a TTY is attached, prompt for an optional label and
                      combine as  "{label}-{hostname}" (or just "{hostname}"
                      if blank).
3. Service fallback – if no TTY is available (systemd / Windows service),
                      silently use "{hostname}".
"""

from __future__ import annotations

import logging
import os
import socket
import sys

logger = logging.getLogger(__name__)

_AUTO_SENTINEL = "auto"


def resolve(config_value: str) -> str:
    """Return the effective machine ID string.

    Parameters
    ----------
    config_value:
        The raw ``machine_id`` value from ``config.json``.
        Pass ``"auto"`` (or an empty string) to trigger auto-detection.
    """
    if config_value and config_value.strip().lower() != _AUTO_SENTINEL:
        logger.debug("Machine ID from config: %s", config_value)
        return config_value.strip()

    hostname = _get_hostname()

    if _has_tty():
        label = _prompt_label(hostname)
        machine_id = f"{label}-{hostname}" if label else hostname
    else:
        logger.info(
            "No interactive TTY detected – using hostname as machine ID: %s",
            hostname,
        )
        machine_id = hostname

    # Sanitise: lowercase, replace spaces with hyphens
    machine_id = machine_id.lower().replace(" ", "-")
    logger.info("Resolved machine ID: %s", machine_id)
    return machine_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_hostname() -> str:
    try:
        return socket.gethostname()
    except Exception:
        return "unknown-host"


def _has_tty() -> bool:
    """Return True only when stdin is a real interactive terminal."""
    try:
        return os.isatty(sys.stdin.fileno())
    except (AttributeError, OSError, ValueError):
        return False


def _prompt_label(hostname: str) -> str:
    """Prompt the user for an optional label; return empty string if skipped."""
    try:
        print(f"\n[SIEM Agent] Auto-detected hostname: {hostname}")
        label = input(
            "Enter a label for this machine (leave blank to use hostname only): "
        ).strip()
        return label
    except (EOFError, OSError):
        return ""

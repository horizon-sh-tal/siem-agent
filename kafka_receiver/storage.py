"""Log storage organiser for the Kafka receiver.

Stores decrypted logs under:
    received_logs/{machine_id}/{filename}

Linux logs use standard Ubuntu filenames (single file per type):
    syslog, alternatives.log, auth.log, dpkg.log, apt/history.log, apt/term.log

Windows logs use one file per event log type:
    Security.evtx, System.evtx, Defender.evtx, etc.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Map Chatterbox log_type → Ubuntu-standard file path (relative to machine dir)
LINUX_LOG_FILENAMES: dict[str, str] = {
    "syslog": "syslog",
    "alternativelog": os.path.join("alternatives.log"),
    "authlog": "auth.log",
    "dpkglog": "dpkg.log",
    "apthistory": os.path.join("apt", "history.log"),
    "aptterm": os.path.join("apt", "term.log"),
}

# Map Chatterbox log_type → Windows Event Log file names
WINDOWS_LOG_FILENAMES: dict[str, str] = {
    "security": "Security.evtx",
    "system": "System.evtx",
    "bit": "BITS-Client.evtx",
    "applocker": "AppLocker.evtx",
    "newservice": "NewService.evtx",
    "bitlocker": "BitLocker.evtx",
    "firewall": "Firewall.evtx",
    "defender": "Defender.evtx",
    "powershell": "PowerShell.evtx",
}


class LogStorage:
    """Write decrypted log payloads to the correct folder structure."""

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir

    def store(
        self,
        machine_id: str,
        log_type: str,
        decrypted_text: str,
        timestamp_ms: int,
    ) -> None:
        """Append *decrypted_text* to the appropriate log file.

        Linux logs are stored as single files matching Ubuntu defaults.
        Windows logs are stored as single .evtx files with event JSON.
        """
        ubuntu_name = LINUX_LOG_FILENAMES.get(log_type)
        windows_name = WINDOWS_LOG_FILENAMES.get(log_type)

        if ubuntu_name is not None:
            # ---- Linux log: single file, Ubuntu naming ----
            log_file = os.path.join(self.base_dir, machine_id, ubuntu_name)
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, "a", encoding="utf-8") as handle:
                try:
                    parsed = json.loads(decrypted_text)
                    entries = parsed.get("entries", [])
                    for line in entries:
                        handle.write(line)
                        handle.write("\n")
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Fallback: write raw text if not valid JSON structure
                    handle.write(decrypted_text)
                    handle.write("\n")
        elif windows_name is not None:
            # ---- Windows log: single file, Windows naming ----
            log_file = os.path.join(self.base_dir, machine_id, windows_name)
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, "a", encoding="utf-8") as handle:
                try:
                    parsed = json.loads(decrypted_text)
                    events = parsed.get("events", [])
                    for event in events:
                        handle.write(json.dumps(event, ensure_ascii=False))
                        handle.write("\n")
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Fallback: write raw text
                    handle.write(decrypted_text)
                    handle.write("\n")
        else:
            # ---- Other: date-based files (fallback) ----
            log_dir = os.path.join(self.base_dir, machine_id, log_type)
            os.makedirs(log_dir, exist_ok=True)

            date_str = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime(
                "%Y-%m-%d"
            )
            log_file = os.path.join(log_dir, f"{date_str}.log")

            with open(log_file, "a", encoding="utf-8") as handle:
                try:
                    parsed = json.loads(decrypted_text)
                    entries = parsed.get("entries", parsed.get("events", []))
                    for line in entries:
                        if isinstance(line, dict):
                            handle.write(json.dumps(line, ensure_ascii=False))
                        else:
                            handle.write(str(line))
                        handle.write("\n")
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Fallback: write raw text
                    handle.write(decrypted_text)
                    handle.write("\n")

        logger.info("Stored logs: %s/%s -> %s", machine_id, log_type, log_file)

    @staticmethod
    def parse_topic(topic: str) -> tuple[str, str]:
        """Extract machine_id and log_key from a Kafka topic name.

        Topics are now structured as  ``{machine_id}-{log_key}``  where
        machine_id may itself contain hyphens (e.g. ``kshitij-ubuntu``).
        The log_key is always the *last* hyphen-separated segment.

        Examples
        --------
        >>> LogStorage.parse_topic("kshitij-ubuntu-syslog")
        ('kshitij-ubuntu', 'syslog')
        >>> LogStorage.parse_topic("lab-pc-security")
        ('lab-pc', 'security')
        >>> LogStorage.parse_topic("ubuntu-auth")
        ('ubuntu', 'auth')
        """
        parts = topic.rsplit("-", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return topic, "unknown"

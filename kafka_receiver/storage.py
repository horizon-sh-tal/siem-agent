"""Log storage organiser for the Kafka receiver.

Stores decrypted logs under:
    received_logs/{machine_id}/{filename}

Linux logs use standard Ubuntu filenames (single file per type, no date splitting):
    syslog, alternatives.log, auth.log, dpkg.log, apt/history.log, apt/term.log

Windows / other logs fall back to:
    received_logs/{machine_id}/{log_type}/{YYYY-MM-DD}.log
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

        Linux logs are stored as single files matching Ubuntu defaults
        (e.g. ``syslog``, ``auth.log``).  All other log types fall back
        to date-based files under a sub-directory.
        """
        ubuntu_name = LINUX_LOG_FILENAMES.get(log_type)

        if ubuntu_name is not None:
            # ---- Linux log: single file, Ubuntu naming ----
            log_file = os.path.join(self.base_dir, machine_id, ubuntu_name)
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, "a", encoding="utf-8") as handle:
                try:
                    parsed = json.loads(decrypted_text)
                    handle.write(json.dumps(parsed, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    handle.write(decrypted_text)
                handle.write("\n")
        else:
            # ---- Windows / other: date-based files ----
            log_dir = os.path.join(self.base_dir, machine_id, log_type)
            os.makedirs(log_dir, exist_ok=True)

            date_str = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime(
                "%Y-%m-%d"
            )
            log_file = os.path.join(log_dir, f"{date_str}.log")

            with open(log_file, "a", encoding="utf-8") as handle:
                try:
                    parsed = json.loads(decrypted_text)
                    handle.write(json.dumps(parsed, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    handle.write(decrypted_text)
                handle.write("\n")

        logger.info("Stored logs: %s/%s -> %s", machine_id, log_type, log_file)

    @staticmethod
    def parse_topic(topic: str) -> tuple[str, str]:
        """Extract machine_id and simplified log_type from a Kafka topic name.

        Examples
        --------
        >>> LogStorage.parse_topic("dev1-syslog-message")
        ('dev1', 'syslog')
        >>> LogStorage.parse_topic("prof2-windowsdefender")
        ('prof2', 'defender')
        """
        parts = topic.split("-", 1)
        machine_id = parts[0]
        raw_type = parts[1] if len(parts) > 1 else "unknown"

        # Simplify according to spec
        simple = (
            raw_type.replace("-message", "")
            .replace("wndsystemd", "")
            .replace("windows", "")
        )
        return machine_id, simple

"""Log storage organiser for the Kafka receiver.

Stores decrypted logs under:
    received_logs/{machine_id}/{log_type}/{YYYY-MM-DD}.log
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


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
        """Append *decrypted_text* to the daily log file."""
        log_dir = os.path.join(self.base_dir, machine_id, log_type)
        os.makedirs(log_dir, exist_ok=True)

        date_str = datetime.utcfromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"{date_str}.log")

        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(f"\n{'=' * 80}\n")
            handle.write(
                f"Timestamp: {datetime.utcfromtimestamp(timestamp_ms / 1000).isoformat()}\n"
            )
            handle.write(f"Machine: {machine_id} | Log Type: {log_type}\n")
            handle.write(f"{'=' * 80}\n")

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

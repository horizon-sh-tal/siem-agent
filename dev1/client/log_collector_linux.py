"""Linux log collector for Dev machines.

Reads 6 log files (/var/log/syslog, auth.log, alternatives.log, dpkg.log,
apt/history.log, apt/term.log), tracks position via CheckpointManager,
encrypts batches with RSA-4096 hybrid encryption, and sends to Kafka.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from common.checkpoint import CheckpointManager
from common.encryption import RSAEncryption
from common.kafka_utils import ResilientKafkaProducer

logger = logging.getLogger(__name__)


class LinuxLogCollector:
    """Collect new log entries from Linux log files and ship to Kafka."""

    def __init__(
        self,
        config: Dict[str, Any],
        checkpoint_manager: CheckpointManager,
        kafka_producer: ResilientKafkaProducer,
    ) -> None:
        self.config = config
        self.checkpoint = checkpoint_manager
        self.producer = kafka_producer
        self.machine_id: str = config["machine_id"]

        pub_key_path = config["encryption"]["public_key_path"]
        self.public_key = RSAEncryption.load_public_key(pub_key_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_collection_cycle(self) -> None:
        """Execute one collection cycle for all enabled logs."""
        logs_cfg: Dict[str, Dict] = self.config["log_collection"]["logs"]

        for log_name, log_cfg in logs_cfg.items():
            if not log_cfg.get("enabled", False):
                continue
            try:
                self._collect_log(log_name, log_cfg)
            except Exception as exc:
                logger.error("Failed to collect %s: %s", log_name, exc, exc_info=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_log(self, log_name: str, log_cfg: Dict[str, Any]) -> None:
        """Collect new entries from a single log file."""
        path: str = log_cfg["path"]
        topic: str = log_cfg["topic"]

        if not os.path.exists(path):
            logger.warning("Log file does not exist: %s", path)
            return

        last_pos = self.checkpoint.get(log_name, 0)
        last_inode = self.checkpoint.get(f"{log_name}_inode", 0)

        current_inode = self._get_inode(path)

        # Detect rotation: inode changed (only if we had a previous inode)
        # or file shrank below our last read position
        if (last_inode != 0 and current_inode != last_inode) or \
           (last_pos > 0 and self._file_size(path) < last_pos):
            logger.info("Rotation detected for %s – resetting position", log_name)
            last_pos = 0

        new_entries = self._read_from_position(path, last_pos)
        new_pos = last_pos + sum(len(line.encode("utf-8", errors="replace")) for line in new_entries)

        if not new_entries:
            logger.debug("No new entries for %s", log_name)
            return

        payload = self._build_payload(log_name, new_entries)
        encrypted = RSAEncryption.encrypt(payload, self.public_key)
        self.producer.send(topic, encrypted)

        self.checkpoint.update(log_name, new_pos)
        self.checkpoint.update(f"{log_name}_inode", current_inode)
        logger.info(
            "Collected %d new entries from %s (%s)", len(new_entries), log_name, path
        )

    def _read_from_position(self, path: str, position: int) -> List[str]:
        """Read lines starting from byte *position*."""
        entries: List[str] = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                handle.seek(position)
                for line in handle:
                    stripped = line.rstrip("\n")
                    if stripped:
                        entries.append(stripped)
        except PermissionError:
            logger.error("Permission denied reading %s", path)
        except OSError as exc:
            logger.error("OS error reading %s: %s", path, exc)
        return entries

    def _build_payload(self, log_name: str, entries: List[str]) -> str:
        """Build a JSON payload for a batch of log entries."""
        return json.dumps(
            {
                "machine_id": self.machine_id,
                "log_name": log_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entry_count": len(entries),
                "entries": entries,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _get_inode(path: str) -> int:
        """Return inode number (0 on platforms without inodes)."""
        try:
            return os.stat(path).st_ino
        except OSError:
            return 0

    @staticmethod
    def _file_size(path: str) -> int:
        """Return file size in bytes."""
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

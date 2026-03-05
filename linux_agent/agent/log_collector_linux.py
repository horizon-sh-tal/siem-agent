"""Linux log collector for SIEM Agent.

Reads log files defined in config.json, tracks read position via
CheckpointManager, encrypts batches with RSA-4096 hybrid encryption,
and ships to Kafka topics named: {machine_id}-{log_key}
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from common.checkpoint import CheckpointManager
from common.encryption import RSAEncryption
from common.kafka_utils import ResilientKafkaProducer

logger = logging.getLogger(__name__)


class LinuxLogCollector:
    """Collect new log entries from Linux log files and ship to Kafka."""

    # Maximum lines per batch to prevent OOM on large log files
    MAX_ENTRIES_PER_BATCH = 500

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
        """Execute one collection cycle for all enabled log sources."""
        logs_cfg: Dict[str, Dict] = self.config["log_collection"]["logs"]
        for log_key, log_cfg in logs_cfg.items():
            if not log_cfg.get("enabled", False):
                continue
            try:
                self._collect_log(log_key, log_cfg)
            except Exception as exc:
                logger.error("Failed to collect %s: %s", log_key, exc, exc_info=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_log(self, log_key: str, log_cfg: Dict[str, Any]) -> None:
        """Collect new entries from a single log file."""
        path: str = log_cfg["path"]
        # Topic is dynamic: {machine_id}-{log_key}
        topic: str = f"{self.machine_id}-{log_key}"

        if not os.path.exists(path):
            logger.warning("Log file does not exist: %s", path)
            return

        last_pos = self.checkpoint.get(log_key, 0)
        last_inode = self.checkpoint.get(f"{log_key}_inode", 0)
        current_inode = self._get_inode(path)

        # Detect log rotation by inode change or file shrinkage
        if (last_inode != 0 and current_inode != last_inode) or (
            last_pos > 0 and self._file_size(path) < last_pos
        ):
            logger.info("Log rotation detected for %s – resetting position", log_key)
            last_pos = 0

        # On first run, start from the current end to avoid dumping history
        if last_inode == 0 and last_pos == 0:
            last_pos = self._file_size(path)
            logger.info(
                "First run for %s – starting from end of file (pos %d)",
                log_key,
                last_pos,
            )
            self.checkpoint.update(log_key, last_pos)
            self.checkpoint.update(f"{log_key}_inode", current_inode)
            return

        new_entries = self._read_from_position(path, last_pos, self.MAX_ENTRIES_PER_BATCH)
        new_pos = last_pos + sum(
            len(line.encode("utf-8", errors="replace")) + 1 for line in new_entries
        )

        if not new_entries:
            logger.debug("No new entries for %s", log_key)
            return

        payload = self._build_payload(log_key, new_entries)
        encrypted = RSAEncryption.encrypt(payload, self.public_key)
        self.producer.send(topic, encrypted)

        self.checkpoint.update(log_key, new_pos)
        self.checkpoint.update(f"{log_key}_inode", current_inode)
        logger.info(
            "Collected %d new entries from %s (%s)", len(new_entries), log_key, path
        )

    def _read_from_position(
        self, path: str, position: int, max_lines: int = 0
    ) -> List[str]:
        """Read lines starting from byte *position*."""
        entries: List[str] = []
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                handle.seek(position)
                for line in handle:
                    stripped = line.rstrip("\n")
                    if stripped:
                        entries.append(stripped)
                    if max_lines and len(entries) >= max_lines:
                        break
        except PermissionError:
            logger.error("Permission denied reading %s", path)
        except OSError as exc:
            logger.error("OS error reading %s: %s", path, exc)
        return entries

    def _build_payload(self, log_key: str, entries: List[str]) -> str:
        """Build a JSON payload for a batch of log entries."""
        return json.dumps(
            {
                "machine_id": self.machine_id,
                "log_key": log_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entry_count": len(entries),
                "entries": entries,
            },
            ensure_ascii=False,
        )

    @staticmethod
    def _get_inode(path: str) -> int:
        try:
            return os.stat(path).st_ino
        except OSError:
            return 0

    @staticmethod
    def _file_size(path: str) -> int:
        try:
            return os.path.getsize(path)
        except OSError:
            return 0

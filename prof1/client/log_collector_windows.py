"""Windows Event Log collector for Prof machines.

Reads 9 event log sources (Security, System, BITS-Client, AppLocker,
Firewall, Defender, PowerShell, new-service filter, bitlocker filter),
tracks last record ID via CheckpointManager, encrypts batches with
RSA-4096 hybrid encryption, and sends to Kafka.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from common.checkpoint import CheckpointManager
from common.encryption import RSAEncryption
from common.kafka_utils import ResilientKafkaProducer

logger = logging.getLogger(__name__)


class WindowsLogCollector:
    """Collect new Windows Event Log entries and ship to Kafka."""

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
        """Execute one collection cycle for all enabled event logs."""
        logs_cfg: Dict[str, Dict] = self.config["log_collection"]["logs"]

        for log_name, log_cfg in logs_cfg.items():
            if not log_cfg.get("enabled", False):
                continue
            try:
                self._collect_event_log(log_name, log_cfg)
            except Exception as exc:
                logger.error(
                    "Failed to collect %s: %s", log_name, exc, exc_info=True
                )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_event_log(self, log_name: str, log_cfg: Dict[str, Any]) -> None:
        """Collect new events from a single Windows Event Log channel."""
        channel: str = log_cfg["log_name"]
        topic: str = log_cfg["topic"]
        event_id_filter: Optional[int] = log_cfg.get("event_id")

        last_record_id = self.checkpoint.get(log_name, 0)

        new_events = self._query_events(channel, last_record_id, event_id_filter)

        if not new_events:
            logger.debug("No new events for %s", log_name)
            return

        max_record_id = max(evt.get("RecordId", 0) for evt in new_events)

        payload = self._build_payload(log_name, new_events)
        encrypted = RSAEncryption.encrypt(payload, self.public_key)
        self.producer.send(topic, encrypted)

        self.checkpoint.update(log_name, max_record_id)
        logger.info(
            "Collected %d new events from %s (channel=%s)",
            len(new_events),
            log_name,
            channel,
        )

    def _query_events(
        self,
        channel: str,
        after_record_id: int,
        event_id_filter: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Query Windows Event Log via PowerShell Get-WinEvent."""
        # Build filter hash table
        filter_parts = [f"LogName='{channel}'"]
        if event_id_filter is not None:
            filter_parts.append(f"Id={event_id_filter}")

        filter_hashtable = "; ".join(filter_parts)

        ps_script = (
            f"try {{\n"
            f"  $events = Get-WinEvent -FilterHashtable @{{{filter_hashtable}}} -ErrorAction Stop\n"
            f"  $events | Where-Object {{ $_.RecordId -gt {after_record_id} }} |\n"
            f"    Select-Object RecordId, TimeCreated, Id, LevelDisplayName, ProviderName, Message |\n"
            f"    ConvertTo-Json -Depth 3 -Compress\n"
            f"}} catch [Exception] {{\n"
            f"  if ($_.Exception.Message -notlike '*No events were found*') {{ throw }}\n"
            f"}}"
        )

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            logger.error("PowerShell timed out querying %s", channel)
            return []

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                logger.warning("PowerShell stderr for %s: %s", channel, stderr)
            return []

        output = result.stdout.strip()
        if not output:
            return []

        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse PowerShell JSON for %s: %s", channel, exc)
            return []

        # PowerShell returns a single object (not array) when there is one event
        if isinstance(parsed, dict):
            parsed = [parsed]

        return parsed

    def _build_payload(self, log_name: str, events: List[Dict[str, Any]]) -> str:
        """Build a JSON payload for a batch of event log entries."""
        return json.dumps(
            {
                "machine_id": self.machine_id,
                "log_name": log_name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_count": len(events),
                "events": events,
            },
            ensure_ascii=False,
            default=str,
        )

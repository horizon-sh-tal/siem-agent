#!/usr/bin/env python3
"""Kafka log receiver – consumes, decrypts, and stores Chatterbox logs."""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

# Ensure project root is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from kafka import KafkaConsumer

from decryption import LogDecryptor
from storage import LogStorage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ChatterboxLogReceiver:
    """Consume encrypted log messages from Kafka, decrypt, and store."""

    def __init__(self, config_path: str = "config.json") -> None:
        with open(config_path, "r", encoding="utf-8") as handle:
            self.config = json.load(handle)

        kafka_cfg = self.config["kafka"]
        enc_cfg = self.config["encryption"]
        storage_cfg = self.config["storage"]

        self.decryptor = LogDecryptor(enc_cfg["private_key_path"])
        self.storage = LogStorage(storage_cfg["base_dir"])

        self.consumer = KafkaConsumer(
            bootstrap_servers=kafka_cfg["bootstrap_servers"],
            group_id=kafka_cfg["group_id"],
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda m: m,  # raw bytes – decrypted later
        )

        pattern = kafka_cfg["topic_pattern"]
        self.consumer.subscribe(pattern=re.compile(pattern))
        logger.info("Receiver started. Topic pattern: %s", pattern)

    def run(self) -> None:
        """Main consumer loop."""
        logger.info("Consuming messages…")
        try:
            for message in self.consumer:
                self._process(message)
        except KeyboardInterrupt:
            logger.info("Interrupted – shutting down")
        finally:
            self.consumer.close()
            logger.info("Consumer closed")

    def _process(self, message) -> None:
        topic = message.topic
        timestamp_ms = message.timestamp or 0

        machine_id, log_type = LogStorage.parse_topic(topic)

        plaintext = self.decryptor.decrypt(message.value)
        if plaintext is None:
            logger.warning("Skipping undecryptable message on topic %s", topic)
            return

        self.storage.store(machine_id, log_type, plaintext, timestamp_ms)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Chatterbox Kafka Log Receiver")
    parser.add_argument("--config", default="config.json", help="Path to receiver config")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    ChatterboxLogReceiver(args.config).run()

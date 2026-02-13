"""Kafka producer with buffering and retry support."""

from __future__ import annotations

import logging
from threading import Lock
from typing import Optional

from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable

from .log_buffer import LocalLogBuffer

logger = logging.getLogger(__name__)


class ResilientKafkaProducer:
    """Kafka producer with automatic buffering and retry logic."""

    def __init__(self, bootstrap_servers: str, buffer_db_path: str, max_buffer_mb: int = 100) -> None:
        self.bootstrap_servers = bootstrap_servers
        self._lock = Lock()
        self.producer: Optional[KafkaProducer] = None
        self.buffer = LocalLogBuffer(buffer_db_path, max_buffer_mb)
        self.connect()

    def connect(self) -> bool:
        """Attempt to connect to Kafka broker."""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                max_block_ms=5000,
                request_timeout_ms=10000,
            )
            logger.info("Connected to Kafka broker")
            return True
        except NoBrokersAvailable:
            logger.warning("Kafka broker unavailable. Buffering logs locally.")
            self.producer = None
            return False

    def send(self, topic: str, encrypted_data: bytes) -> bool:
        """Send encrypted data to Kafka or buffer locally if unavailable."""
        with self._lock:
            self.flush_buffer()

            if self.producer:
                try:
                    future = self.producer.send(topic, encrypted_data)
                    future.get(timeout=10)
                    logger.debug("Sent to Kafka: %s", topic)
                    return True
                except KafkaError as exc:
                    logger.error("Kafka send failed: %s. Buffering locally.", exc)
                    self.producer = None

            self.buffer.add(topic, encrypted_data)
            logger.info("Buffered locally: %s (%s in queue)", topic, self.buffer.count())
            return False

    def flush_buffer(self) -> None:
        """Attempt to send all buffered messages."""
        if not self.producer:
            self.connect()

        if not self.producer:
            return

        for entry_id, topic, encrypted_data in self.buffer.get_all():
            try:
                future = self.producer.send(topic, encrypted_data)
                future.get(timeout=10)
                self.buffer.remove(entry_id)
                logger.info("Flushed buffered message: %s", topic)
            except KafkaError as exc:
                logger.warning("Failed to flush buffered message: %s", exc)
                break

    def close(self) -> None:
        """Close producer and buffer."""
        if self.producer:
            self.producer.flush()
            self.producer.close()
        self.buffer.close()

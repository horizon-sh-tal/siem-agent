#!/usr/bin/env python3
"""Chatterbox main entry point – Dev2 (Linux)."""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.config_loader import load_config
from common.checkpoint import CheckpointManager
from common.kafka_utils import ResilientKafkaProducer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "..", "logs", "chatterbox.log")
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class ChatterboxApplication:
    def __init__(self, config_path: str) -> None:
        self.config = load_config(config_path)
        self.running = True

        # Resolve paths relative to config file directory
        config_dir = os.path.dirname(os.path.abspath(config_path))
        checkpoint_path = os.path.join(config_dir, self.config["resilience"]["checkpoint_file"])
        buffer_path = os.path.join(config_dir, "logs", "buffer.db")

        self.checkpoint = CheckpointManager(checkpoint_path)
        self.kafka_producer = ResilientKafkaProducer(
            self.config["kafka_broker"],
            buffer_path,
            self.config["resilience"].get("buffer_max_size_mb", 100),
        )
        from client.log_collector_linux import LinuxLogCollector
        self.log_collector = LinuxLogCollector(self.config, self.checkpoint, self.kafka_producer)
        from client.service_manager import ServiceManager
        self.service_manager = ServiceManager(self.config)
        self._shutdown_count = 0
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame) -> None:
        self._shutdown_count += 1
        if self._shutdown_count > 1:
            logger.info("Forced exit")
            os._exit(1)
        logger.info("Received signal %s – shutting down (press Ctrl+C again to force)", signum)
        self.running = False

    def _run_collection_loop(self) -> None:
        logger.info("Starting log collection for %s", self.config["machine_id"])
        while self.running:
            try:
                self.log_collector.run_collection_cycle()
                self.service_manager.log_health()
                interval = self.config["log_collection"]["interval_seconds"]
                logger.info("Collection complete. Next in %ds.", interval)
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as exc:
                logger.error("Collection cycle error: %s", exc, exc_info=True)
                time.sleep(60)

    def run(self, chat: bool = False) -> None:
        logger.info("Chatterbox starting for %s", self.config["machine_id"])
        t = threading.Thread(target=self._run_collection_loop, daemon=True)
        t.start()
        if chat and self.config["chat"].get("enabled"):
            try:
                from client.chat_interface import ChatInterface
                username = self.config["chat"]["account"]
                password = input("Password: ")
                ci = ChatInterface(self.config, username, password)
                ci.start_cli()
                self.running = False
            except Exception as exc:
                logger.error("Chat failed: %s", exc)
        else:
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        self.running = False
        t.join(timeout=30)
        self.kafka_producer.close()
        logger.info("Chatterbox shutdown complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chatterbox Dev2")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--chat", action="store_true")
    args = parser.parse_args()
    ChatterboxApplication(args.config).run(chat=args.chat)


if __name__ == "__main__":
    main()

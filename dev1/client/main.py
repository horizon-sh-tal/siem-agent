#!/usr/bin/env python3
"""Chatterbox main entry point – Dev1 (Linux).

Runs the background log collection service. Chat can be started
interactively by passing --chat.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import threading
import time
from pathlib import Path

# Ensure project root is importable
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
    """Main application managing log collection (and optional chat)."""

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

        # Import the correct collector for this OS
        from client.log_collector_linux import LinuxLogCollector

        self.log_collector = LinuxLogCollector(
            self.config, self.checkpoint, self.kafka_producer
        )

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
        logger.info("Starting log collection service for %s", self.config["machine_id"])
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
        logger.info("Log collection stopped")

    def run(self, chat: bool = False, logs_enabled: bool = True) -> None:
        logger.info("Chatterbox starting for %s", self.config["machine_id"])
        collection_thread = None
        if logs_enabled:
            collection_thread = threading.Thread(
                target=self._run_collection_loop,
                daemon=True,
            )
            collection_thread.start()

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
            if logs_enabled:
                try:
                    while self.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    pass
            else:
                logger.error("No mode selected. Use --chat or enable log collection.")

        self.running = False
        if collection_thread is not None:
            collection_thread.join(timeout=30)
        self.kafka_producer.close()
        logger.info("Chatterbox shutdown complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="Chatterbox Dev1")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    parser.add_argument("--chat", action="store_true", help="Start interactive chat")
    parser.add_argument(
        "--chat-only",
        action="store_true",
        help="Run chat without starting log collection",
    )
    args = parser.parse_args()
    if args.chat_only:
        args.chat = True

    app = ChatterboxApplication(args.config)
    app.run(chat=args.chat, logs_enabled=not args.chat_only)


if __name__ == "__main__":
    main()

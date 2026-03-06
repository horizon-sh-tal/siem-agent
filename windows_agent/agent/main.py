#!/usr/bin/env python3
"""SIEM Agent – Windows entry point.

Runs the background Windows Event Log collection service.
Run with --help to see options.
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

# Ensure project root (for common/) and windows_agent root (for agent/) are importable
_THIS_DIR = Path(__file__).resolve()
_AGENT_ROOT = str(_THIS_DIR.parent.parent)          # .../windows/  (contains agent/)
_PROJECT_ROOT = str(_THIS_DIR.parent.parent.parent) # project root  (contains common/)
for _p in (_PROJECT_ROOT, _AGENT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from common.config_loader import load_config
from common.checkpoint import CheckpointManager
from common.kafka_utils import ResilientKafkaProducer
from common import machine_id as mid_resolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(os.path.dirname(__file__), "..", "logs", "siem_agent.log")
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class WindowsSIEMAgent:
    """Manages Windows Event Log collection and Kafka shipping."""

    def __init__(self, config_path: str) -> None:
        self.config = load_config(config_path)

        # Resolve machine ID (auto-detect or config override)
        self.config["machine_id"] = mid_resolver.resolve(
            self.config.get("machine_id", "auto")
        )

        self.running = True

        config_dir = os.path.dirname(os.path.abspath(config_path))
        checkpoint_path = os.path.join(
            config_dir, self.config["resilience"]["checkpoint_file"]
        )
        buffer_path = os.path.join(config_dir, "logs", "buffer.db")
        os.makedirs(os.path.join(config_dir, "logs"), exist_ok=True)

        self.checkpoint = CheckpointManager(checkpoint_path)
        self.kafka_producer = ResilientKafkaProducer(
            self.config["kafka_broker"],
            buffer_path,
            self.config["resilience"].get("buffer_max_size_mb", 100),
        )

        from agent.log_collector_windows import WindowsLogCollector
        from agent.service_manager import ServiceManager

        self.log_collector = WindowsLogCollector(
            self.config, self.checkpoint, self.kafka_producer
        )
        self.service_manager = ServiceManager(self.config)

        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame) -> None:
        logger.info("Received signal %s – shutting down", signum)
        self.running = False

    def _run_collection_loop(self) -> None:
        logger.info(
            "Starting log collection for machine: %s", self.config["machine_id"]
        )
        while self.running:
            try:
                self.log_collector.run_collection_cycle()
                self.service_manager.log_health()
                interval = self.config["log_collection"]["interval_seconds"]
                logger.info("Collection complete. Next run in %ds.", interval)
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as exc:
                logger.error("Collection cycle error: %s", exc, exc_info=True)
                time.sleep(60)
        logger.info("Log collection stopped")

    def run(self) -> None:
        logger.info(
            "SIEM Windows Agent starting — machine_id=%s", self.config["machine_id"]
        )
        collection_thread = threading.Thread(
            target=self._run_collection_loop, daemon=False
        )
        collection_thread.start()
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            collection_thread.join(timeout=30)
            self.kafka_producer.close()
            logger.info("SIEM Agent shutdown complete")


def main() -> None:
    parser = argparse.ArgumentParser(description="SIEM Agent – Windows log collector")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "..", "config.json"),
        help="Path to config.json (default: ../config.json)",
    )
    args = parser.parse_args()
    WindowsSIEMAgent(args.config).run()


if __name__ == "__main__":
    main()

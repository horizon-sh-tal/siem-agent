"""Service health monitoring for Chatterbox."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ServiceManager:
    """Monitor component health and report status."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.machine_id: str = config["machine_id"]
        self._start_time = time.time()

    def health_check(self) -> Dict[str, Any]:
        uptime = time.time() - self._start_time
        return {
            "machine_id": self.machine_id,
            "uptime_seconds": int(uptime),
            "pid": os.getpid(),
            "status": "running",
        }

    def log_health(self) -> None:
        status = self.health_check()
        logger.info(
            "Health: machine=%s uptime=%ds pid=%d",
            status["machine_id"], status["uptime_seconds"], status["pid"],
        )

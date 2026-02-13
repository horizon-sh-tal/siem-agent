"""Checkpoint tracking utilities."""

from __future__ import annotations

import json
import os
from threading import RLock
from typing import Dict


class CheckpointManager:
    """Track last read position per log to prevent duplicates."""

    def __init__(self, checkpoint_file: str) -> None:
        self.checkpoint_file = checkpoint_file
        self.checkpoints: Dict[str, int] = {}
        self._lock = RLock()
        self._ensure_parent_dir()
        self.load()

    def _ensure_parent_dir(self) -> None:
        parent = os.path.dirname(self.checkpoint_file)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def load(self) -> None:
        """Load checkpoints from disk."""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, "r", encoding="utf-8") as handle:
                self.checkpoints = json.load(handle)

    def save(self) -> None:
        """Persist checkpoints to disk atomically."""
        with self._lock:
            temp_path = f"{self.checkpoint_file}.tmp"
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump(self.checkpoints, handle, indent=2)
            os.replace(temp_path, self.checkpoint_file)

    def get(self, log_name: str, default: int = 0) -> int:
        """Get a checkpoint value."""
        return int(self.checkpoints.get(log_name, default))

    def update(self, log_name: str, position: int) -> None:
        """Update a checkpoint value."""
        with self._lock:
            self.checkpoints[log_name] = int(position)
            self.save()

    def get_all(self) -> Dict[str, int]:
        """Get a copy of all checkpoints."""
        return dict(self.checkpoints)

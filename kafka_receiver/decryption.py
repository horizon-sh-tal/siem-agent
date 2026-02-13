"""Decryption helper for the Kafka log receiver."""

from __future__ import annotations

import logging
from typing import Optional

from common.encryption import RSAEncryption

logger = logging.getLogger(__name__)


class LogDecryptor:
    """Decrypt incoming log payloads using the Kafka private key."""

    def __init__(self, private_key_path: str) -> None:
        self._private_key = RSAEncryption.load_private_key(private_key_path)

    def decrypt(self, ciphertext: bytes) -> Optional[str]:
        """Decrypt *ciphertext* and return the UTF-8 string, or None on error."""
        try:
            plaintext = RSAEncryption.decrypt(ciphertext, self._private_key)
            return plaintext.decode("utf-8")
        except Exception as exc:
            logger.error("Decryption failed: %s", exc, exc_info=True)
            return None

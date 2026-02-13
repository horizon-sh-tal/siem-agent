"""RSA-4096 and hybrid AES encryption utilities."""

from __future__ import annotations

import logging
import os
import struct
from typing import Union

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, padding as sym_padding, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

logger = logging.getLogger(__name__)


class RSAEncryption:
    """Handle RSA-4096 encryption/decryption for log transmission."""

    @staticmethod
    def generate_key_pair(private_key_path: str, public_key_path: str) -> None:
        """Generate a new RSA-4096 key pair and save to disk."""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend(),
        )

        with open(private_key_path, "wb") as handle:
            handle.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )

        public_key = private_key.public_key()
        with open(public_key_path, "wb") as handle:
            handle.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

        try:
            os.chmod(private_key_path, 0o600)
            os.chmod(public_key_path, 0o644)
        except PermissionError:
            logger.warning("Unable to set key permissions on this platform")

    @staticmethod
    def load_public_key(public_key_path: str):
        """Load a PEM public key from disk."""
        with open(public_key_path, "rb") as handle:
            return serialization.load_pem_public_key(handle.read(), backend=default_backend())

    @staticmethod
    def load_private_key(private_key_path: str):
        """Load a PEM private key from disk."""
        with open(private_key_path, "rb") as handle:
            return serialization.load_pem_private_key(
                handle.read(), password=None, backend=default_backend()
            )

    @staticmethod
    def encrypt(data: Union[str, bytes], public_key) -> bytes:
        """Encrypt data with RSA public key (hybrid for large payloads)."""
        if isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        if len(data_bytes) > 446:
            return RSAEncryption._hybrid_encrypt(data_bytes, public_key)

        return public_key.encrypt(
            data_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    @staticmethod
    def _hybrid_encrypt(data: bytes, public_key) -> bytes:
        """Hybrid encryption: AES-256 for data, RSA for AES key and IV."""
        aes_key = os.urandom(32)
        iv = os.urandom(16)

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()

        padder = sym_padding.PKCS7(128).padder()
        padded = padder.update(data) + padder.finalize()
        encrypted_data = encryptor.update(padded) + encryptor.finalize()

        encrypted_key = public_key.encrypt(
            aes_key + iv,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        return struct.pack("!I", len(encrypted_key)) + encrypted_key + encrypted_data

    @staticmethod
    def decrypt(ciphertext: bytes, private_key) -> bytes:
        """Decrypt ciphertext with RSA private key (supports hybrid)."""
        if RSAEncryption._is_hybrid(ciphertext):
            return RSAEncryption._hybrid_decrypt(ciphertext, private_key)

        return private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

    @staticmethod
    def _is_hybrid(ciphertext: bytes) -> bool:
        """Determine if payload matches hybrid format."""
        if len(ciphertext) < 4:
            return False
        key_len = struct.unpack("!I", ciphertext[:4])[0]
        return 0 < key_len < len(ciphertext) - 4

    @staticmethod
    def _hybrid_decrypt(ciphertext: bytes, private_key) -> bytes:
        """Decrypt hybrid payload."""
        key_len = struct.unpack("!I", ciphertext[:4])[0]
        encrypted_key = ciphertext[4 : 4 + key_len]
        encrypted_data = ciphertext[4 + key_len :]

        aes_key_iv = private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        aes_key = aes_key_iv[:32]
        iv = aes_key_iv[32:48]

        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        padded = decryptor.update(encrypted_data) + decryptor.finalize()

        unpadder = sym_padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

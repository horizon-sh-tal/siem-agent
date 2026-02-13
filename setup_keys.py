#!/usr/bin/env python3
"""Generate RSA key pairs for all Chatterbox machines."""

from __future__ import annotations

import os

from common.encryption import RSAEncryption


def setup_all_keys() -> None:
    """Generate keys for all machines and copy public keys as required."""
    machines = ["dev1", "dev2", "prof1", "prof2", "kafka_receiver"]

    for machine in machines:
        key_dir = os.path.join(machine, "keys")
        os.makedirs(key_dir, exist_ok=True)

        private_key_path = os.path.join(key_dir, f"{machine}_private.pem")
        public_key_path = os.path.join(key_dir, f"{machine}_public.pem")

        RSAEncryption.generate_key_pair(private_key_path, public_key_path)

    kafka_public_key = os.path.join("kafka_receiver", "keys", "kafka_receiver_public.pem")

    for client in ["dev1", "dev2", "prof1", "prof2"]:
        dest = os.path.join(client, "keys", "kafka_public.pem")
        with open(kafka_public_key, "rb") as src_handle:
            with open(dest, "wb") as dst_handle:
                dst_handle.write(src_handle.read())

    for client in ["dev1", "dev2", "prof1", "prof2"]:
        src = os.path.join(client, "keys", f"{client}_public.pem")
        dest = os.path.join("kafka_receiver", "keys", f"{client}_public.pem")
        with open(src, "rb") as src_handle:
            with open(dest, "wb") as dst_handle:
                dst_handle.write(src_handle.read())


if __name__ == "__main__":
    setup_all_keys()

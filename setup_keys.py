#!/usr/bin/env python3
"""Generate RSA key pairs for all Chatterbox machines."""

from __future__ import annotations

import os

from common.encryption import RSAEncryption


def setup_all_keys() -> None:
    """Generate RSA-4096 key pairs for both agents and the Kafka receiver.

    Each agent gets its own key pair.  The Kafka receiver's public key is
    copied into every agent's keys/ folder so they can encrypt outbound logs.
    """
    agents = ["linux_agent", "windows_agent", "kafka_receiver"]

    for agent in agents:
        key_dir = os.path.join(agent, "keys")
        os.makedirs(key_dir, exist_ok=True)

        private_key_path = os.path.join(key_dir, f"{agent}_private.pem")
        public_key_path  = os.path.join(key_dir, f"{agent}_public.pem")
        RSAEncryption.generate_key_pair(private_key_path, public_key_path)
        print(f"Generated keys for {agent}")

    # Copy the Kafka receiver's public key into each agent so they can encrypt
    kafka_public_key = os.path.join("kafka_receiver", "keys", "kafka_receiver_public.pem")
    for agent in ["linux_agent", "windows_agent"]:
        dest = os.path.join(agent, "keys", "kafka_public.pem")
        with open(kafka_public_key, "rb") as src_handle:
            with open(dest, "wb") as dst_handle:
                dst_handle.write(src_handle.read())
        print(f"Copied kafka_public.pem -> {dest}")


if __name__ == "__main__":
    setup_all_keys()

"""Chat interface using Kafka as message broker.

Supports EXACTLY 3 hardcoded accounts: Prof1, Prof2, Guest.
No user registration or creation functionality exists.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

# Absolute list of allowed usernames — no others permitted
_ALLOWED_USERS = frozenset({"Prof1", "Prof2", "Guest"})


class ChatInterface:
    """Kafka-backed CLI chat with strict 3-user enforcement."""

    def __init__(
        self,
        config: Dict[str, Any],
        username: str,
        password: str,
        users_file: str = "users.json",
    ) -> None:
        if username not in _ALLOWED_USERS:
            raise ValueError(f"User '{username}' is not a valid account")

        self.config = config
        self.username = username
        # Look for users.json in parent directory (Chatterbox root)
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._users_file = os.path.join(os.path.dirname(script_dir), users_file)

        if not self.authenticate(username, password):
            raise ValueError("Invalid credentials")

        self.user_info = self._load_user_info(username)

        self.producer = KafkaProducer(
            bootstrap_servers=config["kafka_broker"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        subscribed = self._get_subscribed_topics()
        self.consumer = KafkaConsumer(
            *subscribed,
            bootstrap_servers=config["kafka_broker"],
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            group_id=f"chat-{username}",
            auto_offset_reset="latest",
        )

        self.running = True
        self._listener = threading.Thread(
            target=self._listen, daemon=True
        )
        self._listener.start()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, username: str, password: str) -> bool:
        """Verify credentials against hardcoded users.json."""
        users_db = self._load_users_db()

        if users_db.get("registration_disabled") is not True:
            raise RuntimeError("registration_disabled must be true!")

        if username not in users_db.get("users", {}):
            logger.warning("Auth attempt for unknown user: %s", username)
            return False

        stored_hash = users_db["users"][username]["password_hash"]
        candidate = self._hash_password(password)
        return candidate == stored_hash

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(self, recipient: str, message: str) -> None:
        """Send a chat message to *recipient*."""
        if recipient not in self.user_info.get("can_chat_with", []):
            logger.warning("%s tried to message disallowed user %s", self.username, recipient)
            print(f"You cannot send messages to {recipient}")
            return

        topic = self._get_chat_topic(self.username, recipient)
        msg = {
            "from": self.username,
            "to": recipient,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.producer.send(topic, msg)
        self.producer.flush()
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] You -> {recipient}: {message}")

    # ------------------------------------------------------------------
    # CLI loop
    # ------------------------------------------------------------------

    def start_cli(self) -> None:
        """Interactive CLI chat session."""
        print(f"\n=== Chatterbox Chat ===")
        print(f"Logged in as: {self.username}")
        print(f"You can chat with: {', '.join(self.user_info.get('can_chat_with', []))}")
        print("Usage: @Recipient Your message here")
        print("Commands: /quit")
        print("=" * 40)

        while self.running:
            try:
                user_input = input("> ")
                if user_input.strip() == "/quit":
                    self.running = False
                    break
                if user_input.startswith("@"):
                    parts = user_input[1:].split(" ", 1)
                    if len(parts) == 2:
                        self.send_message(parts[0], parts[1])
                    else:
                        print("Usage: @Recipient Your message here")
                else:
                    print("Start messages with @Recipient")
            except (KeyboardInterrupt, EOFError):
                self.running = False
                break

        print("\nGoodbye!")
        self._close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _listen(self) -> None:
        """Background thread that prints incoming messages."""
        for message in self.consumer:
            if not self.running:
                break
            msg = message.value
            if msg.get("from") == self.username:
                continue
            ts = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
            print(f"\n[{ts}] {msg['from']}: {msg['message']}")
            print("> ", end="", flush=True)

    def _get_subscribed_topics(self) -> List[str]:
        mapping = {
            "Prof1": ["chat-prof1-prof2", "chat-prof1-guest"],
            "Prof2": ["chat-prof1-prof2", "chat-prof2-guest"],
            "Guest": ["chat-prof1-guest", "chat-prof2-guest", "chat-guest-group"],
        }
        return mapping.get(self.username, [])

    @staticmethod
    def _get_chat_topic(sender: str, recipient: str) -> str:
        if sender == "Guest" or recipient == "Guest":
            prof = sender if "Prof" in sender else recipient
            if "Prof" in prof:
                return f"chat-{prof.lower()}-guest"
            return "chat-guest-group"
        return "chat-prof1-prof2"

    def _load_users_db(self) -> Dict[str, Any]:
        with open(self._users_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_user_info(self, username: str) -> Dict[str, Any]:
        db = self._load_users_db()
        return db["users"][username]

    @staticmethod
    def _hash_password(password: str) -> str:
        """Simple SHA-256 hash placeholder — replace with scrypt in production."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _close(self) -> None:
        try:
            self.consumer.close()
        except Exception:
            pass
        try:
            self.producer.close()
        except Exception:
            pass

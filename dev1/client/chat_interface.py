"""Chat interface using Kafka as message broker.

Supports EXACTLY 3 hardcoded accounts: Prof1, Prof2, Guest.
No user registration or creation functionality exists.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

logger = logging.getLogger(__name__)

# Absolute list of allowed usernames — no others permitted
_ALLOWED_USERS = frozenset({"Prof1", "Prof2", "Guest"})
MAX_ATTACHMENT_BYTES = 7 * 1024 * 1024
ATTACHMENT_CHUNK_SIZE = 256 * 1024


class ChatInterface:
    """Kafka-backed CLI chat with strict 3-user enforcement."""

    def __init__(
        self,
        config: Dict[str, Any],
        username: str,
        password: str,
        users_file: str = "users.json",
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        if username not in _ALLOWED_USERS:
            raise ValueError(f"User '{username}' is not a valid account")

        self.config = config
        self.username = username
        # Look for users.json in parent directory (Chatterbox root)
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._users_file = os.path.join(os.path.dirname(script_dir), users_file)
        self._on_message = on_message
        self._chat_log_path = self._resolve_chat_log_path(script_dir)
        self._attachment_dir = self._resolve_attachment_dir(script_dir)
        self._attachment_buffers: Dict[str, Dict[str, Any]] = {}

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
            "type": "message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.producer.send(topic, msg)
        self.producer.flush()
        self._log_chat(
            {
                "timestamp": msg["timestamp"],
                "direction": "sent",
                "from": self.username,
                "to": recipient,
                "type": "message",
                "message": message,
            }
        )
        logger.info("Chat sent: %s -> %s", self.username, recipient)
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] You -> {recipient}: {message}")

    def send_attachment(self, recipient: str, file_path: str) -> None:
        """Send a file attachment to *recipient* in chunks."""
        if recipient not in self.user_info.get("can_chat_with", []):
            logger.warning("%s tried to send attachment to %s", self.username, recipient)
            print(f"You cannot send attachments to {recipient}")
            return

        if not os.path.isfile(file_path):
            print("Attachment not found.")
            return

        file_size = os.path.getsize(file_path)
        if file_size > MAX_ATTACHMENT_BYTES:
            print("Attachment too large.")
            return

        file_name = os.path.basename(file_path)
        transfer_id = str(uuid.uuid4())
        with open(file_path, "rb") as handle:
            data = handle.read()

        chunk_count = (len(data) + ATTACHMENT_CHUNK_SIZE - 1) // ATTACHMENT_CHUNK_SIZE
        for index in range(chunk_count):
            start = index * ATTACHMENT_CHUNK_SIZE
            end = start + ATTACHMENT_CHUNK_SIZE
            chunk = data[start:end]
            msg = {
                "from": self.username,
                "to": recipient,
                "type": "attachment_chunk",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transfer_id": transfer_id,
                "chunk_index": index,
                "chunk_count": chunk_count,
                "file_name": file_name,
                "file_size": file_size,
                "data": base64.b64encode(chunk).decode("ascii"),
            }
            topic = self._get_chat_topic(self.username, recipient)
            self.producer.send(topic, msg)
        self.producer.flush()

        self._log_chat(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "direction": "sent",
                "from": self.username,
                "to": recipient,
                "type": "attachment",
                "file_name": file_name,
                "file_size": file_size,
                "transfer_id": transfer_id,
            }
        )

    # ------------------------------------------------------------------
    # CLI loop
    # ------------------------------------------------------------------

    def start_cli(self) -> None:
        """Interactive CLI chat session."""
        print(f"\n=== Chatterbox Chat ===")
        print(f"Logged in as: {self.username}")
        print(f"You can chat with: {', '.join(self.user_info.get('can_chat_with', []))}")
        print("Usage: @Recipient Your message here")
        print("Commands: /quit, /attach Recipient /path/to/file")
        print("=" * 40)

        while self.running:
            try:
                user_input = input("> ")
                if user_input.strip() == "/quit":
                    self.running = False
                    break
                if user_input.startswith("/attach "):
                    parts = user_input.split(" ", 2)
                    if len(parts) == 3:
                        self.send_attachment(parts[1], parts[2])
                    else:
                        print("Usage: /attach Recipient /path/to/file")
                    continue
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
            if msg.get("type") == "attachment_chunk":
                self._handle_attachment_chunk(msg)
                continue

            logger.info("Chat received: %s -> %s", msg.get("from"), self.username)
            self._log_chat(
                {
                    "timestamp": msg.get("timestamp"),
                    "direction": "received",
                    "from": msg.get("from"),
                    "to": self.username,
                    "type": msg.get("type", "message"),
                    "message": msg.get("message", ""),
                }
            )
            if self._on_message is not None:
                self._on_message(msg)
            else:
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

    def _resolve_chat_log_path(self, script_dir: str) -> str:
        base_dir = os.path.join(os.path.dirname(script_dir), "logs")
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, "chat.log")

    def _resolve_attachment_dir(self, script_dir: str) -> str:
        base_dir = os.path.join(os.path.dirname(script_dir), "logs", "attachments")
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def _log_chat(self, entry: Dict[str, Any]) -> None:
        entry = dict(entry)
        entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        try:
            with open(self._chat_log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False))
                handle.write("\n")
        except OSError as exc:
            logger.warning("Failed to write chat log: %s", exc)

    def _handle_attachment_chunk(self, msg: Dict[str, Any]) -> None:
        transfer_id = msg.get("transfer_id")
        if not transfer_id:
            return

        buffer = self._attachment_buffers.setdefault(
            transfer_id,
            {
                "file_name": msg.get("file_name", "attachment"),
                "file_size": msg.get("file_size", 0),
                "from": msg.get("from"),
                "to": msg.get("to"),
                "chunk_count": msg.get("chunk_count", 0),
                "chunks": {},
            },
        )
        buffer["chunks"][msg.get("chunk_index")] = msg.get("data")

        if len(buffer["chunks"]) != buffer["chunk_count"]:
            return

        file_name = os.path.basename(buffer["file_name"])
        file_path = self._unique_attachment_path(file_name)
        chunks = [buffer["chunks"][i] for i in range(buffer["chunk_count"])]
        data = b"".join(base64.b64decode(c) for c in chunks)

        with open(file_path, "wb") as handle:
            handle.write(data)

        self._attachment_buffers.pop(transfer_id, None)

        event = {
            "timestamp": msg.get("timestamp"),
            "direction": "received",
            "from": msg.get("from"),
            "to": self.username,
            "type": "attachment",
            "file_name": file_name,
            "file_size": buffer["file_size"],
            "path": file_path,
            "transfer_id": transfer_id,
        }
        self._log_chat(event)

        if self._on_message is not None:
            self._on_message({"type": "attachment_received", **event})
        else:
            ts = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
            print(f"\n[{ts}] {msg.get('from')} sent attachment: {file_name}")
            print(f"Saved to: {file_path}")
            print("> ", end="", flush=True)

    def _unique_attachment_path(self, file_name: str) -> str:
        base = os.path.join(self._attachment_dir, file_name)
        if not os.path.exists(base):
            return base

        name, ext = os.path.splitext(file_name)
        counter = 1
        while True:
            candidate = os.path.join(self._attachment_dir, f"{name}_{counter}{ext}")
            if not os.path.exists(candidate):
                return candidate
            counter += 1

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

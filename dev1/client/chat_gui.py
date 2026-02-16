#!/usr/bin/env python3
"""Tkinter chat GUI for Chatterbox clients."""

from __future__ import annotations

import argparse
import logging
import os
import queue
import sys
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk

# Ensure project root is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.config_loader import load_config
from client.chat_interface import ChatInterface

logger = logging.getLogger(__name__)


def _build_gui(config_path: str) -> None:
    config = load_config(config_path)
    username = config["chat"]["account"]

    root = tk.Tk()
    root.title(f"Chatterbox Chat - {username}")
    root.geometry("720x520")

    password = simpledialog.askstring(
        "Chatterbox Login",
        f"Password for {username}:",
        show="*",
        parent=root,
    )
    if not password:
        root.destroy()
        return

    incoming = queue.Queue()

    def on_message(msg: dict) -> None:
        incoming.put(msg)

    try:
        ci = ChatInterface(config, username, password, on_message=on_message)
    except Exception as exc:
        messagebox.showerror("Chat Error", str(exc))
        root.destroy()
        return

    header = ttk.Label(root, text=f"Logged in as: {username}")
    header.pack(anchor="w", padx=10, pady=(10, 4))

    recipient_frame = ttk.Frame(root)
    recipient_frame.pack(fill="x", padx=10)

    ttk.Label(recipient_frame, text="Recipient:").pack(side="left")
    recipients = list(ci.user_info.get("can_chat_with", []))
    if not recipients:
        recipients = ["Guest"]
    recipient_var = tk.StringVar(value=recipients[0])
    recipient_box = ttk.Combobox(
        recipient_frame, textvariable=recipient_var, values=recipients, state="readonly"
    )
    recipient_box.pack(side="left", padx=6)

    chat_log = scrolledtext.ScrolledText(root, state="disabled", wrap="word")
    chat_log.pack(fill="both", expand=True, padx=10, pady=10)

    entry_frame = ttk.Frame(root)
    entry_frame.pack(fill="x", padx=10, pady=(0, 10))

    message_var = tk.StringVar()
    message_entry = ttk.Entry(entry_frame, textvariable=message_var)
    message_entry.pack(side="left", fill="x", expand=True)

    def append_message(line: str) -> None:
        chat_log.configure(state="normal")
        chat_log.insert("end", line + "\n")
        chat_log.configure(state="disabled")
        chat_log.see("end")

    def send_message(event=None) -> None:
        recipient = recipient_var.get().strip()
        text = message_var.get().strip()
        if not text:
            return
        ci.send_message(recipient, text)
        ts = datetime.now().strftime("%H:%M:%S")
        append_message(f"[{ts}] You -> {recipient}: {text}")
        message_var.set("")

    send_button = ttk.Button(entry_frame, text="Send", command=send_message)
    send_button.pack(side="right", padx=(6, 0))
    message_entry.bind("<Return>", send_message)

    def poll_incoming() -> None:
        while not incoming.empty():
            msg = incoming.get()
            ts = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
            append_message(f"[{ts}] {msg['from']}: {msg['message']}")
        root.after(200, poll_incoming)

    def on_close() -> None:
        try:
            ci.running = False
            ci._close()
        except Exception:
            pass
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    poll_incoming()
    message_entry.focus_set()
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Chatterbox Chat GUI (Dev1)")
    parser.add_argument("--config", default="config.json", help="Path to config.json")
    args = parser.parse_args()
    _build_gui(args.config)


if __name__ == "__main__":
    main()

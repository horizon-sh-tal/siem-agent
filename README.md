# SIEM Agent

Distributed log collection agents for Linux and Windows machines.  
Each agent encrypts system logs with RSA-4096 and ships them to a central Kafka broker for storage and analysis.

## Architecture

```
┌─────────────────────────┐     ┌─────────────────────────┐
│   Any Linux Machine     │     │   Any Windows Machine   │
│                         │     │                         │
│  linux_agent/           │     │  windows_agent/         │
│  └─ agent/main.py       │     │  └─ agent/main.py       │
│     ├─ log_collector    │     │     ├─ log_collector     │
│     └─ service_manager  │     │     └─ service_manager  │
│                         │     │                         │
│  Collects:              │     │  Collects:              │
│  • syslog               │     │  • Security             │
│  • auth.log             │     │  • System               │
│  • dpkg.log             │     │  • Defender             │
│  • apt history/term     │     │  • Firewall             │
│  • alternatives.log     │     │  • PowerShell           │
│                         │     │  • AppLocker, BITS, etc │
└──────────┬──────────────┘     └────────────┬────────────┘
           │  RSA-4096 encrypted             │
           │  Kafka topics                   │
           └──────────────┬──────────────────┘
                          ↓
           ┌──────────────────────────┐
           │   Kafka Broker VM        │
           │   (192.168.27.211:9092)  │
           │                          │
           │   kafka_receiver/        │
           │   └─ receiver.py         │
           │      ├─ decryption.py    │
           │      └─ storage.py       │
           │                          │
           │   received_logs/         │
           │   └─ {machine_id}/       │
           │      └─ {log files}      │
           └──────────────────────────┘
```

## Machine ID

Each agent resolves its machine ID at startup using this priority order:

1. **Config override** – set `machine_id` to anything other than `"auto"` in `config.json`
2. **Interactive + auto** – if `machine_id` is `"auto"` and a TTY is attached:
   - Auto-detects hostname via `socket.gethostname()`
   - Prompts: *Enter a label for this machine (leave blank to use hostname only)*
   - Result: `{label}-{hostname}` or just `{hostname}`
3. **Service fallback** – if no TTY (systemd / Windows service), silently uses `{hostname}`

## Project Structure

```
siem-agent/
├── common/                    # Shared library (both agents + receiver)
│   ├── encryption.py          # RSA-4096 hybrid encrypt/decrypt
│   ├── kafka_utils.py         # Resilient Kafka producer with SQLite buffer
│   ├── config_loader.py       # JSON config validation
│   ├── checkpoint.py          # Thread-safe read-position tracking
│   ├── log_buffer.py          # SQLite offline buffer
│   └── machine_id.py          # Machine ID resolution logic
│
├── linux_agent/               # Deploy on any Linux machine
│   ├── config.json
│   ├── requirements.txt
│   ├── install.sh
│   ├── agent/
│   │   ├── main.py
│   │   ├── log_collector_linux.py
│   │   └── service_manager.py
│   ├── keys/                  # kafka_public.pem (do not commit)
│   └── services/
│       └── siem-agent-linux.service
│
├── windows_agent/             # Deploy on any Windows machine
│   ├── config.json
│   ├── requirements.txt
│   ├── install.bat
│   ├── agent/
│   │   ├── main.py
│   │   ├── log_collector_windows.py
│   │   └── service_manager.py
│   ├── keys/                  # kafka_public.pem (do not commit)
│   └── services/
│       └── install_service.ps1
│
├── kafka_receiver/            # Deploy on Kafka broker VM
│   ├── config.json
│   ├── receiver.py
│   ├── decryption.py
│   ├── storage.py
│   ├── install.sh
│   └── keys/                  # kafka_receiver_private.pem (do not commit)
│
└── setup_keys.py              # Generate all RSA key pairs (run once)
```

## Setup

### 1. Kafka VM

Install Java and Kafka 3.6.2, then start Zookeeper and Kafka as systemd services.

### 2. Generate Keys (run once)

```bash
python3 setup_keys.py
```

Generates RSA-4096 key pairs for `linux_agent`, `windows_agent`, and `kafka_receiver`.  
Copies `kafka_receiver_public.pem` into each agent's `keys/` folder as `kafka_public.pem`.

> **Never commit `.pem` files.** Distribute keys to each machine out-of-band (e.g. SCP).

### 3. Linux Agent

```bash
cd linux_agent
sudo ./install.sh
# or run manually:
python3 agent/main.py --config config.json
```

### 4. Windows Agent

```bat
REM Run as Administrator
install.bat
```

Or manually:

```powershell
python agent\main.py --config config.json
```

### 5. Kafka Receiver

```bash
cd kafka_receiver
pip3 install -r requirements.txt
python3 receiver.py
```

Decrypted logs are stored under `received_logs/{machine_id}/`.

## Configuration

| Key | Description |
|-----|-------------|
| `machine_id` | `"auto"` to detect at runtime, or a fixed string |
| `kafka_broker` | `"host:port"` of the Kafka broker |
| `log_collection.interval_seconds` | Collection cycle interval |
| `log_collection.logs` | Map of log sources to collect |
| `encryption.public_key_path` | Path to `kafka_public.pem` |
| `resilience.buffer_max_size_mb` | Max local SQLite buffer size |
| `resilience.checkpoint_file` | Path to checkpoint file |

## Resilience

- Encrypted log batches are buffered locally in SQLite when Kafka is unreachable
- Buffered messages are flushed automatically on reconnect
- Linux: log rotation detected via inode tracking
- First run skips historical logs to avoid flooding the broker

## Requirements

- Python 3.8+
- `kafka-python==2.0.2`
- `cryptography==41.0.7`
- Linux: `adm` group membership or root (for `/var/log` access)
- Windows: Administrator privileges (for Event Log access)

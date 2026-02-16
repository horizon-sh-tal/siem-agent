# Chatterbox - ADAPT Honeypot Application

Active camouflage chat application with hidden log exfiltration for the ADAPT deception honeypot.

## Network Layout

| Machine | OS | IP | Role |
|---------|----|----|------|
| Dev1 | Ubuntu 20.04 | 192.168.27.200 | Linux log collection + Guest chat |
| Dev2 | Ubuntu 20.04 | (configure in config.json) | Linux log collection + Guest chat |
| Prof1 | Windows 10 | (configure in config.json) | Windows Event Log collection + Prof1 chat |
| Prof2 | Windows 10 | (configure in config.json) | Windows Event Log collection + Prof2 chat |
| Kafka | Ubuntu 20.04 | 192.168.27.211 | Kafka broker + Log receiver |

## Architecture

```
┌───────────────────────────────────────────────────────────┐
│                  Dev1 / Dev2 (Linux)                      │
│  ┌─────────────────┐       ┌─────────────────┐           │
│  │  main.py --chat │       │  main.py        │           │
│  │  (interactive   │       │  (background    │           │
│  │   chat CLI)     │       │   log collector)│           │
│  └───────┬─────────┘       └───────┬─────────┘           │
│          │ chat messages           │ encrypted logs       │
│          │ (Kafka)                 │ (RSA-4096 hybrid)    │
└──────────┼─────────────────────────┼──────────────────────┘
           │                         │
           └───────────┬─────────────┘
                       ↓
           ┌───────────────────────┐
           │   Kafka VM            │
           │  ┌─────────────────┐  │
           │  │ Kafka 3.6.2     │  │
           │  │ (systemd)       │  │
           │  └───────┬─────────┘  │
           │          ↓            │
           │  ┌─────────────────┐  │
           │  │ receiver.py     │  │
           │  │ (decrypts &     │  │
           │  │  stores logs)   │  │
           │  └─────────────────┘  │
           └───────────────────────┘
```

## Prerequisites

- **Kafka VM**: Java JDK, Apache Kafka 3.6.2, Python 3.8+
- **Dev VMs (Linux)**: Python 3.8+, `adm` group membership (for log access)
- **Prof VMs (Windows)**: Python 3.8+, Administrator access (for Event Logs)

---

## Step-by-Step Setup

### 1. Kafka VM Setup (192.168.27.211)

#### Install Java & Kafka (one-time)

```bash
# Install Java
sudo apt update && sudo apt install -y default-jdk

# Download and install Kafka
cd /opt
sudo wget https://archive.apache.org/dist/kafka/3.6.2/kafka_2.13-3.6.2.tgz
sudo tar -xzf kafka_2.13-3.6.2.tgz
sudo mv kafka_2.13-3.6.2 kafka
sudo rm kafka_2.13-3.6.2.tgz
sudo chown -R kafka:kafka /opt/kafka
```

#### Create systemd services (one-time)

```bash
# Zookeeper service
sudo tee /etc/systemd/system/zookeeper.service > /dev/null <<'EOF'
[Unit]
Description=Apache Zookeeper
After=network.target
[Service]
Type=simple
User=kafka
ExecStart=/opt/kafka/bin/zookeeper-server-start.sh /opt/kafka/config/zookeeper.properties
ExecStop=/opt/kafka/bin/zookeeper-server-stop.sh
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

# Kafka service
sudo tee /etc/systemd/system/kafka.service > /dev/null <<'EOF'
[Unit]
Description=Apache Kafka
After=zookeeper.service
Requires=zookeeper.service
[Service]
Type=simple
User=kafka
ExecStart=/opt/kafka/bin/kafka-server-start.sh /opt/kafka/config/server.properties
ExecStop=/opt/kafka/bin/kafka-server-stop.sh
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable zookeeper kafka
```

#### Configure Kafka for external access (one-time)

```bash
sudo sed -i 's|#listeners=PLAINTEXT://:9092|listeners=PLAINTEXT://0.0.0.0:9092|' /opt/kafka/config/server.properties
sudo sed -i 's|#advertised.listeners=PLAINTEXT://your.host.name:9092|advertised.listeners=PLAINTEXT://192.168.27.211:9092|' /opt/kafka/config/server.properties
```

#### Start Kafka

```bash
sudo systemctl start zookeeper
sudo systemctl start kafka

# Verify
sudo systemctl status kafka
ss -tlnp | grep 9092
```

#### Clone the repo and install Python dependencies

```bash
cd ~
git clone <your-repo-url> chatterbox
cd chatterbox/kafka_receiver
python3 -m pip install --user -r requirements.txt
```

#### Start the log receiver

```bash
cd ~/chatterbox/kafka_receiver
python3 receiver.py --config config.json --verbose
```

> Keep this running. Linux logs are stored as single files matching Ubuntu defaults:
> `received_logs/{machine_id}/syslog`, `auth.log`, `dpkg.log`, etc.
> Windows logs use date-based files: `received_logs/{machine_id}/{log_type}/{date}.log`

---

### 2. Generate RSA Keys (one-time, from any machine)

```bash
cd ~/chatterbox    # or wherever Chatterbox/ is cloned
python3 setup_keys.py
```

This generates RSA-4096 key pairs for all machines and distributes public keys automatically:
- Each client gets `keys/kafka_public.pem` (receiver's public key for encrypting logs)
- The receiver gets all client public keys in `kafka_receiver/keys/`

> After running, push to git and pull on all machines, or manually copy the `keys/` folders.

---

### 3. Dev1 Setup (192.168.27.200)

```bash
# Clone the repo
cd ~/Desktop
git clone <your-repo-url> chatterbox
cd chatterbox/dev1

# Install dependencies
pip3 install -r requirements.txt

# Add yourself to adm group (for reading /var/log/*)
sudo usermod -aG adm $(whoami)
newgrp adm

# Start log collector (with sudo for log access)
sudo python3 -m client.main --config config.json
```

**With chat:**
```bash
sudo python3 -m client.main --config config.json --chat
```

---

### 4. Dev2 Setup

Same as Dev1 but use the `dev2/` folder:
```bash
cd ~/Desktop/chatterbox/dev2
pip3 install -r requirements.txt
sudo python3 -m client.main --config config.json
```

---

### 5. Prof1 Setup (Windows)

```powershell
# Clone the repo
cd C:\Users\<user>\Desktop
git clone <your-repo-url> chatterbox
cd chatterbox\prof1

# Install dependencies
pip install -r requirements.txt

# Start log collector (run as Administrator)
python -m client.main --config config.json

# With chat:
python -m client.main --config config.json --chat
```

---

### 6. Prof2 Setup (Windows)

Same as Prof1 but use the `prof2\` folder:
```powershell
cd chatterbox\prof2
pip install -r requirements.txt
python -m client.main --config config.json
```

---

## Quick Start (After Initial Setup)

Once everything is installed, starting the full system only requires:

```
# 1. Kafka VM
sudo systemctl start zookeeper && sudo systemctl start kafka
cd ~/chatterbox/kafka_receiver && python3 receiver.py --config config.json --verbose

# 2. Dev1
cd ~/Desktop/chatterbox/dev1 && sudo python3 -m client.main --config config.json

# 3. Dev2
cd ~/Desktop/chatterbox/dev2 && sudo python3 -m client.main --config config.json

# 4. Prof1 (Admin PowerShell)
cd C:\...\chatterbox\prof1; python -m client.main --config config.json

# 5. Prof2 (Admin PowerShell)
cd C:\...\chatterbox\prof2; python -m client.main --config config.json
```

---

## Fixed Accounts

Only three accounts are allowed (hardcoded in `users.json`):

| Account | Role | Used By |
|---------|------|---------|
| **Prof1** | Professor / high-privilege | Prof1 VM |
| **Prof2** | Professor / high-privilege | Prof2 VM |
| **Guest** | Developer / low-privilege | Dev1, Dev2 VMs |

No other users can be created. `registration_disabled: true`.

---

## Log Topics

### Linux (6 logs per machine)

| # | Log Name | File Path | Kafka Topic |
|---|----------|-----------|-------------|
| 1 | syslog | /var/log/syslog | {machine}-syslog-message |
| 2 | altlog | /var/log/alternatives.log | {machine}-alternativelog-message |
| 3 | authlog | /var/log/auth.log | {machine}-authlog-message |
| 4 | dpkglog | /var/log/dpkg.log | {machine}-dpkglog-message |
| 5 | apthistorylog | /var/log/apt/history.log | {machine}-apthistory-message |
| 6 | apttermlog | /var/log/apt/term.log | {machine}-aptterm-message |

### Windows (9 event logs per machine)

| # | Log Name | Windows Channel | Kafka Topic |
|---|----------|----------------|-------------|
| 1 | security | Security | {machine}-wndsystemdsecurity |
| 2 | system | System | {machine}-wndsystemdsystem |
| 3 | bits_client | BITS-Client/Operational | {machine}-wndsystemdwindowsbit |
| 4 | applocker | AppLocker/EXE and DLL | {machine}-windowsapplocker |
| 5 | new_service | System (EventID 7045) | {machine}-windowsnewservice |
| 6 | bitlocker | BITS-Client (EventID 59) | {machine}-windowsbitlocker |
| 7 | firewall | Windows Firewall | {machine}-windowsfirewall |
| 8 | defender | Windows Defender | {machine}-windowsdefender |
| 9 | powershell | PowerShell/Operational | {machine}-windowspowershell |

### Chat Topics

- `chat-prof1-prof2` — Prof1 ↔ Prof2
- `chat-prof1-guest` — Prof1 ↔ Guest
- `chat-prof2-guest` — Prof2 ↔ Guest
- `chat-guest-group` — Guest broadcast

---

## Configuration

Each machine has a `config.json` with:

```json
{
  "machine_id": "dev1",
  "machine_type": "linux",
  "kafka_broker": "192.168.27.211:9092",
  "log_collection": {
    "interval_seconds": 30
  },
  "encryption": {
    "public_key_path": "keys/kafka_public.pem",
    "algorithm": "RSA-4096"
  },
  "chat": {
    "enabled": true,
    "account": "Guest"
  }
}
```

**Key settings:**
- `kafka_broker` — set to your Kafka VM's IP
- `interval_seconds` — log collection interval (default: 30s)
- `chat.account` — which of the 3 fixed accounts this machine uses

---

## Security Model

- **Encryption**: RSA-4096 with hybrid AES-256-CBC for payloads >446 bytes
- **Kafka transport**: PLAINTEXT (no TLS) — intentional for research honeypot
- **Authentication**: None on Kafka; hardcoded 3-account system for chat
- **Key management**: `setup_keys.py` generates and distributes all RSA key pairs

---

## Resilience Features

- **Checkpoint tracking**: JSON file tracks byte position per log file, prevents duplicate log shipping
- **Log rotation detection**: Inode-based detection for Linux log rotation
- **Kafka outage buffering**: SQLite-backed FIFO queue buffers logs locally when Kafka is unreachable
- **Auto-retry**: Reconnects to Kafka automatically, flushes buffer on reconnect
- **Graceful shutdown**: Ctrl+C once for graceful, twice to force exit

---

## File Structure

```
Chatterbox/
├── setup_keys.py              # RSA-4096 key generation for all machines
├── users.json                 # Hardcoded 3 accounts (Prof1, Prof2, Guest)
├── common/                    # Shared libraries
│   ├── encryption.py          #   RSA-4096 + hybrid AES-256 encryption
│   ├── checkpoint.py          #   Position tracking per log file
│   ├── kafka_utils.py         #   Resilient Kafka producer with buffering
│   ├── log_buffer.py          #   SQLite FIFO buffer
│   └── config_loader.py       #   Config validation
├── dev1/                      # Linux Dev Machine 1
│   ├── config.json
│   ├── requirements.txt
│   ├── client/
│   │   ├── main.py            #   Entry point (--config, --chat)
│   │   ├── log_collector_linux.py
│   │   ├── chat_interface.py
│   │   └── service_manager.py
│   ├── keys/                  #   RSA keys (generated by setup_keys.py)
│   ├── logs/                  #   Runtime: chatterbox.log, .checkpoint, buffer.db
│   └── services/              #   systemd unit file
├── dev2/                      # (same structure as dev1)
├── prof1/                     # Windows Prof Machine 1
│   ├── config.json
│   ├── requirements.txt
│   ├── client/
│   │   ├── main.py
│   │   ├── log_collector_windows.py
│   │   ├── chat_interface.py
│   │   └── service_manager.py
│   ├── keys/
│   ├── logs/
│   └── services/              #   PowerShell install script + .bat wrapper
├── prof2/                     # (same structure as prof1)
└── kafka_receiver/            # Kafka VM - Central receiver
    ├── config.json
    ├── receiver.py
    ├── decryption.py
    ├── storage.py
    ├── requirements.txt
    ├── keys/                  #   Receiver private key + all client public keys
    └── received_logs/         #   Output: Linux={machine}/syslog,auth.log,... Windows={machine}/{type}/{date}.log
```

---

## Testing End-to-End

### 1. Verify Kafka is running
```bash
# On Kafka VM
ss -tlnp | grep 9092
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### 2. Generate test log entries on Dev1
```bash
logger "CHATTERBOX-TEST-$(date +%s)"          # → syslog
sudo su -c "echo test"                        # → authlog
sudo dpkg --configure -a                      # → dpkglog
sudo apt install -y sl                        # → dpkglog + apthistory + aptterm
```

### 3. Verify on Dev1
```bash
grep "Collected" ~/Desktop/chatterbox/dev1/logs/chatterbox.log | tail -10
cat ~/Desktop/chatterbox/dev1/logs/.checkpoint
```

### 4. Verify on Kafka VM
```bash
/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
find ~/chatterbox/kafka_receiver/received_logs/ -type f
tail -10 ~/chatterbox/kafka_receiver/received_logs/dev1/syslog
tail -10 ~/chatterbox/kafka_receiver/received_logs/dev1/auth.log
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Permission denied reading /var/log/syslog` | Run with `sudo` or add user to `adm` group |
| `NoBrokersAvailable` | Start Kafka: `sudo systemctl start zookeeper && sudo systemctl start kafka` |
| `pip3` broken on Ubuntu 20.04 | Use `python3 -m pip install` instead |
| Process killed (OOM) | Normal on first run with huge logs — collector now starts from end of file |
| Checkpoint not saving | Fixed — uses reentrant lock (RLock) |
| New topics not appearing in receiver | Restart the receiver to re-subscribe |
| Ctrl+C doesn't stop | Press Ctrl+C twice for force exit |

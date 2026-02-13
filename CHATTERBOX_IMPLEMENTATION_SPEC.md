# Chatterbox Application - Complete Implementation Specification

## Project Overview
Implement the Chatterbox application from the ADAPT research paper for trapping Advanced Persistent Threats (APTs). This is a dual-purpose application providing secure chat functionality while covertly transmitting encrypted system logs to a Kafka broker for attacker behavior monitoring.

**Paper Reference**: ADAPT: Adaptive Camouflage Based Deception Orchestration For Trapping Advanced Persistent Threats
- Section 4 (Design): Pages 21:9-21:10
- Algorithm 3: Page 21:32
- Tables 2 & 3: Page 21:10

---

## Critical Non-Negotiable Requirements

### 1. User Account Restrictions
**ABSOLUTE REQUIREMENT - ZERO EXCEPTIONS:**
- **EXACTLY 3 user accounts ONLY**:
  - `Prof1` - Windows high-privileged user
  - `Prof2` - Windows high-privileged user  
  - `Guest` - Shared account for developers/researchers
- **NO user registration functionality**
- **NO admin interface to create users**
- **NO API endpoints to add users**
- Accounts hardcoded in application configuration
- Any user creation attempt must be blocked and logged

### 2. Current Deployment Architecture
```
PC1 (Host Machine)
├── VM1: Dev1 (Ubuntu 20.04 LTS)
│   └── Chatterbox Linux Client
└── VM2: Dev2 (Ubuntu 20.04 LTS)
    └── Chatterbox Linux Client

Future Expansion:
├── Prof1 VM (Windows 10)
├── Prof2 VM (Windows 10)
└── Kafka Broker (Separate server/VM)
```

### 3. Encryption Architecture
**Asymmetric Encryption (RSA-4096):**
- Each client encrypts logs with Kafka server's **PUBLIC key**
- Only Kafka receiver can decrypt with its **PRIVATE key**
- Clients have NO decryption capability
- Each machine has unique key pair for future use
- Keys stored in machine-specific `keys/` folders

---

## Project Structure

```
chatterbox/
├── README.md
├── requirements.txt
├── setup_keys.py                  # Generate all encryption keys
├── common/                        # Shared utilities
│   ├── __init__.py
│   ├── encryption.py              # RSA encryption/decryption
│   ├── kafka_utils.py             # Kafka producer/consumer helpers
│   └── config_loader.py           # Configuration management
│
├── dev1/                          # Linux client for Dev1 machine
│   ├── config.json
│   ├── client/
│   │   ├── __init__.py
│   │   ├── main.py                # Entry point
│   │   ├── chat_interface.py     # Chat GUI/CLI
│   │   ├── log_collector_linux.py # Linux log collection
│   │   ├── kafka_producer.py     # Send encrypted logs to Kafka
│   │   └── service_manager.py    # Service health monitoring
│   ├── keys/
│   │   ├── dev1_private.pem
│   │   ├── dev1_public.pem
│   │   └── kafka_public.pem      # For encrypting logs
│   ├── services/
│   │   └── chatterbox-dev1.service
│   ├── logs/                      # Local log buffer
│   │   └── .checkpoint            # Track last read position
│   └── install.sh                 # Installation script
│
├── dev2/                          # Linux client for Dev2 machine
│   ├── config.json
│   ├── client/
│   │   └── [same structure as dev1]
│   ├── keys/
│   │   ├── dev2_private.pem
│   │   ├── dev2_public.pem
│   │   └── kafka_public.pem
│   ├── services/
│   │   └── chatterbox-dev2.service
│   ├── logs/
│   └── install.sh
│
├── prof1/                         # Windows client for Prof1 machine
│   ├── config.json
│   ├── client/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── chat_interface.py
│   │   ├── log_collector_windows.py # Windows Event Log collection
│   │   ├── kafka_producer.py
│   │   └── service_manager.py
│   ├── keys/
│   │   ├── prof1_private.pem
│   │   ├── prof1_public.pem
│   │   └── kafka_public.pem
│   ├── services/
│   │   ├── install_service.ps1   # Windows service installation
│   │   └── service_config.xml
│   ├── logs/
│   └── install.bat
│
├── prof2/                         # Windows client for Prof2 machine
│   ├── config.json
│   ├── client/
│   │   └── [same structure as prof1]
│   ├── keys/
│   │   ├── prof2_private.pem
│   │   ├── prof2_public.pem
│   │   └── kafka_public.pem
│   ├── services/
│   │   ├── install_service.ps1
│   │   └── service_config.xml
│   ├── logs/
│   └── install.bat
│
└── kafka_receiver/                # Server-side log receiver & decryptor
    ├── config.json
    ├── receiver.py                # Main Kafka consumer
    ├── decryption.py              # Decrypt incoming logs
    ├── storage.py                 # Organize logs by machine/type
    ├── keys/
    │   ├── kafka_private.pem      # Master decryption key
    │   ├── kafka_public.pem
    │   ├── dev1_public.pem        # For verification (optional)
    │   ├── dev2_public.pem
    │   ├── prof1_public.pem
    │   └── prof2_public.pem
    ├── received_logs/
    │   ├── dev1/
    │   │   ├── syslog/
    │   │   ├── authlog/
    │   │   ├── dpkglog/
    │   │   ├── apthistory/
    │   │   ├── aptterm/
    │   │   └── altlog/
    │   ├── dev2/
    │   │   └── [same structure]
    │   ├── prof1/
    │   │   ├── security/
    │   │   ├── system/
    │   │   ├── bits_client/
    │   │   ├── applocker/
    │   │   ├── firewall/
    │   │   ├── defender/
    │   │   ├── powershell/
    │   │   ├── new_service/
    │   │   └── bitlocker/
    │   └── prof2/
    │       └── [same structure]
    ├── requirements.txt
    └── install.sh
```

---

## Linux Log Collection (Dev1, Dev2)

### Table 2 from Paper (Page 21:10)

| S.No | Log Name | Log File Location | Kafka Topic Pattern |
|------|----------|-------------------|---------------------|
| 1 | syslog | /var/log/syslog | dev{X}-syslog-message |
| 2 | altlog | /var/log/alternatives.log | dev{X}-alternativelog-message |
| 3 | authlog | /var/log/auth.log | dev{X}-authlog-message |
| 4 | dpkglog | /var/log/dpkg.log | dev{X}-dpkglog-message |
| 5 | apthistorylog | /var/log/apt/history.log | dev{X}-apthistory-message |
| 6 | apttermlog | /var/log/apt/term.log | dev{X}-aptterm-message |

**Note**: {X} = machine ID (1 or 2)

### Linux Configuration (config.json)
```json
{
  "machine_id": "dev1",
  "machine_type": "linux",
  "kafka_broker": "192.168.1.100:9092",
  "log_collection": {
    "interval_seconds": 3600,
    "logs": {
      "syslog": {
        "path": "/var/log/syslog",
        "topic": "dev1-syslog-message",
        "enabled": true
      },
      "altlog": {
        "path": "/var/log/alternatives.log",
        "topic": "dev1-alternativelog-message",
        "enabled": true
      },
      "authlog": {
        "path": "/var/log/auth.log",
        "topic": "dev1-authlog-message",
        "enabled": true
      },
      "dpkglog": {
        "path": "/var/log/dpkg.log",
        "topic": "dev1-dpkglog-message",
        "enabled": true
      },
      "apthistorylog": {
        "path": "/var/log/apt/history.log",
        "topic": "dev1-apthistory-message",
        "enabled": true
      },
      "apttermlog": {
        "path": "/var/log/apt/term.log",
        "topic": "dev1-aptterm-message",
        "enabled": true
      }
    }
  },
  "encryption": {
    "public_key_path": "keys/kafka_public.pem",
    "algorithm": "RSA-4096"
  },
  "resilience": {
    "buffer_max_size_mb": 100,
    "kafka_retry_interval_sec": 60,
    "checkpoint_file": "logs/.checkpoint"
  },
  "chat": {
    "enabled": true,
    "account": "Guest"
  }
}
```

### Linux Implementation Requirements

**log_collector_linux.py must:**
1. Read only NEW entries since last checkpoint (avoid duplicates)
2. Handle log rotation gracefully (detect when /var/log/syslog → syslog.1)
3. Track file position in `.checkpoint` file per log type
4. Batch log entries by collection interval (1 hour)
5. Encrypt batch with RSA public key
6. Send to specific Kafka topic
7. Buffer locally if Kafka unavailable
8. Resume from checkpoint after restart

**Key Functions:**
```python
class LinuxLogCollector:
    def __init__(self, config):
        self.config = config
        self.checkpoints = load_checkpoints()
        self.public_key = load_public_key(config['encryption']['public_key_path'])
        self.kafka_producer = create_kafka_producer(config['kafka_broker'])
    
    def collect_log(self, log_name, log_config):
        """Collect new entries from a specific log file"""
        last_position = self.checkpoints.get(log_name, 0)
        new_entries = read_log_from_position(log_config['path'], last_position)
        
        if new_entries:
            encrypted = encrypt_with_public_key(new_entries, self.public_key)
            send_to_kafka(self.kafka_producer, log_config['topic'], encrypted)
            update_checkpoint(log_name, current_position)
    
    def run_collection_cycle(self):
        """Execute one collection cycle for all enabled logs"""
        for log_name, log_config in self.config['log_collection']['logs'].items():
            if log_config['enabled']:
                self.collect_log(log_name, log_config)
    
    def start_periodic_collection(self):
        """Run collection every interval_seconds"""
        while True:
            self.run_collection_cycle()
            time.sleep(self.config['log_collection']['interval_seconds'])
```

---

## Windows Log Collection (Prof1, Prof2)

### Table 3 from Paper (Page 21:10)

| S.No | Event Log Name | Event ID Filter | Kafka Topic Pattern |
|------|----------------|-----------------|---------------------|
| 1 | Security | All | prof{X}-wndsystemdsecurity |
| 2 | System | All | prof{X}-wndsystemdsystem |
| 3 | Microsoft-Windows-Bits-Client/Operational | All | prof{X}-wndsystemdwindowsbit |
| 4 | Microsoft-Windows-AppLocker/EXE and DLL | All | prof{X}-windowsapplocker |
| 5 | System | 7045 only | prof{X}-windowsnewservice |
| 6 | Microsoft-Windows-Bits-Client/Operational | 59 only | prof{X}-windowsbitlocker |
| 7 | Microsoft-Windows-Windows Firewall With Advanced Security/Firewall | All | prof{X}-windowsfirewall |
| 8 | Microsoft-Windows-Windows Defender/Operational | All | prof{X}-windowsdefender |
| 9 | Microsoft-Windows-PowerShell/Operational | All | prof{X}-windowspowershell |

**Note**: {X} = machine ID (1 or 2)

### Windows Configuration (config.json)
```json
{
  "machine_id": "prof1",
  "machine_type": "windows",
  "kafka_broker": "192.168.1.100:9092",
  "log_collection": {
    "interval_seconds": 3600,
    "logs": {
      "security": {
        "log_name": "Security",
        "event_id": null,
        "topic": "prof1-wndsystemdsecurity",
        "enabled": true
      },
      "system": {
        "log_name": "System",
        "event_id": null,
        "topic": "prof1-wndsystemdsystem",
        "enabled": true
      },
      "bits_client": {
        "log_name": "Microsoft-Windows-Bits-Client/Operational",
        "event_id": null,
        "topic": "prof1-wndsystemdwindowsbit",
        "enabled": true
      },
      "applocker": {
        "log_name": "Microsoft-Windows-AppLocker/EXE and DLL",
        "event_id": null,
        "topic": "prof1-windowsapplocker",
        "enabled": true
      },
      "new_service": {
        "log_name": "System",
        "event_id": 7045,
        "topic": "prof1-windowsnewservice",
        "enabled": true
      },
      "bitlocker": {
        "log_name": "Microsoft-Windows-Bits-Client/Operational",
        "event_id": 59,
        "topic": "prof1-windowsbitlocker",
        "enabled": true
      },
      "firewall": {
        "log_name": "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall",
        "event_id": null,
        "topic": "prof1-windowsfirewall",
        "enabled": true
      },
      "defender": {
        "log_name": "Microsoft-Windows-Windows Defender/Operational",
        "event_id": null,
        "topic": "prof1-windowsdefender",
        "enabled": true
      },
      "powershell": {
        "log_name": "Microsoft-Windows-PowerShell/Operational",
        "event_id": null,
        "topic": "prof1-windowspowershell",
        "enabled": true
      }
    }
  },
  "encryption": {
    "public_key_path": "keys\\kafka_public.pem",
    "algorithm": "RSA-4096"
  },
  "resilience": {
    "buffer_max_size_mb": 100,
    "kafka_retry_interval_sec": 60,
    "checkpoint_file": "logs\\.checkpoint"
  },
  "chat": {
    "enabled": true,
    "account": "Prof1"
  }
}
```

### Windows Implementation Requirements

**log_collector_windows.py must:**
1. Use `win32evtlog` or PowerShell `Get-WinEvent` API
2. Track last processed Event Record ID (avoid duplicates)
3. Filter by Event ID where specified (7045, 59)
4. Convert events to JSON format
5. Encrypt with RSA public key
6. Send to specific Kafka topic
7. Buffer locally if Kafka unavailable
8. Persist checkpoint in registry or file

**Key Functions:**
```python
import win32evtlog
import win32con

class WindowsLogCollector:
    def __init__(self, config):
        self.config = config
        self.checkpoints = load_checkpoints()
        self.public_key = load_public_key(config['encryption']['public_key_path'])
        self.kafka_producer = create_kafka_producer(config['kafka_broker'])
    
    def collect_event_log(self, log_name, log_config):
        """Collect new events from Windows Event Log"""
        last_record_id = self.checkpoints.get(log_name, 0)
        
        # Open event log
        hand = win32evtlog.OpenEventLog(None, log_config['log_name'])
        flags = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        
        new_events = []
        events = win32evtlog.ReadEventLog(hand, flags, 0)
        
        for event in events:
            if event.RecordNumber > last_record_id:
                # Apply Event ID filter if specified
                if log_config.get('event_id') is None or event.EventID == log_config['event_id']:
                    event_data = {
                        'RecordNumber': event.RecordNumber,
                        'TimeGenerated': str(event.TimeGenerated),
                        'EventID': event.EventID,
                        'EventCategory': event.EventCategory,
                        'SourceName': event.SourceName,
                        'StringInserts': event.StringInserts,
                        'Data': event.Data
                    }
                    new_events.append(event_data)
        
        win32evtlog.CloseEventLog(hand)
        
        if new_events:
            encrypted = encrypt_with_public_key(json.dumps(new_events), self.public_key)
            send_to_kafka(self.kafka_producer, log_config['topic'], encrypted)
            update_checkpoint(log_name, events[-1].RecordNumber)
    
    def run_collection_cycle(self):
        """Execute one collection cycle for all enabled logs"""
        for log_name, log_config in self.config['log_collection']['logs'].items():
            if log_config['enabled']:
                try:
                    self.collect_event_log(log_name, log_config)
                except Exception as e:
                    log_error(f"Failed to collect {log_name}: {e}")
    
    def start_periodic_collection(self):
        """Run collection every interval_seconds"""
        while True:
            self.run_collection_cycle()
            time.sleep(self.config['log_collection']['interval_seconds'])
```

---

## Encryption Implementation

### RSA-4096 Asymmetric Encryption

**common/encryption.py:**
```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
import os

class RSAEncryption:
    """Handle RSA-4096 encryption/decryption for log transmission"""
    
    @staticmethod
    def generate_key_pair(private_key_path, public_key_path):
        """Generate new RSA-4096 key pair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        
        # Save private key
        with open(private_key_path, 'wb') as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Save public key
        public_key = private_key.public_key()
        with open(public_key_path, 'wb') as f:
            f.write(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ))
        
        # Set secure permissions
        os.chmod(private_key_path, 0o600)
        os.chmod(public_key_path, 0o644)
    
    @staticmethod
    def load_public_key(public_key_path):
        """Load public key from file"""
        with open(public_key_path, 'rb') as f:
            return serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
    
    @staticmethod
    def load_private_key(private_key_path):
        """Load private key from file"""
        with open(private_key_path, 'rb') as f:
            return serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
    
    @staticmethod
    def encrypt(data, public_key):
        """
        Encrypt data with public key (for client-side log encryption)
        
        Note: RSA has size limits. For large data, use hybrid encryption:
        1. Generate random AES-256 key
        2. Encrypt data with AES key
        3. Encrypt AES key with RSA public key
        4. Send both encrypted AES key + encrypted data
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # For data larger than RSA block size, use hybrid encryption
        if len(data) > 446:  # RSA-4096 max plaintext = 446 bytes
            return RSAEncryption._hybrid_encrypt(data, public_key)
        
        # Direct RSA encryption for small data
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    
    @staticmethod
    def _hybrid_encrypt(data, public_key):
        """Hybrid encryption: AES-256 for data, RSA for AES key"""
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        
        # Generate random AES-256 key
        aes_key = os.urandom(32)
        iv = os.urandom(16)
        
        # Encrypt data with AES
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Pad data to AES block size
        from cryptography.hazmat.primitives import padding as sym_padding
        padder = sym_padding.PKCS7(128).padder()
        padded_data = padder.update(data) + padder.finalize()
        
        encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
        
        # Encrypt AES key with RSA
        encrypted_aes_key = public_key.encrypt(
            aes_key + iv,  # Send both key and IV
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Combine: [4 bytes length of encrypted key][encrypted key][encrypted data]
        import struct
        result = struct.pack('!I', len(encrypted_aes_key)) + encrypted_aes_key + encrypted_data
        return result
    
    @staticmethod
    def decrypt(ciphertext, private_key):
        """
        Decrypt data with private key (for Kafka receiver)
        Handles both direct RSA and hybrid encryption
        """
        import struct
        
        # Check if this is hybrid encryption (has length prefix)
        if len(ciphertext) > 512:  # RSA-4096 ciphertext is 512 bytes
            # Hybrid decryption
            key_length = struct.unpack('!I', ciphertext[:4])[0]
            encrypted_aes_key = ciphertext[4:4+key_length]
            encrypted_data = ciphertext[4+key_length:]
            
            # Decrypt AES key
            aes_key_and_iv = private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            aes_key = aes_key_and_iv[:32]
            iv = aes_key_and_iv[32:]
            
            # Decrypt data with AES
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Unpad
            from cryptography.hazmat.primitives import padding as sym_padding
            unpadder = sym_padding.PKCS7(128).unpadder()
            data = unpadder.update(padded_data) + unpadder.finalize()
            return data
        
        # Direct RSA decryption
        plaintext = private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext
```

### Key Generation Script

**setup_keys.py:**
```python
#!/usr/bin/env python3
"""
Generate all RSA key pairs for Chatterbox deployment
Run this ONCE before deploying to any machine
"""

import os
from common.encryption import RSAEncryption

def setup_all_keys():
    """Generate keys for all machines and Kafka receiver"""
    
    machines = ['dev1', 'dev2', 'prof1', 'prof2', 'kafka_receiver']
    
    for machine in machines:
        key_dir = f"{machine}/keys"
        os.makedirs(key_dir, exist_ok=True)
        
        private_key_path = f"{key_dir}/{machine}_private.pem"
        public_key_path = f"{key_dir}/{machine}_public.pem"
        
        print(f"Generating keys for {machine}...")
        RSAEncryption.generate_key_pair(private_key_path, public_key_path)
    
    # Copy Kafka public key to all client machines
    kafka_public_key = "kafka_receiver/keys/kafka_receiver_public.pem"
    
    for client in ['dev1', 'dev2', 'prof1', 'prof2']:
        dest = f"{client}/keys/kafka_public.pem"
        with open(kafka_public_key, 'rb') as src_file:
            with open(dest, 'wb') as dst_file:
                dst_file.write(src_file.read())
        print(f"Copied Kafka public key to {client}")
    
    # Copy all client public keys to Kafka receiver (for verification)
    for client in ['dev1', 'dev2', 'prof1', 'prof2']:
        src = f"{client}/keys/{client}_public.pem"
        dest = f"kafka_receiver/keys/{client}_public.pem"
        with open(src, 'rb') as src_file:
            with open(dest, 'wb') as dst_file:
                dst_file.write(src_file.read())
        print(f"Copied {client} public key to Kafka receiver")
    
    print("\n✅ All keys generated successfully!")
    print("⚠️  Keep all *_private.pem files SECRET and on their respective machines only!")

if __name__ == "__main__":
    setup_all_keys()
```

---

## Chat Functionality

### User Accounts (HARDCODED)

**users.json (shared across all machines):**
```json
{
  "users": {
    "Prof1": {
      "password_hash": "scrypt$32768$8$1$...",
      "role": "professor",
      "machine": "prof1",
      "can_chat_with": ["Prof2", "Guest"]
    },
    "Prof2": {
      "password_hash": "scrypt$32768$8$1$...",
      "role": "professor",
      "machine": "prof2",
      "can_chat_with": ["Prof1", "Guest"]
    },
    "Guest": {
      "password_hash": "scrypt$32768$8$1$...",
      "role": "researcher",
      "machine": "any",
      "can_chat_with": ["Prof1", "Prof2", "Guest"]
    }
  },
  "registration_disabled": true
}
```

### Chat Topics in Kafka
```
chat-prof1-prof2      # Direct messages between professors
chat-prof1-guest      # Prof1 ↔ Researchers
chat-prof2-guest      # Prof2 ↔ Researchers
chat-guest-group      # Group chat for all Guest users
```

### Chat Implementation

**chat_interface.py:**
```python
import threading
from kafka import KafkaProducer, KafkaConsumer
import json
from datetime import datetime
from common.encryption import RSAEncryption  # For chat message encryption (optional)

class ChatInterface:
    """Simple chat interface using Kafka as message broker"""
    
    def __init__(self, config, username, password):
        self.config = config
        self.username = username
        
        # Authenticate user (check against hardcoded users.json)
        if not self.authenticate(username, password):
            raise ValueError("Invalid credentials")
        
        # Load user permissions
        self.user_info = self.load_user_info(username)
        
        # Kafka setup
        self.producer = KafkaProducer(
            bootstrap_servers=config['kafka_broker'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Subscribe to relevant chat topics
        self.consumer = KafkaConsumer(
            *self.get_subscribed_topics(),
            bootstrap_servers=config['kafka_broker'],
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            group_id=f'chat-{username}',
            auto_offset_reset='latest'
        )
        
        # Start listening thread
        self.running = True
        self.listener_thread = threading.Thread(target=self.listen_for_messages, daemon=True)
        self.listener_thread.start()
    
    def authenticate(self, username, password):
        """Verify credentials against hardcoded users"""
        with open('users.json', 'r') as f:
            users_db = json.load(f)
        
        if users_db.get('registration_disabled', True) is False:
            raise RuntimeError("User registration must be disabled!")
        
        if username not in users_db['users']:
            return False
        
        # Verify password hash (use scrypt or bcrypt)
        from passlib.hash import scrypt
        stored_hash = users_db['users'][username]['password_hash']
        return scrypt.verify(password, stored_hash)
    
    def load_user_info(self, username):
        """Load user permissions and allowed contacts"""
        with open('users.json', 'r') as f:
            users_db = json.load(f)
        return users_db['users'][username]
    
    def get_subscribed_topics(self):
        """Get list of Kafka topics this user should listen to"""
        topics = []
        
        if self.username == "Prof1":
            topics = ["chat-prof1-prof2", "chat-prof1-guest"]
        elif self.username == "Prof2":
            topics = ["chat-prof1-prof2", "chat-prof2-guest"]
        elif self.username == "Guest":
            topics = ["chat-prof1-guest", "chat-prof2-guest", "chat-guest-group"]
        
        return topics
    
    def send_message(self, recipient, message):
        """Send message to another user or group"""
        if recipient not in self.user_info['can_chat_with']:
            print(f"❌ You cannot send messages to {recipient}")
            return
        
        # Determine topic
        topic = self.get_chat_topic(self.username, recipient)
        
        msg_data = {
            'from': self.username,
            'to': recipient,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.producer.send(topic, msg_data)
        self.producer.flush()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] You → {recipient}: {message}")
    
    def get_chat_topic(self, sender, recipient):
        """Determine Kafka topic for this conversation"""
        if sender == "Guest" or recipient == "Guest":
            if "Prof" in sender or "Prof" in recipient:
                prof = sender if "Prof" in sender else recipient
                return f"chat-{prof.lower()}-guest"
            else:
                return "chat-guest-group"
        else:
            # Prof1 ↔ Prof2
            return "chat-prof1-prof2"
    
    def listen_for_messages(self):
        """Background thread to receive messages"""
        for message in self.consumer:
            msg_data = message.value
            
            # Don't show our own messages
            if msg_data['from'] == self.username:
                continue
            
            timestamp = datetime.fromisoformat(msg_data['timestamp']).strftime('%H:%M:%S')
            print(f"\n[{timestamp}] {msg_data['from']}: {msg_data['message']}")
            print("> ", end='', flush=True)  # Re-print prompt
    
    def start_cli(self):
        """Simple CLI chat interface"""
        print(f"\n=== Chatterbox Chat ===")
        print(f"Logged in as: {self.username}")
        print(f"You can chat with: {', '.join(self.user_info['can_chat_with'])}")
        print("Commands: /quit to exit")
        print("=" * 40)
        
        while self.running:
            try:
                user_input = input("> ")
                
                if user_input == "/quit":
                    self.running = False
                    break
                
                # Parse: @recipient message
                if user_input.startswith("@"):
                    parts = user_input[1:].split(" ", 1)
                    if len(parts) == 2:
                        recipient, message = parts
                        self.send_message(recipient, message)
                    else:
                        print("Usage: @Recipient Your message here")
                else:
                    print("Start messages with @Recipient")
            
            except KeyboardInterrupt:
                self.running = False
                break
        
        print("\nGoodbye!")
        self.consumer.close()
        self.producer.close()

# Usage in main.py
if __name__ == "__main__":
    config = load_config('config.json')
    
    # Get credentials (in real deployment, use secure input)
    username = config['chat']['account']
    password = input("Password: ")
    
    chat = ChatInterface(config, username, password)
    chat.start_cli()
```

---

## Service Installation

### Linux systemd Service

**services/chatterbox-dev1.service:**
```ini
[Unit]
Description=Chatterbox Application - Dev1 Machine
Documentation=https://github.com/your-org/chatterbox
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/chatterbox/dev1
ExecStart=/usr/bin/python3 /opt/chatterbox/dev1/client/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/chatterbox/dev1/logs
ReadOnlyPaths=/var/log

# Resource limits
MemoryMax=512M
CPUQuota=50%

# Prevent service from being killed easily
KillMode=process
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

**Installation script (install.sh):**
```bash
#!/bin/bash
# Install Chatterbox on Linux (Dev1/Dev2)

set -e

MACHINE_ID="dev1"  # Change for dev2
INSTALL_DIR="/opt/chatterbox/$MACHINE_ID"

echo "🚀 Installing Chatterbox for $MACHINE_ID..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (sudo ./install.sh)"
    exit 1
fi

# Create installation directory
mkdir -p $INSTALL_DIR
cp -r client/ $INSTALL_DIR/
cp -r keys/ $INSTALL_DIR/
cp -r logs/ $INSTALL_DIR/
cp config.json $INSTALL_DIR/

# Install Python dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Copy systemd service file
cp services/chatterbox-$MACHINE_ID.service /etc/systemd/system/

# Make service file immutable (harder to modify)
chattr +i /etc/systemd/system/chatterbox-$MACHINE_ID.service

# Set secure permissions
chmod 700 $INSTALL_DIR/client/
chmod 600 $INSTALL_DIR/keys/*.pem
chmod 600 $INSTALL_DIR/config.json

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable chatterbox-$MACHINE_ID.service
systemctl start chatterbox-$MACHINE_ID.service

# Check status
sleep 2
systemctl status chatterbox-$MACHINE_ID.service

echo "✅ Chatterbox installed successfully!"
echo "📊 Check logs: journalctl -u chatterbox-$MACHINE_ID -f"
```

### Windows Service Installation

**services/install_service.ps1:**
```powershell
# Install Chatterbox as Windows Service
# Run as Administrator

param(
    [Parameter(Mandatory=$true)]
    [string]$MachineId  # "prof1" or "prof2"
)

$ErrorActionPreference = "Stop"

$InstallDir = "C:\Chatterbox\$MachineId"
$ServiceName = "Chatterbox$MachineId"
$DisplayName = "System Monitoring Service"  # Camouflaged name
$PythonExe = "C:\Python39\python.exe"
$MainScript = "$InstallDir\client\main.py"

Write-Host "🚀 Installing Chatterbox for $MachineId..." -ForegroundColor Green

# Check if running as Administrator
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "❌ Please run as Administrator" -ForegroundColor Red
    exit 1
}

# Create installation directory
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Recurse -Force "client\" "$InstallDir\"
Copy-Item -Recurse -Force "keys\" "$InstallDir\"
Copy-Item -Recurse -Force "logs\" "$InstallDir\"
Copy-Item -Force "config.json" "$InstallDir\"

# Install Python dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
& pip install -r requirements.txt

# Install NSSM (Non-Sucking Service Manager) for easy service creation
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Host "Installing NSSM..." -ForegroundColor Yellow
    choco install nssm -y
}

# Remove existing service if present
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Removing existing service..." -ForegroundColor Yellow
    nssm stop $ServiceName
    nssm remove $ServiceName confirm
}

# Install service using NSSM
Write-Host "Creating Windows service..." -ForegroundColor Yellow
nssm install $ServiceName $PythonExe $MainScript
nssm set $ServiceName AppDirectory $InstallDir
nssm set $ServiceName DisplayName $DisplayName
nssm set $ServiceName Description "Chatterbox monitoring and communication service"
nssm set $ServiceName Start SERVICE_AUTO_START

# Set failure actions (restart on failure)
nssm set $ServiceName AppExit Default Restart
nssm set $ServiceName AppRestartDelay 10000  # 10 seconds
nssm set $ServiceName AppStdout "$InstallDir\logs\service_stdout.log"
nssm set $ServiceName AppStderr "$InstallDir\logs\service_stderr.log"

# Set service to run as LocalSystem (required for Event Log access)
nssm set $ServiceName ObjectName LocalSystem

# Secure file permissions
Write-Host "Setting secure permissions..." -ForegroundColor Yellow
icacls "$InstallDir\keys" /inheritance:r /grant "SYSTEM:(OI)(CI)F" /T
icacls "$InstallDir\config.json" /inheritance:r /grant "SYSTEM:F"

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
nssm start $ServiceName

# Wait and check status
Start-Sleep -Seconds 3
$status = nssm status $ServiceName

if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✅ Chatterbox installed and running successfully!" -ForegroundColor Green
    Write-Host "📊 Check logs at: $InstallDir\logs\" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  Service installed but not running. Status: $status" -ForegroundColor Yellow
    Write-Host "Check logs for errors: $InstallDir\logs\service_stderr.log" -ForegroundColor Yellow
}

Write-Host "`n🔍 Service Information:" -ForegroundColor Cyan
nssm status $ServiceName
```

---

## Kafka Receiver Implementation

**receiver.py:**
```python
#!/usr/bin/env python3
"""
Kafka Log Receiver - Decrypts and stores logs from all Chatterbox clients
"""

import json
import os
from datetime import datetime
from kafka import KafkaConsumer
from common.encryption import RSAEncryption
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChatterboxLogReceiver:
    """Consume, decrypt, and store logs from all machines"""
    
    def __init__(self, config_path='config.json'):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Load Kafka private key for decryption
        self.private_key = RSAEncryption.load_private_key(
            self.config['encryption']['private_key_path']
        )
        
        # Create Kafka consumer
        # Subscribe to all Chatterbox log topics (not chat topics)
        topic_pattern = self.config['kafka']['topic_pattern']  # e.g., "dev.*|prof.*"
        
        self.consumer = KafkaConsumer(
            bootstrap_servers=self.config['kafka']['bootstrap_servers'],
            group_id=self.config['kafka']['group_id'],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            value_deserializer=lambda m: m  # Don't deserialize yet (encrypted)
        )
        
        # Subscribe with pattern matching
        self.consumer.subscribe(pattern=topic_pattern)
        
        logger.info(f"Kafka receiver started. Listening for topics matching: {topic_pattern}")
    
    def parse_topic_name(self, topic):
        """
        Extract machine ID and log type from topic name
        Examples:
            dev1-syslog-message → (dev1, syslog)
            prof2-windowsdefender → (prof2, defender)
        """
        parts = topic.split('-')
        machine_id = parts[0]  # dev1, dev2, prof1, prof2
        log_type = '-'.join(parts[1:])  # syslog-message, windowsdefender, etc.
        
        # Simplify log type name for folder structure
        log_type_simple = log_type.replace('-message', '').replace('wndsystemd', '').replace('windows', '')
        
        return machine_id, log_type_simple
    
    def store_logs(self, machine_id, log_type, decrypted_data, timestamp):
        """
        Store decrypted logs in organized folder structure
        Format: received_logs/{machine_id}/{log_type}/{date}.log
        """
        # Create directory structure
        log_dir = os.path.join(
            self.config['storage']['base_dir'],
            machine_id,
            log_type
        )
        os.makedirs(log_dir, exist_ok=True)
        
        # Generate filename with date
        date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
        log_file = os.path.join(log_dir, f"{date_str}.log")
        
        # Append logs to file
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {datetime.fromtimestamp(timestamp / 1000).isoformat()}\n")
            f.write(f"Machine: {machine_id} | Log Type: {log_type}\n")
            f.write(f"{'='*80}\n")
            
            # Write decrypted log data
            try:
                # Try to parse as JSON for pretty printing
                log_data = json.loads(decrypted_data)
                f.write(json.dumps(log_data, indent=2))
            except json.JSONDecodeError:
                # Write as plain text if not JSON
                f.write(decrypted_data)
            
            f.write("\n")
        
        logger.info(f"Stored logs: {machine_id}/{log_type} → {log_file}")
    
    def process_message(self, message):
        """Process single Kafka message: decrypt and store"""
        try:
            topic = message.topic
            encrypted_data = message.value
            timestamp = message.timestamp
            
            # Parse topic to get machine ID and log type
            machine_id, log_type = self.parse_topic_name(topic)
            
            # Decrypt the log data
            decrypted_bytes = RSAEncryption.decrypt(encrypted_data, self.private_key)
            decrypted_data = decrypted_bytes.decode('utf-8')
            
            # Store in appropriate folder
            self.store_logs(machine_id, log_type, decrypted_data, timestamp)
            
        except Exception as e:
            logger.error(f"Failed to process message from {topic}: {e}", exc_info=True)
    
    def run(self):
        """Main consumer loop"""
        logger.info("Starting to consume messages...")
        
        try:
            for message in self.consumer:
                self.process_message(message)
        
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
        
        finally:
            self.consumer.close()
            logger.info("Consumer closed")

if __name__ == "__main__":
    receiver = ChatterboxLogReceiver('config.json')
    receiver.run()
```

**config.json (Kafka Receiver):**
```json
{
  "kafka": {
    "bootstrap_servers": ["localhost:9092"],
    "group_id": "chatterbox-log-receiver",
    "topic_pattern": "^(dev1|dev2|prof1|prof2)-.*"
  },
  "encryption": {
    "private_key_path": "keys/kafka_receiver_private.pem"
  },
  "storage": {
    "base_dir": "received_logs"
  }
}
```

---

## Failure Handling & Resilience

### Local Log Buffering

**common/log_buffer.py:**
```python
import sqlite3
import json
from datetime import datetime
import os

class LocalLogBuffer:
    """
    SQLite-based buffer for logs when Kafka is unavailable
    Implements FIFO queue with max size limit
    """
    
    def __init__(self, db_path, max_size_mb=100):
        self.db_path = db_path
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_table()
    
    def create_table(self):
        """Create buffer table if not exists"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS log_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                topic TEXT,
                encrypted_data BLOB,
                size_bytes INTEGER
            )
        ''')
        self.conn.commit()
    
    def add(self, topic, encrypted_data):
        """Add encrypted log to buffer"""
        timestamp = datetime.utcnow().isoformat()
        size_bytes = len(encrypted_data)
        
        # Check total buffer size
        current_size = self.get_total_size()
        
        # If buffer full, remove oldest entries (FIFO)
        while current_size + size_bytes > self.max_size_bytes:
            self.remove_oldest()
            current_size = self.get_total_size()
        
        # Insert new entry
        self.conn.execute(
            'INSERT INTO log_buffer (timestamp, topic, encrypted_data, size_bytes) VALUES (?, ?, ?, ?)',
            (timestamp, topic, encrypted_data, size_bytes)
        )
        self.conn.commit()
    
    def get_total_size(self):
        """Get total size of buffered data in bytes"""
        cursor = self.conn.execute('SELECT SUM(size_bytes) FROM log_buffer')
        result = cursor.fetchone()[0]
        return result if result else 0
    
    def remove_oldest(self):
        """Remove oldest buffered entry"""
        self.conn.execute('DELETE FROM log_buffer WHERE id = (SELECT MIN(id) FROM log_buffer)')
        self.conn.commit()
    
    def get_all(self):
        """Retrieve all buffered entries"""
        cursor = self.conn.execute('SELECT id, topic, encrypted_data FROM log_buffer ORDER BY id')
        return cursor.fetchall()
    
    def remove(self, entry_id):
        """Remove specific entry after successful transmission"""
        self.conn.execute('DELETE FROM log_buffer WHERE id = ?', (entry_id,))
        self.conn.commit()
    
    def count(self):
        """Get number of buffered entries"""
        cursor = self.conn.execute('SELECT COUNT(*) FROM log_buffer')
        return cursor.fetchone()[0]
    
    def close(self):
        """Close database connection"""
        self.conn.close()
```

### Enhanced Kafka Producer with Buffering

**common/kafka_utils.py:**
```python
from kafka import KafkaProducer
from kafka.errors import KafkaError, NoBrokersAvailable
import time
import logging
from .log_buffer import LocalLogBuffer

logger = logging.getLogger(__name__)

class ResilientKafkaProducer:
    """
    Kafka producer with automatic buffering and retry logic
    Handles network failures and Kafka unavailability
    """
    
    def __init__(self, bootstrap_servers, buffer_db_path, max_buffer_mb=100):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None
        self.buffer = LocalLogBuffer(buffer_db_path, max_buffer_mb)
        self.connect()
    
    def connect(self):
        """Attempt to connect to Kafka broker"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                max_block_ms=5000,  # Don't block forever
                request_timeout_ms=10000
            )
            logger.info("Connected to Kafka broker")
            return True
        except NoBrokersAvailable:
            logger.warning("Kafka broker unavailable. Will buffer logs locally.")
            self.producer = None
            return False
    
    def send(self, topic, encrypted_data):
        """
        Send encrypted data to Kafka topic
        Falls back to local buffer if Kafka unavailable
        """
        # Try to send buffered messages first
        self.flush_buffer()
        
        # Try to send current message
        if self.producer:
            try:
                future = self.producer.send(topic, encrypted_data)
                future.get(timeout=10)  # Wait for confirmation
                logger.debug(f"Sent to Kafka: {topic}")
                return True
            except KafkaError as e:
                logger.error(f"Kafka send failed: {e}. Buffering locally.")
                self.producer = None  # Mark as disconnected
        
        # Buffer if Kafka unavailable
        self.buffer.add(topic, encrypted_data)
        logger.info(f"Buffered locally: {topic} ({self.buffer.count()} in queue)")
        return False
    
    def flush_buffer(self):
        """
        Attempt to send all buffered messages
        Called periodically and before each new send
        """
        if not self.producer:
            # Try to reconnect
            self.connect()
        
        if not self.producer:
            return  # Still no connection
        
        buffered = self.buffer.get_all()
        
        for entry_id, topic, encrypted_data in buffered:
            try:
                future = self.producer.send(topic, encrypted_data)
                future.get(timeout=10)
                
                # Success - remove from buffer
                self.buffer.remove(entry_id)
                logger.info(f"Flushed buffered message: {topic}")
                
            except KafkaError as e:
                logger.warning(f"Failed to flush buffered message: {e}")
                break  # Stop trying if we hit an error
    
    def close(self):
        """Close producer and buffer"""
        if self.producer:
            self.producer.flush()
            self.producer.close()
        self.buffer.close()
```

### Checkpoint Management

**common/checkpoint.py:**
```python
import json
import os
from threading import Lock

class CheckpointManager:
    """
    Track last read position for each log file
    Prevents duplicate log entries after restart
    """
    
    def __init__(self, checkpoint_file):
        self.checkpoint_file = checkpoint_file
        self.checkpoints = {}
        self.lock = Lock()
        self.load()
    
    def load(self):
        """Load checkpoints from file"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                self.checkpoints = json.load(f)
    
    def save(self):
        """Save checkpoints to file"""
        with self.lock:
            # Atomic write (write to temp file, then rename)
            temp_file = self.checkpoint_file + '.tmp'
            with open(temp_file, 'w') as f:
                json.dump(self.checkpoints, f, indent=2)
            os.replace(temp_file, self.checkpoint_file)
    
    def get(self, log_name, default=0):
        """Get last checkpoint for a log"""
        return self.checkpoints.get(log_name, default)
    
    def update(self, log_name, position):
        """Update checkpoint for a log"""
        with self.lock:
            self.checkpoints[log_name] = position
            self.save()
    
    def get_all(self):
        """Get all checkpoints"""
        return self.checkpoints.copy()
```

---

## Main Entry Point

**client/main.py (for all machines):**
```python
#!/usr/bin/env python3
"""
Chatterbox Main Entry Point
Handles both log collection and chat functionality
"""

import sys
import os
import signal
import threading
import time
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.config_loader import load_config
from common.checkpoint import CheckpointManager
from common.kafka_utils import ResilientKafkaProducer

# Import appropriate log collector based on OS
if sys.platform == 'win32':
    from client.log_collector_windows import WindowsLogCollector as LogCollector
else:
    from client.log_collector_linux import LinuxLogCollector as LogCollector

from client.chat_interface import ChatInterface

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/chatterbox.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ChatterboxApplication:
    """Main application managing log collection and chat"""
    
    def __init__(self, config_path='config.json'):
        self.config = load_config(config_path)
        self.running = True
        
        # Initialize components
        self.checkpoint_manager = CheckpointManager(
            self.config['resilience']['checkpoint_file']
        )
        
        self.kafka_producer = ResilientKafkaProducer(
            self.config['kafka_broker'],
            'logs/buffer.db',
            self.config['resilience']['buffer_max_size_mb']
        )
        
        self.log_collector = LogCollector(
            self.config,
            self.checkpoint_manager,
            self.kafka_producer
        )
        
        # Chat interface (optional, for testing)
        self.chat = None
        if self.config['chat']['enabled']:
            # In production, chat would run separately
            # For now, just initialize but don't start
            pass
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_shutdown)
        signal.signal(signal.SIGINT, self.handle_shutdown)
    
    def handle_shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False
    
    def run_log_collection(self):
        """Main log collection loop"""
        logger.info("Starting log collection service...")
        
        while self.running:
            try:
                # Run collection cycle
                self.log_collector.run_collection_cycle()
                
                # Sleep until next collection
                interval = self.config['log_collection']['interval_seconds']
                logger.info(f"Collection complete. Next run in {interval} seconds.")
                
                # Sleep in small chunks to allow graceful shutdown
                for _ in range(interval):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in collection cycle: {e}", exc_info=True)
                time.sleep(60)  # Wait before retry
        
        logger.info("Log collection stopped")
    
    def run(self):
        """Start the application"""
        logger.info(f"Starting Chatterbox for {self.config['machine_id']}")
        
        # Start log collection in background thread
        collection_thread = threading.Thread(
            target=self.run_log_collection,
            daemon=False
        )
        collection_thread.start()
        
        # Main thread just waits
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        # Wait for collection thread to finish
        collection_thread.join(timeout=30)
        
        # Cleanup
        self.kafka_producer.close()
        logger.info("Chatterbox shutdown complete")

if __name__ == "__main__":
    app = ChatterboxApplication()
    app.run()
```

---

## Testing Checklist

Before deployment, verify:

### ✅ Security Tests
- [ ] Only 3 user accounts exist (Prof1, Prof2, Guest)
- [ ] No user creation functionality accessible
- [ ] All private keys remain on their respective machines
- [ ] Encryption/decryption works correctly (test with sample data)
- [ ] File permissions are restrictive (600 for keys, 700 for directories)

### ✅ Functionality Tests
- [ ] Linux log collector reads all 6 log types from Dev machines
- [ ] Windows log collector reads all 9 event logs from Prof machines
- [ ] Each log type goes to correct Kafka topic
- [ ] Kafka receiver decrypts and stores logs in correct folders
- [ ] No duplicate log entries after restart
- [ ] Chat works between allowed user pairs

### ✅ Resilience Tests
- [ ] Service auto-restarts after kill
- [ ] Logs buffered locally when Kafka down
- [ ] Buffered logs sent when Kafka returns
- [ ] Log file rotation handled correctly
- [ ] Service survives system reboot
- [ ] Checkpoint prevents duplicate transmission

### ✅ Service Tests (Linux)
- [ ] Service starts on boot
- [ ] Service cannot be stopped by non-root users
- [ ] Service restarts on failure within 10 seconds
- [ ] Logs visible in journalctl

### ✅ Service Tests (Windows)
- [ ] Service starts on boot
- [ ] Service cannot be stopped by non-admin users
- [ ] Service restarts on failure
- [ ] Logs written to service log files

---

## Deployment Workflow

### Phase 1: Initial Setup
```bash
# 1. Generate all encryption keys
python3 setup_keys.py

# 2. Distribute folders to respective machines
# - Copy dev1/ to Dev1 VM
# - Copy dev2/ to Dev2 VM  
# - Copy prof1/ to Prof1 VM (when ready)
# - Copy prof2/ to Prof2 VM (when ready)
# - Keep kafka_receiver/ on Kafka server

# 3. Setup Kafka broker
# (Installation instructions for Kafka not included here)
```

### Phase 2: Client Installation

**On Dev1 (Linux):**
```bash
cd dev1/
sudo ./install.sh
```

**On Dev2 (Linux):**
```bash
cd dev2/
sudo ./install.sh
```

**On Prof1 (Windows) - Run PowerShell as Administrator:**
```powershell
cd prof1\
.\install.bat
```

**On Prof2 (Windows) - Run PowerShell as Administrator:**
```powershell
cd prof2\
.\install.bat
```

### Phase 3: Kafka Receiver Setup
```bash
cd kafka_receiver/
pip3 install -r requirements.txt
python3 receiver.py
```

### Phase 4: Verification
```bash
# Check services are running
# Linux:
sudo systemctl status chatterbox-dev1
sudo systemctl status chatterbox-dev2

# Windows:
Get-Service ChatterboxProf1
Get-Service ChatterboxProf2

# Check Kafka topics created
kafka-topics.sh --list --bootstrap-server localhost:9092

# Monitor logs being received
tail -f kafka_receiver/received_logs/dev1/syslog/$(date +%Y-%m-%d).log
```

---

## Dependencies

**requirements.txt (for all components):**
```
kafka-python==2.0.2
cryptography==41.0.7
passlib==1.7.4
pywin32==306; sys_platform == 'win32'
```

**Additional Windows Requirements:**
```
pywin32==306
wmi==1.5.1
```

---

## Success Criteria

The implementation is complete and successful when:

1. ✅ Chatterbox runs continuously for 7+ days without manual intervention
2. ✅ All log types collected and transmitted every hour
3. ✅ Zero logs lost during Kafka/network failures
4. ✅ Services cannot be stopped by non-privileged users
5. ✅ Services auto-recover from crashes within 30 seconds
6. ✅ Chat works reliably between authorized users only
7. ✅ Encryption prevents log tampering/interception
8. ✅ System survives reboots and resumes operation
9. ✅ Kafka receiver organizes logs correctly by machine/type
10. ✅ No duplicate log entries (checkpoint system works)

---

## Support & Troubleshooting

### Common Issues

**Issue: Kafka connection failed**
```bash
# Check Kafka is running
systemctl status kafka

# Check network connectivity
telnet <kafka-server> 9092

# Check firewall rules
sudo ufw status
```

**Issue: Logs not being collected**
```bash
# Check file permissions
ls -la /var/log/syslog
ls -la /opt/chatterbox/dev1/client/

# Check service logs
journalctl -u chatterbox-dev1 -f
```

**Issue: Service won't start**
```bash
# Check Python path
which python3

# Test main.py directly
cd /opt/chatterbox/dev1
python3 client/main.py
```

---

## Paper References

- **Section 4 (Chatterbox Design)**: Pages 21:9-21:10
- **Algorithm 3 (Implementation)**: Page 21:32
- **Table 2 (Linux Logs)**: Page 21:10
- **Table 3 (Windows Event Logs)**: Page 21:10
- **Figure 2 (Architecture Diagram)**: Page 21:10
- **Section 5.7 (Overhead Analysis)**: Page 21:26
- **Section 5.8 (False Positives)**: Page 21:26
- **Section 5.9 (Limitations)**: Page 21:26

---

## Final Notes

This specification provides complete, implementation-ready requirements for the Chatterbox application as described in the ADAPT research paper. All components are designed for production deployment with emphasis on:

- **Security**: Asymmetric encryption, secure key management, restricted permissions
- **Resilience**: Local buffering, auto-restart, checkpoint system
- **Stealth**: Camouflaged service names, hidden log transmission
- **Reliability**: Handles failures, rotations, and restarts gracefully

The system is ready for deployment on Dev1 and Dev2 VMs with future expansion to Prof1/Prof2 Windows machines.

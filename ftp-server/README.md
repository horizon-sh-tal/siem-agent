# FTP Honeypot Server - ADAPT Project

Dockerized FTP server with Kafka monitoring for the ADAPT honeypot network.

## Quick Overview

This FTP server is part of the ADAPT (Adaptive Camouflage Based Deception Orchestration) honeypot designed to trap Advanced Persistent Threats (APTs).

**Server**: Ubuntu 20.04 Server VM (IP: 192.168.27.211)  
**Purpose**: Store fake classified documents to attract attackers  
**Monitoring**: Kafka-based activity tracking

---

## Architecture

```
┌─────────────────────────────────────────────┐
│ Prof-1 VM (192.168.27.212)                  │
│ Prof-2 VM (192.168.27.155)                  │──┐
│ Dev-1 VM  (192.168.27.200)                  │  │
│ Dev-2 VM  (192.168.27.54)                   │  │
└─────────────────────────────────────────────┘  │
                    │                             │
                    │ FTP Access                  │
                    ▼                             │
┌─────────────────────────────────────────────┐  │
│ FTP Server VM (192.168.27.211)              │  │
│                                             │  │
│  ┌──────────────────────────────────────┐  │  │
│  │ Docker: pure-ftpd                    │  │  │
│  │  - Port 21 (control)                 │  │  │
│  │  - Ports 30000-30009 (passive)       │  │  │
│  │  - 3 accounts: guest, prof1, prof2   │  │  │
│  └──────────────────────────────────────┘  │  │
│                                             │  │
│  ┌──────────────────────────────────────┐  │  │
│  │ Docker: ftp-monitor (Python)         │  │  │
│  │  - File integrity monitoring         │  │  │
│  │  - SHA256 hashing                    │  │  │
│  │  - Kafka log producer                │──┼──┘
│  └──────────────────────────────────────┘  │
│                                             │
│  /ftp-data/                                 │
│  ├── guest/   (1 README)                   │
│  ├── prof1/   (7 MoUs, 12 PDFs, 5 CSVs)    │
│  └── prof2/   (7 MoUs, 12 PDFs, 5 CSVs)    │
└─────────────────────────────────────────────┘
                    │
                    │ Kafka Topic: ftp-activity-logs
                    ▼
┌─────────────────────────────────────────────┐
│ Kafka Broker (192.168.27.211:9092)         │
│  - Receives file change events             │
│  - Tracks upload/download/modify/delete    │
└─────────────────────────────────────────────┘
```

---

## Quick Start

### 1. Upload Files to Ubuntu VM

Copy these files to `~/ftp-server/` on your Ubuntu 20.04 Server VM:
- `docker-compose.yml`
- `add_ftp_users.sh`
- `ftp_monitor.py`
- `generate_fake_assets.sh`
- `deploy_ftp.sh`

```bash
# On Ubuntu VM:
mkdir -p ~/ftp-server
cd ~/ftp-server

# Copy files here (use scp, sftp, or paste content)
```

### 2. Run Deployment Script

```bash
chmod +x deploy_ftp.sh
./deploy_ftp.sh
```

This will:
- ✅ Install Docker and Docker Compose
- ✅ Install required tools (enscript, ghostscript)
- ✅ Generate 80+ fake assets (MoUs, research papers, datasets)
- ✅ Configure firewall
- ✅ Start FTP server and monitoring agent
- ✅ Verify everything is working

### 3. Test FTP Access

From any VM on the network:
```bash
ftp 192.168.27.211
# Username: guest
# Password: guest123

ftp> ls
ftp> get README.txt
ftp> bye
```

---

## FTP Accounts

| Username | Password | Access | Contents |
|----------|----------|--------|----------|
| `guest` | `guest123` | Read-only | Shared files |
| `prof1` | `Maharanapratap!` | Full | 7 MoUs, 12 research papers, 5 datasets, honey credentials |
| `prof2` | `gogreen@7560` | Full | 7 MoUs, 12 research papers, 5 datasets, honey credentials |

---

## Fake Assets Generated

### Prof1 & Prof2 Directories (each):

**MoUs** (7 PDF files):
- MoU_Health_and_Family_Welfare_2024.pdf
- MoU_Science_and_Technology_2024.pdf
- MoU_Home_Affairs_2024.pdf
- MoU_External_Affairs_2024.pdf
- MoU_Defense_2024.pdf
- MoU_Education_2024.pdf
- MoU_Electronics_and_IT_2024.pdf

**Research Papers** (12 PDF files):
- COVID-19 Transmission Dynamics
- Predictive Modeling Using AI/ML
- Vaccine Distribution Optimization
- Economic Impact Assessment
- Mental Health Crisis Management
- Supply Chain Resilience
- Genomic Surveillance
- Contact Tracing Technology
- Hospital Capacity Planning
- Risk Communication Strategies
- Cross-Border Response Coordination
- Long-term Health Effects

**Datasets** (5 CSV files):
- COVID_Cases_India_2020.csv (365 rows)
- Vaccination_Progress_2021.csv (365 rows)
- Hospital_Capacity_Utilization.csv (365 rows)
- Mortality_Analysis_Urban.csv (365 rows)
- Contact_Tracing_Network.csv (365 rows)

**Honey Tokens**:
- README.txt with fake SSH/VPN credentials
- .backup/system_credentials.txt with fake database/web/AWS credentials

---

## Monitoring

### Activity Tracking

The `ftp-monitor` container tracks:
- 📁 New files uploaded
- ✏️ Files modified (with hash comparison)
- 🗑️ Files deleted
- 👤 Which FTP account accessed files
- ⏰ Timestamp of all changes

### Kafka Integration

Every 30 minutes, the monitor sends a report to Kafka:

```json
{
  "timestamp": "2024-02-18T10:30:00",
  "event_type": "ftp_activity_scan",
  "machine_id": "ftp-server",
  "changes": {
    "new_files": [...],
    "modified_files": [...],
    "deleted_files": [...]
  },
  "summary": {
    "new_files": 2,
    "modified_files": 1,
    "deleted_files": 0
  }
}
```

**Kafka Topic**: `ftp-activity-logs`  
**Broker**: `192.168.27.211:9092`

---

## Common Tasks

### View Logs
```bash
cd ~/ftp-server

# All logs
docker-compose logs -f

# FTP server only
docker logs ftp-server -f

# Monitor only
docker logs ftp-monitor -f
```

### Restart Server
```bash
cd ~/ftp-server
docker-compose restart
```

### Stop Server
```bash
cd ~/ftp-server
docker-compose down
```

### Regenerate Fake Assets
```bash
cd ~/ftp-server
docker-compose down
rm -rf ftp-data/
./generate_fake_assets.sh
docker-compose up -d
```

### Check Kafka Messages
```bash
# On Kafka VM
kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic ftp-activity-logs \
    --from-beginning
```

---

## Network Configuration

**FTP Server VM IP**: 192.168.27.211

**Allowed Clients**:
- Prof-1: 192.168.27.212
- Prof-2: 192.168.27.155
- Dev-1: 192.168.27.200
- Dev-2: 192.168.27.54

**Firewall Rules**:
```bash
# Only allow FTP from internal network
sudo ufw allow from 192.168.27.0/24 to any port 21
sudo ufw allow from 192.168.27.0/24 to any port 30000:30009
```

---

## Troubleshooting

### Cannot connect to FTP
```bash
# Check if container is running
docker ps | grep ftp-server

# Check if port is listening
netstat -tuln | grep 21

# Check firewall
sudo ufw status
```

### Login fails for prof1/prof2
```bash
# Verify users were created
docker exec ftp-server pure-pw list

# Expected output:
# prof1     /home/ftpusers/prof1
# prof2     /home/ftpusers/prof2

# If missing, restart:
docker-compose restart ftp
```

### Monitor not sending to Kafka
```bash
# Check monitor logs
docker logs ftp-monitor

# Test Kafka connectivity
telnet 192.168.27.211 9092

# If fails, check Kafka is running
# On Kafka VM:
sudo systemctl status kafka
```

---

## File Structure

```
~/ftp-server/
├── docker-compose.yml       # Docker orchestration
├── add_ftp_users.sh         # FTP user creation script
├── ftp_monitor.py           # Kafka monitoring agent
├── generate_fake_assets.sh  # Asset generation script
├── deploy_ftp.sh            # One-click deployment
├── INSTALLATION_GUIDE.md    # Detailed setup guide
└── ftp-data/                # FTP file storage
    ├── guest/
    ├── prof1/
    └── prof2/
```

---

## Security Notes

⚠️ **This is a HONEYPOT** - All credentials and documents are FAKE

- All "classified" documents are fabricated
- Honey credentials are intentionally weak
- System is designed to be compromised
- All activity is logged to Kafka
- Do NOT put real sensitive data here

---

## Integration with ADAPT

This FTP server is part of the larger ADAPT honeypot network:

1. **Attack Path**: HTTP Server → Internal Network → FTP Server
2. **Attackers**: Intended to trap APT-40, APT-28, Lazarus groups
3. **Goal**: Monitor sophisticated attackers accessing "classified" data
4. **Intelligence**: Track which files attackers target and exfiltrate

---

## Documentation

- **Full Installation Guide**: `INSTALLATION_GUIDE.md`
- **Kafka Integration**: `KAFKA_INTEGRATION.md`
- **Testing Commands**: `FTP_TESTING_COMMANDS.md`

---

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Read troubleshooting in `INSTALLATION_GUIDE.md`
3. Verify network connectivity
4. Check firewall rules

---

## Next Steps

After FTP server is running:
1. ✅ Test access from all VMs (Prof-1, Prof-2, Dev-1, Dev-2)
2. ✅ Verify Kafka is receiving activity logs
3. ⏭️ Set up attack paths (HTTP → Dev → FTP)
4. ⏭️ Deploy Chatterbox on all VMs
5. ⏭️ Monitor for 100 days as per paper

---

**Status**: ✅ Ready for deployment

**Version**: 1.0.0  
**Last Updated**: 2024-02-18  
**Project**: ADAPT Honeypot (IIT Kanpur)

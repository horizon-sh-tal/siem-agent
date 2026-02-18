# FTP Server Setup Guide - Complete Installation

## System Information
- **FTP Server VM IP**: 192.168.27.211 (Ubuntu 20.04 Server)
- **Kafka Broker**: 192.168.27.211:9092
- **Prof-1 IP**: 192.168.27.212
- **Prof-2 IP**: 192.168.27.155
- **Dev-1 IP**: 192.168.27.200
- **Dev-2 IP**: 192.168.27.54

---

## Prerequisites Installation

### 1. Update System
```bash
sudo apt-get update
sudo apt-get upgrade -y
```

### 2. Install Docker & Docker Compose
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version

# IMPORTANT: Log out and log back in for group changes to take effect
exit
# SSH back in
```

### 3. Install Required Tools
```bash
sudo apt-get install -y \
    enscript \
    ghostscript \
    python3 \
    python3-pip \
    git \
    net-tools \
    ufw
```

---

## FTP Server Setup

### 1. Create Project Directory
```bash
# Create directory
mkdir -p ~/ftp-server
cd ~/ftp-server

# Download/copy all project files here:
# - docker-compose.yml
# - add_ftp_users.sh
# - ftp_monitor.py
# - generate_fake_assets.sh
```

### 2. Make Scripts Executable
```bash
chmod +x add_ftp_users.sh
chmod +x generate_fake_assets.sh
chmod +x ftp_monitor.py
```

### 3. Generate Fake Assets
```bash
./generate_fake_assets.sh
```

**Expected output:**
```
================================================
Generating Fake FTP Assets for Honeypot
================================================
Creating directory structure...
Generating fake MoU documents...
  ✓ Created MoU with Ministry of Health and Family Welfare
  ✓ Created MoU with Ministry of Science and Technology
  ...
Generating fake research papers...
  ✓ Created research paper: COVID-19 Transmission Dynamics...
  ...
Generating fake pandemic datasets...
  ✓ Created dataset: COVID_Cases_India_2020.csv (365 rows)
  ...
Total fake files: ~80 files
```

### 4. Verify Generated Files
```bash
tree ftp-data/  # or use: find ftp-data -type f
```

**Expected structure:**
```
ftp-data/
├── guest/
│   └── README.txt
├── prof1/
│   ├── MoUs/          (7 PDF files)
│   ├── research/      (12 PDF files)
│   ├── datasets/      (5 CSV files)
│   ├── .backup/       (system_credentials.txt)
│   └── README.txt
└── prof2/
    ├── MoUs/          (7 PDF files)
    ├── research/      (12 PDF files)
    ├── datasets/      (5 CSV files)
    ├── .backup/       (system_credentials.txt)
    └── README.txt
```

---

## Docker Deployment

### 1. Review Configuration
```bash
# Check docker-compose.yml
cat docker-compose.yml

# Verify FTP server IP is set correctly in PUBLICHOST
# Should be: PUBLICHOST: "192.168.27.211"
```

### 2. Start FTP Server
```bash
# Start in detached mode
docker-compose up -d

# Check logs
docker-compose logs -f
```

**Expected output:**
```
Creating ftp-server ... done
Creating ftp-monitor ... done
ftp-server    | Creating FTP user database...
ftp-server    | Adding prof1 user...
ftp-server    | Adding prof2 user...
ftp-server    | Building PureDB database...
ftp-server    | Starting FTP server...
ftp-monitor   | FTP Activity Monitor Starting
ftp-monitor   | Connected to Kafka broker at 192.168.27.211:9092
```

### 3. Verify Container Status
```bash
docker ps

# Should show:
# - ftp-server (running)
# - ftp-monitor (running)
```

### 4. Check FTP Server Logs
```bash
docker logs ftp-server

# Should show:
# - User prof1 added
# - User prof2 added
# - FTP server started
```

### 5. Check Monitor Logs
```bash
docker logs ftp-monitor -f

# Should show:
# - Kafka connection successful
# - Initial scan complete
# - Waiting for next scan
```

---

## Firewall Configuration

```bash
# Allow FTP ports
sudo ufw allow 21/tcp
sudo ufw allow 30000:30009/tcp

# Allow from specific IPs only (more secure)
sudo ufw allow from 192.168.27.0/24 to any port 21
sudo ufw allow from 192.168.27.0/24 to any port 30000:30009

# Enable firewall
sudo ufw enable
sudo ufw status
```

---

## Testing FTP Access

### Test from FTP Server VM (Local Test)
```bash
# Install FTP client
sudo apt-get install -y ftp

# Test guest account
ftp localhost
# Username: guest
# Password: guest123
ftp> ls
ftp> cd /
ftp> ls
ftp> bye

# Test prof1 account
ftp localhost
# Username: prof1
# Password: Maharanapratap!
ftp> ls
ftp> cd MoUs
ftp> ls
ftp> bye

# Test prof2 account
ftp localhost
# Username: prof2
# Password: gogreen@7560
ftp> ls
ftp> cd research
ftp> ls
ftp> bye
```

### Test from Prof-1 VM (192.168.27.212)

**On Windows (PowerShell):**
```powershell
ftp 192.168.27.211
# Username: prof1
# Password: Maharanapratap!

ftp> dir
ftp> cd MoUs
ftp> dir
ftp> get MoU_Health_and_Family_Welfare_2024.pdf
ftp> bye
```

**On Linux/Ubuntu:**
```bash
ftp 192.168.27.211
# Username: prof1
# Password: Maharanapratap!

ftp> ls
ftp> cd datasets
ftp> ls
ftp> get COVID_Cases_India_2020.csv
ftp> bye
```

### Test from Prof-2 VM (192.168.27.155)
```bash
ftp 192.168.27.211
# Username: prof2
# Password: gogreen@7560

ftp> ls
ftp> cd research
ftp> ls
ftp> bye
```

### Test from Dev-1 VM (192.168.27.200)
```bash
ftp 192.168.27.211
# Username: guest
# Password: guest123

ftp> ls
ftp> get README.txt
ftp> bye
```

---

## Monitoring & Logs

### 1. View FTP Activity Monitor Logs
```bash
docker logs ftp-monitor --tail 50 -f
```

**Expected output every 30 minutes:**
```
INFO - Starting scan at 2024-02-18T10:30:00
INFO - Scan complete: 85 files found
INFO - New file detected: prof1/MoUs/test_upload.pdf (account: prof1)
INFO - Sent activity log to Kafka: {'new_files': 1, 'modified_files': 0, 'deleted_files': 0}
```

### 2. Check Kafka Topic (from Kafka VM)
```bash
# SSH to Kafka broker VM (192.168.27.211)
kafka-console-consumer.sh \
    --bootstrap-server localhost:9092 \
    --topic ftp-activity-logs \
    --from-beginning
```

**Expected output:**
```json
{
  "timestamp": "2024-02-18T10:30:00",
  "event_type": "ftp_activity_scan",
  "machine_id": "ftp-server",
  "changes": {
    "new_files": [
      {
        "filename": "test_upload.pdf",
        "account": "prof1",
        "path": "/ftp-data/prof1/MoUs/test_upload.pdf",
        "hash": "abc123...",
        "size": 12345
      }
    ],
    "modified_files": [],
    "deleted_files": []
  },
  "summary": {
    "new_files": 1,
    "modified_files": 0,
    "deleted_files": 0
  }
}
```

### 3. View FTP Server Access Logs
```bash
# Pure-FTPd logs are in container
docker exec ftp-server cat /var/log/pure-ftpd/transfer.log
```

---

## Troubleshooting

### Issue: FTP Connection Refused
```bash
# Check if FTP container is running
docker ps | grep ftp-server

# If not running, check logs
docker logs ftp-server

# Restart container
docker-compose restart ftp
```

### Issue: Cannot Login with prof1/prof2
```bash
# Check if users were created
docker exec ftp-server pure-pw list

# Expected output:
# prof1     /home/ftpusers/prof1
# prof2     /home/ftpusers/prof2

# If users missing, recreate them
docker-compose down
docker-compose up -d
```

### Issue: Passive Mode Connection Fails
```bash
# Ensure passive ports are open
sudo ufw allow 30000:30009/tcp

# Check PUBLICHOST in docker-compose.yml
# Must be: PUBLICHOST: "192.168.27.211"

# Restart FTP server
docker-compose restart ftp
```

### Issue: Monitor Cannot Connect to Kafka
```bash
# Check Kafka is reachable
telnet 192.168.27.211 9092

# If fails, check Kafka broker is running on that IP
# On Kafka VM:
sudo systemctl status kafka

# Check firewall
sudo ufw status
```

### Issue: Files Not Visible in FTP
```bash
# Check permissions
ls -lah ftp-data/prof1/

# Should show readable files
# If not, fix permissions:
chmod -R 755 ftp-data/
```

---

## Maintenance Commands

### Start/Stop FTP Server
```bash
# Stop
docker-compose down

# Start
docker-compose up -d

# Restart
docker-compose restart

# View logs
docker-compose logs -f
```

### Update FTP Users
```bash
# Edit add_ftp_users.sh with new users/passwords
# Then restart:
docker-compose down
docker-compose up -d
```

### Backup FTP Data
```bash
# Create backup
tar -czf ftp-data-backup-$(date +%Y%m%d).tar.gz ftp-data/

# Restore backup
tar -xzf ftp-data-backup-20240218.tar.gz
```

### Clear All Data (Reset)
```bash
# WARNING: This deletes all FTP data
docker-compose down
sudo rm -rf ftp-data/
./generate_fake_assets.sh
docker-compose up -d
```

---

## Security Checklist

- [✓] FTP server only accessible from internal network (192.168.27.0/24)
- [✓] Firewall configured to block external access
- [✓] Strong passwords used for prof1/prof2 accounts
- [✓] Monitoring agent sends encrypted logs to Kafka
- [✓] File integrity checking via SHA256 hashes
- [✓] Docker containers isolated from host system
- [✓] All fake assets marked as "CLASSIFIED" to entice attackers

---

## Quick Reference

### FTP Accounts
| Username | Password | Home Directory | Access Level |
|----------|----------|----------------|--------------|
| guest | guest123 | /home/ftpusers/guest | Read-only |
| prof1 | Maharanapratap! | /home/ftpusers/prof1 | Full access |
| prof2 | gogreen@7560 | /home/ftpusers/prof2 | Full access |

### Ports
| Port | Protocol | Purpose |
|------|----------|---------|
| 21 | TCP | FTP Control |
| 30000-30009 | TCP | FTP Passive Data |

### Important Paths
| Path | Description |
|------|-------------|
| ~/ftp-server | Project root |
| ~/ftp-server/ftp-data | FTP file storage |
| ~/ftp-server/docker-compose.yml | Docker configuration |
| ~/ftp-server/ftp_monitor.py | Kafka monitoring agent |

### Useful Commands
```bash
# View running containers
docker ps

# View all logs
docker-compose logs -f

# View only FTP logs
docker logs ftp-server -f

# View only monitor logs
docker logs ftp-monitor -f

# Restart everything
docker-compose restart

# Check disk usage
du -sh ftp-data/
```

---

## Next Steps

1. ✅ FTP server is running and accessible
2. ✅ Fake assets generated
3. ✅ Monitoring agent connected to Kafka
4. ⏭️ Configure VPN access from Prof/Dev VMs
5. ⏭️ Test attack paths (HTTP → Internal → FTP)
6. ⏭️ Monitor Kafka logs for attacker activity
7. ⏭️ Set up Elasticsearch/Kibana dashboard for visualization

---

## Support

If you encounter issues:
1. Check logs: `docker-compose logs -f`
2. Verify network connectivity: `ping 192.168.27.212`
3. Test FTP locally first: `ftp localhost`
4. Check Kafka connectivity: `telnet 192.168.27.211 9092`
5. Review this guide's Troubleshooting section

---

**Installation Complete! 🎉**

Your FTP honeypot server is now ready to trap attackers.

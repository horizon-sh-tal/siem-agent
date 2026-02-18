# FTP Server Setup Guide (Ubuntu 20.04, Docker, Kafka Integration)

## 1. Prerequisites
- Ubuntu 20.04 LTS VM
- Docker & Docker Compose installed
- Python 3, pip installed
- Network access to Kafka broker (192.168.27.211:9092)

## 2. Directory Structure
```bash
mkdir -p ~/ftp-server
cd ~/ftp-server
```

## 3. Generate Fake Assets
```bash
chmod +x generate_fake_assets.sh
./generate_fake_assets.sh
```

## 4. Configure FTP Users
- Edit `docker-compose.yml` to set prof1/prof2 passwords to match their login passwords.
- Example (in command section):
  ```
  pure-pw useradd prof1 -u ftpuser -d /home/ftpusers/prof1 -m && \
  pure-pw passwd prof1 [prof1_password]
  ```

## 5. Start FTP Server
```bash
docker-compose up -d
```

## 6. Start Monitoring Agent
```bash
pip3 install kafka-python
sudo python3 ftp_monitor.py
```

## 7. Network Configuration
- Ensure VM is on the same VPN/subnet as Prof/Dev machines.
- Assign static internal IP if needed.

## 8. Test FTP Access (from Prof/Dev machines)
```bash
# From Prof-1/Prof-2/Dev-1/Dev-2
ftp [FTP_SERVER_IP]
# Login as guest, prof1, or prof2
# Test upload/download in respective directories
```

## 9. Kafka Integration
- Monitoring agent will send logs to Kafka topic `ftp-activity-logs` at 192.168.27.211:9092 every 30 minutes.

---

# End of Guide

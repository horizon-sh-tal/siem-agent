# Kafka Integration for FTP Monitoring Agent

- Kafka Broker IP: 192.168.27.211
- Kafka Broker Port: 9092
- Kafka Topic: ftp-activity-logs

## Python Agent Configuration

In `ftp_monitor.py`:

KAFKA_BROKER = '192.168.27.211:9092'
KAFKA_TOPIC = 'ftp-activity-logs'

No further configuration is needed if the broker is reachable from the FTP server VM.

## Docker Compose

No changes needed for Kafka in docker-compose.yml, as the monitoring agent runs outside the container and connects directly to Kafka.

---

#!/bin/bash
# =============================================================================
# SIEM Agent – Kafka VM Setup Script
# Run on a fresh Ubuntu 20.04/22.04 server as root
# Sets up: Java, Apache Kafka 3.6.2, Zookeeper and Kafka as systemd services
# =============================================================================
set -e

KAFKA_VERSION="3.6.2"
SCALA_VERSION="2.13"
KAFKA_DIR="/opt/kafka"
KAFKA_USER="kafka"
KAFKA_TGZ="kafka_${SCALA_VERSION}-${KAFKA_VERSION}.tgz"
KAFKA_URL="https://archive.apache.org/dist/kafka/${KAFKA_VERSION}/${KAFKA_TGZ}"

echo "============================================="
echo "  SIEM Agent – Kafka VM Setup"
echo "  Kafka ${KAFKA_VERSION} on $(hostname)"
echo "============================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./kafka_vm_setup.sh)"
    exit 1
fi

# -----------------------------------------------------------------------------
# 1. System update + Java
# -----------------------------------------------------------------------------
echo ""
echo "[1/6] Installing Java..."
apt-get update -qq
apt-get install -y default-jdk wget

java -version
echo "Java installed."

# -----------------------------------------------------------------------------
# 2. Create kafka system user
# -----------------------------------------------------------------------------
echo ""
echo "[2/6] Creating kafka user..."
if ! id "$KAFKA_USER" &>/dev/null; then
    useradd -r -m -d "$KAFKA_DIR" -s /bin/false "$KAFKA_USER"
    echo "User '$KAFKA_USER' created."
else
    echo "User '$KAFKA_USER' already exists."
fi

# -----------------------------------------------------------------------------
# 3. Download and extract Kafka
# -----------------------------------------------------------------------------
echo ""
echo "[3/6] Downloading Kafka ${KAFKA_VERSION}..."
cd /opt

if [ ! -d "$KAFKA_DIR" ]; then
    wget -q --show-progress "$KAFKA_URL"
    tar -xzf "$KAFKA_TGZ"
    mv "kafka_${SCALA_VERSION}-${KAFKA_VERSION}" kafka
    rm -f "$KAFKA_TGZ"
    chown -R "$KAFKA_USER:$KAFKA_USER" "$KAFKA_DIR"
    echo "Kafka extracted to $KAFKA_DIR"
else
    echo "Kafka directory already exists at $KAFKA_DIR — skipping download."
fi

# -----------------------------------------------------------------------------
# 4. Configure Kafka to listen on all interfaces
# -----------------------------------------------------------------------------
echo ""
echo "[4/6] Configuring Kafka..."

# Detect the primary non-loopback IP
HOST_IP=$(hostname -I | awk '{print $1}')
echo "Detected host IP: $HOST_IP"

# Update server.properties to advertise the correct IP
sed -i "s|#advertised.listeners=PLAINTEXT://your.host.name:9092|advertised.listeners=PLAINTEXT://${HOST_IP}:9092|" \
    "$KAFKA_DIR/config/server.properties"

# Set log retention to 7 days (reasonable for a SIEM)
sed -i "s|log.retention.hours=168|log.retention.hours=168|" \
    "$KAFKA_DIR/config/server.properties"

# Allow auto-creation of topics (agents will create their own topics)
grep -q "auto.create.topics.enable" "$KAFKA_DIR/config/server.properties" || \
    echo "auto.create.topics.enable=true" >> "$KAFKA_DIR/config/server.properties"

echo "Kafka configured with advertised IP: $HOST_IP"

# -----------------------------------------------------------------------------
# 5. Create systemd service files
# -----------------------------------------------------------------------------
echo ""
echo "[5/6] Creating systemd services..."

# Zookeeper service
cat > /etc/systemd/system/zookeeper.service << 'EOF'
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
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

# Kafka service
cat > /etc/systemd/system/kafka.service << 'EOF'
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
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable zookeeper.service kafka.service

echo "Systemd services created and enabled."

# -----------------------------------------------------------------------------
# 6. Start services
# -----------------------------------------------------------------------------
echo ""
echo "[6/6] Starting Zookeeper and Kafka..."
systemctl start zookeeper.service
echo "Waiting for Zookeeper to be ready..."
sleep 5

systemctl start kafka.service
echo "Waiting for Kafka to be ready..."
sleep 8

systemctl status zookeeper.service --no-pager
systemctl status kafka.service --no-pager

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Kafka setup complete!"
echo ""
echo "  Broker address:  ${HOST_IP}:9092"
echo ""
echo "  Useful commands:"
echo "    journalctl -u kafka -f          # Kafka logs"
echo "    journalctl -u zookeeper -f      # Zookeeper logs"
echo "    systemctl stop kafka            # Stop Kafka"
echo "    systemctl restart kafka         # Restart"
echo ""
echo "  NEXT STEPS:"
echo "    1. Note the broker IP above (${HOST_IP})"
echo "    2. Run the SIEM receiver installer:"
echo "       sudo ./kafka_receiver/install.sh"
echo "============================================="

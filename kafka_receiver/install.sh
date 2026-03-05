#!/bin/bash
# =============================================================================
# SIEM Agent – Kafka Receiver Installer
# Run on the Kafka VM as root AFTER kafka_vm_setup.sh has completed
# =============================================================================
set -e

INSTALL_DIR="/opt/siem-agent/kafka_receiver"
SERVICE_FILE="services/siem-receiver.service"

echo "============================================="
echo "  SIEM Agent – Kafka Receiver Installer"
echo "============================================="

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

# Verify Kafka is running before installing receiver
if ! systemctl is-active --quiet kafka.service; then
    echo "ERROR: kafka.service is not running."
    echo "Run kafka_vm_setup.sh first, then re-run this script."
    exit 1
fi

# -----------------------------------------------------------------------------
# Install files
# -----------------------------------------------------------------------------
echo ""
echo "[1/4] Installing receiver files to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR/received_logs"
mkdir -p "$INSTALL_DIR/keys"

cp receiver.py    "$INSTALL_DIR/"
cp decryption.py  "$INSTALL_DIR/"
cp storage.py     "$INSTALL_DIR/"
cp config.json    "$INSTALL_DIR/"
cp requirements.txt "$INSTALL_DIR/"

# Copy common/ library one level up so imports work
cp -r ../common/ "$(dirname $INSTALL_DIR)/common/" 2>/dev/null || true

# -----------------------------------------------------------------------------
# Check for private key
# -----------------------------------------------------------------------------
echo ""
echo "[2/4] Checking encryption keys..."
if [ ! -f "keys/kafka_receiver_private.pem" ]; then
    echo ""
    echo "  WARNING: keys/kafka_receiver_private.pem not found."
    echo "  You must copy the key BEFORE the receiver can decrypt logs."
    echo "  Generate keys on the management machine with:"
    echo "    python3 setup_keys.py"
    echo "  Then copy the private key here:"
    echo "    scp kafka_receiver/keys/kafka_receiver_private.pem <this-server>:$INSTALL_DIR/keys/"
    echo ""
else
    cp keys/kafka_receiver_private.pem "$INSTALL_DIR/keys/"
    chmod 600 "$INSTALL_DIR/keys/kafka_receiver_private.pem"
    echo "  Private key installed."
fi

# -----------------------------------------------------------------------------
# Python dependencies
# -----------------------------------------------------------------------------
echo ""
echo "[3/4] Installing Python dependencies..."
pip3 install -r requirements.txt

# -----------------------------------------------------------------------------
# Systemd service
# -----------------------------------------------------------------------------
echo ""
echo "[4/4] Installing systemd service..."
cp "$SERVICE_FILE" /etc/systemd/system/siem-receiver.service
systemctl daemon-reload
systemctl enable siem-receiver.service
systemctl start  siem-receiver.service

sleep 3
systemctl status siem-receiver.service --no-pager

echo ""
echo "============================================="
echo "  Receiver installed and running!"
echo ""
echo "  Logs are stored in: $INSTALL_DIR/received_logs/"
echo ""
echo "  Useful commands:"
echo "    journalctl -u siem-receiver -f   # Follow logs"
echo "    systemctl restart siem-receiver  # Restart"
echo "============================================="

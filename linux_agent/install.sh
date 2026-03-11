#!/bin/bash
# SIEM Agent – Linux installer
# Run as root: sudo ./install.sh
set -e
cd "$(dirname "$0")"  # always run from script's own directory

INSTALL_DIR="/opt/siem-agent/linux"

echo "==> SIEM Agent Linux Installer"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

mkdir -p "$INSTALL_DIR/logs"
mkdir -p "$INSTALL_DIR/keys"
cp -r agent/       "$INSTALL_DIR/"
cp    config.json  "$INSTALL_DIR/"
cp -r ../common/   "$INSTALL_DIR/../common/" 2>/dev/null || true

# Copy key if present, otherwise warn
if [ -f "keys/kafka_public.pem" ]; then
    cp keys/kafka_public.pem "$INSTALL_DIR/keys/"
    chmod 600 "$INSTALL_DIR/keys/kafka_public.pem"
    echo "==> Public key installed."
else
    echo ""
    echo "  WARNING: keys/kafka_public.pem not found."
    echo "  Copy it before starting the agent:"
    echo "    scp kafka@<kafka-server>:~/siem-agent/linux_agent/keys/kafka_public.pem \\"
    echo "        $INSTALL_DIR/keys/kafka_public.pem"
    echo ""
fi

echo "==> Installing Python dependencies (venv)..."
apt-get install -y python3-venv python3-full
VENV_DIR="$INSTALL_DIR/venv"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r requirements.txt

SERVICE_FILE="services/siem-agent-linux.service"
cp "$SERVICE_FILE" /etc/systemd/system/

chmod 700 "$INSTALL_DIR/agent/"
chmod 600 "$INSTALL_DIR/keys/"*.pem 2>/dev/null || true
chmod 600 "$INSTALL_DIR/config.json"

systemctl daemon-reload
systemctl enable siem-agent-linux.service
systemctl start  siem-agent-linux.service

sleep 2
systemctl status siem-agent-linux.service

echo "==> SIEM Agent installed. Follow logs with:"
echo "    journalctl -u siem-agent-linux -f"

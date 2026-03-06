#!/bin/bash
# SIEM Agent – Linux installer
# Run as root: sudo ./install.sh
set -e

INSTALL_DIR="/opt/siem-agent/linux"

echo "==> SIEM Agent Linux Installer"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

mkdir -p "$INSTALL_DIR/logs"
cp -r agent/       "$INSTALL_DIR/"
cp -r keys/        "$INSTALL_DIR/"
cp    config.json  "$INSTALL_DIR/"
cp -r ../common/   "$INSTALL_DIR/../common/" 2>/dev/null || true

echo "==> Installing Python dependencies (venv)..."
if ! python3 -m venv --help &>/dev/null; then
    apt-get install -y python3-venv
fi
VENV_DIR="$INSTALL_DIR/venv"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r requirements.txt

SERVICE_FILE="services/siem-agent-linux.service"
cp "$SERVICE_FILE" /etc/systemd/system/
chattr +i "/etc/systemd/system/siem-agent-linux.service" 2>/dev/null || true

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

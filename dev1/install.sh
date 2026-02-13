#!/bin/bash
# Install Chatterbox on Dev1 (Linux)
set -e

MACHINE_ID="dev1"
INSTALL_DIR="/opt/chatterbox/$MACHINE_ID"

echo "Installing Chatterbox for $MACHINE_ID..."

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./install.sh)"
    exit 1
fi

mkdir -p "$INSTALL_DIR"
cp -r client/ "$INSTALL_DIR/"
cp -r keys/ "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/logs"
cp config.json "$INSTALL_DIR/"

# Copy common module
cp -r ../common/ "$INSTALL_DIR/../common/" 2>/dev/null || true

echo "Installing dependencies..."
pip3 install -r requirements.txt

cp "services/chatterbox-$MACHINE_ID.service" /etc/systemd/system/
chattr +i "/etc/systemd/system/chatterbox-$MACHINE_ID.service" 2>/dev/null || true

chmod 700 "$INSTALL_DIR/client/"
chmod 600 "$INSTALL_DIR/keys/"*.pem
chmod 600 "$INSTALL_DIR/config.json"

systemctl daemon-reload
systemctl enable "chatterbox-$MACHINE_ID.service"
systemctl start "chatterbox-$MACHINE_ID.service"

sleep 2
systemctl status "chatterbox-$MACHINE_ID.service"

echo "Chatterbox installed. Logs: journalctl -u chatterbox-$MACHINE_ID -f"

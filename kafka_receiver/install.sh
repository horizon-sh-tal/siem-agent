#!/bin/bash
# Install Kafka Receiver
set -e

echo "Installing Kafka Log Receiver..."
pip3 install -r requirements.txt
mkdir -p received_logs

echo "Done. Start with:  python3 receiver.py --config config.json --verbose"

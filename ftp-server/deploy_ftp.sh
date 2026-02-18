#!/bin/bash
# FTP Server Quick Deployment Script
# Run this on Ubuntu 20.04 Server VM (IP: 192.168.27.211)

set -e

echo "========================================="
echo "FTP Honeypot Server - Quick Deployment"
echo "========================================="
echo ""

# Check if running as non-root user
if [ "$EUID" -eq 0 ]; then 
    echo "❌ Please run as normal user (not root)"
    echo "   This script will use sudo when needed"
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt-get update -qq

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed"
    echo "⚠️  You need to LOG OUT and LOG BACK IN for Docker to work"
    echo "   After logging back in, run this script again."
    exit 0
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "🐳 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed"
else
    echo "✅ Docker Compose already installed"
fi

# Install required tools
echo "🔧 Installing required tools..."
sudo apt-get install -y enscript ghostscript python3 python3-pip net-tools ufw -qq
echo "✅ Tools installed"

# Create project directory
PROJECT_DIR="$HOME/ftp-server"
if [ -d "$PROJECT_DIR" ]; then
    echo "📁 Project directory exists: $PROJECT_DIR"
    read -p "   Do you want to DELETE and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Removing old directory..."
        rm -rf "$PROJECT_DIR"
        mkdir -p "$PROJECT_DIR"
    fi
else
    echo "📁 Creating project directory: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"

# Check if files exist
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found in $PROJECT_DIR"
    echo "   Please copy all files to this directory first:"
    echo "   - docker-compose.yml"
    echo "   - add_ftp_users.sh"
    echo "   - ftp_monitor.py"
    echo "   - generate_fake_assets.sh"
    exit 1
fi

echo "✅ All files found in $PROJECT_DIR"

# Make scripts executable
chmod +x add_ftp_users.sh generate_fake_assets.sh ftp_monitor.py

# Generate fake assets
if [ ! -d "ftp-data" ]; then
    echo "🎭 Generating fake assets..."
    ./generate_fake_assets.sh
    echo "✅ Fake assets generated"
else
    echo "📂 ftp-data directory exists, skipping asset generation"
    read -p "   Regenerate assets? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf ftp-data
        ./generate_fake_assets.sh
    fi
fi

# Configure firewall
echo "🔥 Configuring firewall..."
sudo ufw allow from 192.168.27.0/24 to any port 21 comment 'FTP Control'
sudo ufw allow from 192.168.27.0/24 to any port 30000:30009 comment 'FTP Passive'
sudo ufw --force enable
echo "✅ Firewall configured"

# Stop any running containers
if docker ps | grep -q ftp-server; then
    echo "🛑 Stopping existing FTP containers..."
    docker-compose down
fi

# Start FTP server
echo "🚀 Starting FTP server..."
docker-compose up -d

# Wait for containers to start
sleep 5

# Check container status
echo ""
echo "📊 Container Status:"
docker ps --filter "name=ftp" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Test FTP server
echo ""
echo "🧪 Testing FTP server..."
if nc -z localhost 21; then
    echo "✅ FTP server is listening on port 21"
else
    echo "❌ FTP server is NOT responding on port 21"
    echo "   Check logs: docker logs ftp-server"
    exit 1
fi

# Display summary
echo ""
echo "========================================="
echo "✅ FTP Honeypot Server Deployment Complete!"
echo "========================================="
echo ""
echo "📋 Summary:"
echo "   FTP Server IP: 192.168.27.211"
echo "   Control Port: 21"
echo "   Passive Ports: 30000-30009"
echo ""
echo "👥 FTP Accounts:"
echo "   guest / guest123 (read-only)"
echo "   prof1 / Maharanapratap! (full access)"
echo "   prof2 / gogreen@7560 (full access)"
echo ""
echo "📁 Fake Assets:"
echo "   $(find ftp-data -type f | wc -l) files generated"
echo "   MoUs: $(find ftp-data -name '*.pdf' -path '*/MoUs/*' | wc -l) PDFs"
echo "   Research: $(find ftp-data -name '*.pdf' -path '*/research/*' | wc -l) PDFs"
echo "   Datasets: $(find ftp-data -name '*.csv' | wc -l) CSVs"
echo ""
echo "📡 Monitoring:"
echo "   Kafka Broker: 192.168.27.211:9092"
echo "   Topic: ftp-activity-logs"
echo "   Scan Interval: 30 minutes"
echo ""
echo "🔍 Useful Commands:"
echo "   View logs:       docker-compose logs -f"
echo "   View FTP logs:   docker logs ftp-server -f"
echo "   View monitor:    docker logs ftp-monitor -f"
echo "   Stop server:     docker-compose down"
echo "   Restart server:  docker-compose restart"
echo ""
echo "🧪 Test FTP Access:"
echo "   ftp 192.168.27.211"
echo "   Username: guest"
echo "   Password: guest123"
echo ""
echo "📖 Full documentation: cat INSTALLATION_GUIDE.md"
echo ""

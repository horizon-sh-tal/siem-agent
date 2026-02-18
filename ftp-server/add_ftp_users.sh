#!/bin/bash
set -e

echo "Creating FTP user database..."

# Create ftpuser system user if it doesn't exist
id -u ftpuser &>/dev/null || adduser --system --no-create-home --disabled-login ftpuser

# Ensure directories exist with proper permissions
mkdir -p /home/ftpusers/guest /home/ftpusers/prof1 /home/ftpusers/prof2
chown -R ftpuser:nogroup /home/ftpusers

# Add privileged users (prof1, prof2)
echo "Adding prof1 user..."
pure-pw useradd prof1 -u ftpuser -d /home/ftpusers/prof1 -m <<EOF
Maharanapratap!
Maharanapratap!
EOF

echo "Adding prof2 user..."
pure-pw useradd prof2 -u ftpuser -d /home/ftpusers/prof2 -m <<EOF
gogreen@7560
gogreen@7560
EOF

echo "Building PureDB database..."
pure-pw mkdb

echo "Listing all FTP users:"
pure-pw list

echo "Starting FTP server..."
# Start Pure-FTPd with specific flags
exec /usr/sbin/pure-ftpd \
    -c 50 \
    -C 10 \
    -l puredb:/etc/pure-ftpd/pureftpd.pdb \
    -E \
    -j \
    -R \
    -P $PUBLICHOST \
    -p 30000:30009

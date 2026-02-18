#!/bin/bash
set -e

# Start FTP server in background with guest user
/entrypoint.sh pure-ftpd &
sleep 5

# Add privileged users (replace [prof1_password] and [prof2_password] with real passwords)
pure-pw useradd prof1 -u ftpuser -d /home/ftpusers/prof1 <<EOF
[prof1_password]
[prof1_password]
EOF
pure-pw useradd prof2 -u ftpuser -d /home/ftpusers/prof2 <<EOF
[prof2_password]
[prof2_password]
EOF
pure-pw mkdb

# Wait for background FTP server
wait

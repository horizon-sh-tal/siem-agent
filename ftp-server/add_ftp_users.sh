#!/bin/bash
set -e

# Only add privileged users (prof1, prof2)
pure-pw useradd prof1 -u ftpuser -d /home/ftpusers/prof1 <<EOF
Maharanapratap!
Maharanapratap!
EOF

pure-pw useradd prof2 -u ftpuser -d /home/ftpusers/prof2 <<EOF
gogreen@7560
gogreen@7560
EOF

pure-pw mkdb

# Now start the FTP server (this must be the last command)
exec /entrypoint.sh pure-ftpd

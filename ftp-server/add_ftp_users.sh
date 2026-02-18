#!/bin/bash
set -e

# Only add privileged users (prof1, prof2)
pure-pw useradd prof1 -u ftpuser -d /home/ftpusers/prof1 <<EOF
[prof1_password]
[prof1_password]
EOF

pure-pw useradd prof2 -u ftpuser -d /home/ftpusers/prof2 <<EOF
[prof2_password]
[prof2_password]
EOF

pure-pw mkdb

# Now start the FTP server (this must be the last command)
exec /entrypoint.sh pure-ftpd

#!/bin/sh
# Starts as root only long enough to make sure the app can write its data
# folder (Docker creates a missing bind-mount folder as root), then drops
# to the unprivileged "ironrod" user to run the server.
set -e
mkdir -p /data
chown -R ironrod:ironrod /data
exec setpriv --reuid=ironrod --regid=ironrod --init-groups "$@"

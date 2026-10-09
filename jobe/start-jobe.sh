#!/bin/sh
set -eu
# Cache lifetime equals container uptime; only Jobe's server may publish objects.
install -d -o www-data -g www-data -m 0755 /var/cache/jobe/catch2
find /var/cache/jobe/catch2 -mindepth 1 -delete
exec "$@"

#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo 'Usage: bash start.sh [deployment-directory]'
    echo 'Default directory: /opt/letto/docker/compose/letto'
    echo 'Requires docker-service-pluginpython.yml and .env in that directory.'
}
case "${1:-}" in
    --help|-h) usage; exit 0 ;;
    -*) usage >&2; exit 1 ;;
esac
if (( $# > 1 )); then usage >&2; exit 1; fi

deployment_dir="${1:-/opt/letto/docker/compose/letto}"
cd -- "$deployment_dir"
for file in docker-service-pluginpython.yml .env; do
    if [[ ! -f "$file" ]]; then
        echo "Missing $PWD/$file" >&2
        exit 1
    fi
done
compose=(docker compose --env-file .env -f docker-service-pluginpython.yml)
services=(pluginpython jobe)

docker info >/dev/null
"${compose[@]}" config --quiet
echo 'Pulling the configured images:'
"${compose[@]}" config --images
"${compose[@]}" pull "${services[@]}"

# Prepare the external network before interrupting the existing services.
if ! docker network inspect nw-letto >/dev/null 2>&1; then
    docker network create nw-letto
fi

echo 'Stopping the previous containers and starting the downloaded images...'
"${compose[@]}" stop "${services[@]}"
if ! "${compose[@]}" up -d --no-build --pull never --force-recreate \
    --wait --wait-timeout 180 "${services[@]}"; then
    echo 'Startup failed or timed out. No automatic rollback was performed.' >&2
    "${compose[@]}" ps --all || true
    echo 'Inspect service logs with docker compose --env-file .env -f docker-service-pluginpython.yml logs --tail 100' >&2
    exit 1
fi
"${compose[@]}" ps
echo 'Plugin Python and Jobe are running and healthy.'

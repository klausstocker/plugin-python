#!/usr/bin/env bash
set -euo pipefail

usage() { echo 'Usage: bash docker-cleanup.sh [--yes]'; }
confirmed=false
case "${1:-}" in
    --yes) confirmed=true; shift ;;
    --help|-h) usage; exit 0 ;;
esac
if (( $# )); then usage >&2; exit 1; fi

docker info >/dev/null
echo 'WARNING: This affects ALL containers and images on the Docker engine targeted by your current Docker settings.'
echo 'Containers and their writable data will be removed. Volumes and bind-mounted files are preserved.'
echo 'All unused images and the selected builder cache will be deleted.'
if [[ "$confirmed" == false ]]; then
    read -r -p 'Type DELETE to continue: ' answer
    if [[ "$answer" != DELETE ]]; then echo 'Cancelled.'; exit 1; fi
fi

# Capture successfully before making changes; an empty engine is valid.
container_output="$(docker container ls --all --quiet --no-trunc)"
containers=()
if [[ -n "$container_output" ]]; then mapfile -t containers <<< "$container_output"; fi
for container in "${containers[@]}"; do
    docker container stop "$container"
    docker container rm "$container"
done
docker image prune --all --force
docker builder prune --all --force
docker system df
echo 'Cleanup complete. Volumes and bind-mounted files were preserved.'

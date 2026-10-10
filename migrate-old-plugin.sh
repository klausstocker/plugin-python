#!/usr/bin/env bash
# Run on the playground before installing the replacement deployment files.
set -euo pipefail

dry_run=false
if [[ ${1:-} == --dry-run ]]; then
    dry_run=true
    shift
fi
if (( $# > 2 )); then
    echo "Usage: bash migrate-old-plugin.sh [--dry-run] [compose-directory] [proxy-directory]" >&2
    exit 2
fi
compose_dir=${1:-/opt/letto/docker/compose/letto}
proxy_dir=${2:-/opt/letto/docker/proxy}

# Check Docker before changing any files. Stop only the legacy containers.
docker info >/dev/null
for container in letto-pluginpython letto-jobe; do
    if docker container inspect "$container" >/dev/null 2>&1; then
        if [[ $dry_run == true ]]; then
            echo "Would stop container: $container"
        else
            docker stop "$container"
        fi
    else
        echo "Legacy container absent: $container"
    fi
done

for file in "$compose_dir/docker-service-pluginpython.yml" "$proxy_dir/pluginpython.conf"; do
    if [[ ! -e $file && ! -L $file ]]; then
        echo "Legacy file absent: $file"
        continue
    fi
    if [[ -L $file || ! -f $file ]]; then
        echo "Refusing to remove a symlink or non-regular file: $file" >&2
        exit 1
    fi
    # Preserve replacement configurations installed under their former names.
    if grep -Eq 'PythonCppPlugin|python-cpp-plugin|pythoncppplugin' "$file"; then
        echo "Keeping replacement configuration: $file"
        continue
    fi
    if [[ $dry_run == true ]]; then
        echo "Would remove legacy file: $file"
    else
        rm -- "$file"
        echo "Removed legacy file: $file"
    fi
done

echo "Migration cleanup finished. Container data, images and volumes are retained."

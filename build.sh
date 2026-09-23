#!/usr/bin/env bash
set -euo pipefail

no_push=false
target=
usage() { echo 'Usage: bash build.sh [jobe|plugin] [--no-push]'; }
for arg in "$@"; do
    case "$arg" in
        --no-push) no_push=true ;;
        --help|-h) usage; exit 0 ;;
        jobe|plugin)
            if [[ -n "$target" ]]; then usage >&2; exit 1; fi
            target="$arg"
            ;;
        *) usage >&2; exit 1 ;;
    esac
done

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
hash=unknown
tags=()
if [[ -e "$root/.git" ]] && command -v git >/dev/null 2>&1; then
    hash="$(git -C "$root" rev-parse --short HEAD)"
    tag_output="$(git -C "$root" tag --points-at HEAD)"
    if [[ -n "$tag_output" ]]; then
        mapfile -t tags <<< "$tag_output"
    fi
fi
for tag in "${tags[@]}"; do
    if [[ ! "$tag" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]; then
        echo "Git tag '$tag' is not a valid Docker tag." >&2
        exit 1
    fi
done
if (( ${#tags[@]} )) && [[ "$no_push" == false ]]; then
    changes="$(git -C "$root" status --porcelain --untracked-files=normal)"
    if [[ -n "$changes" ]]; then
        echo 'Publishing requires a clean checkout. Commit changes or use --no-push.' >&2
        exit 1
    fi
fi

images=(klausstocker/letto-plugin-python klausstocker/letto-plugin-python-jobe)
files=(Dockerfile jobe/Dockerfile)
case "$target" in
    plugin) images=("${images[0]}"); files=("${files[0]}") ;;
    jobe) images=("${images[1]}"); files=("${files[1]}") ;;
esac
for i in "${!images[@]}"; do
    echo "Building ${images[$i]}:latest (commit $hash)"
    docker build --build-arg "PLUGIN_BUILD_HASH=$hash" -t "${images[$i]}:latest" -f "$root/${files[$i]}" "$root"
done
for tag in "${tags[@]}"; do
    for image in "${images[@]}"; do
        docker tag "$image:latest" "$image:$tag"
    done
done
if [[ "$no_push" == false ]]; then
    for image in "${images[@]}"; do
        docker push "$image:latest"
        for tag in "${tags[@]}"; do
            [[ "$tag" == latest ]] || docker push "$image:$tag"
        done
    done
else
    echo 'Images built locally; publishing skipped (--no-push set).'
fi

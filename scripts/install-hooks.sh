#!/usr/bin/env bash
#
# Install the repo's git hooks into .git/hooks/ as symlinks.
#
# Idempotent: re-running overwrites the symlinks but is otherwise
# safe. Run from the repo root:
#
#     scripts/install-hooks.sh

set -e

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

src_dir="scripts/hooks"
dst_dir=".git/hooks"

if [[ ! -d "$src_dir" ]]; then
    echo "✖ $src_dir not found. Are you in the repo root?" >&2
    exit 1
fi

mkdir -p "$dst_dir"

for hook in "$src_dir"/*; do
    [[ -f "$hook" ]] || continue
    name=$(basename "$hook")
    chmod +x "$hook"
    ln -sf "../../$hook" "$dst_dir/$name"
    echo "✓ installed $name"
done

#!/usr/bin/env bash
# Commit what's staged without the trailer Cursor's shell adds to `git commit`.
set -euo pipefail
msg_file=$(mktemp)
printf '%s\n' "$@" > "$msg_file"
tree=$(git write-tree)
commit=$(git commit-tree "$tree" -p HEAD -F "$msg_file")
git reset --soft "$commit"
rm -f "$msg_file"
git log -1 --format=%B

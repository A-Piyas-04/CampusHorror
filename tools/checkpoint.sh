#!/usr/bin/env bash
# Snapshots the WHOLE working tree (tracked + untracked, respecting .gitignore) into refs/checkpoints/<name>,
# using a temporary index: HEAD, the real index and the working tree are untouched. Nothing is committed to a
# branch and nothing is pushed.
#
#   tools/checkpoint.sh before-big-edit      # save
#   git log --oneline refs/checkpoints/before-big-edit -1
#   git diff refs/checkpoints/before-big-edit   # what changed since
#   git restore --source=refs/checkpoints/before-big-edit -- <path>   # bring one file back
set -e
cd "$(dirname "$0")/.."
name=${1:?usage: tools/checkpoint.sh <name>}
tmp=$(mktemp)
cp .git/index "$tmp"
export GIT_INDEX_FILE="$tmp"
git add -A >/dev/null 2>&1
tree=$(git write-tree)
commit=$(git commit-tree "$tree" -p HEAD -m "checkpoint: $name")
unset GIT_INDEX_FILE
rm -f "$tmp"
git update-ref "refs/checkpoints/$name" "$commit"
echo "checkpoint $name -> ${commit:0:10} (tree ${tree:0:10}); HEAD still $(git rev-parse --short HEAD)"

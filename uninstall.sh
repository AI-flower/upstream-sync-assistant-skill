#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
SKILL_NAME="upstream-sync-assistant"
TARGETS="$HOME/.agents/skills/$SKILL_NAME $HOME/.codex/skills/$SKILL_NAME"

for target in $TARGETS; do
  if [ -L "$target" ] && [ "$(readlink "$target")" = "$ROOT_DIR" ]; then
    rm -f "$target"
    echo "Removed $target"
  fi
done

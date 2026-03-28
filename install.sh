#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
SKILL_NAME="upstream-sync-assistant"
TARGETS="$HOME/.agents/skills/$SKILL_NAME $HOME/.codex/skills/$SKILL_NAME"

for target in $TARGETS; do
  parent=$(dirname "$target")
  mkdir -p "$parent"

  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "Refusing to overwrite non-symlink target: $target" >&2
    exit 1
  fi

  rm -f "$target"
  ln -s "$ROOT_DIR" "$target"
  echo "Installed $SKILL_NAME -> $target"
done

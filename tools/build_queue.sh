#!/usr/bin/env bash
# Build one topic and state, one build at a time, logging to the queue log. No language model.
# Run: bash tools/build_queue.sh agriculture AP
# Waiting builds take a lock (mkdir is atomic), so two never start together when the one before finishes.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=eval/cache/hand/queue.log
LOCK=eval/cache/hand/.build.lock
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }
until mkdir "$LOCK" 2>/dev/null; do
  # A lock left by a build that died is cleared when no build is running.
  if ! ps -ef | grep 'vetra.intake build' | grep -v grep > /dev/null && [ -n "$(find "$LOCK" -maxdepth 0 -mmin +5 2>/dev/null)" ]; then
    rmdir "$LOCK" 2>/dev/null
  fi
  sleep 20
done
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
while ps -ef | grep 'vetra.intake build' | grep -v grep > /dev/null; do sleep 20; done  # builds started the old way
say "build $1 $2"
python -m vetra.intake build "$1" "$2" 2>&1 | tail -1 | cut -c1-120 >> "$LOG"
say "build $1 $2 finished"

#!/usr/bin/env bash
# Build one topic and state, logging to the queue log. No language model. Run: bash tools/data_queue6.sh agriculture AP
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=eval/cache/hand/queue.log
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }
while ps -ef | grep 'vetra.intake build' | grep -v grep > /dev/null; do sleep 30; done
say "build $1 $2"
python -m vetra.intake build "$1" "$2" 2>&1 | tail -1 | cut -c1-120 >> "$LOG"
say "build $1 $2 finished"

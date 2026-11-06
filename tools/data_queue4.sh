#!/usr/bin/env bash
# Builds after the 6 Nov morning picks (eval/cache/hand/pick_TN3.jsonl). No language model. Run: bash tools/data_queue4.sh
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=eval/cache/hand/queue.log
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }
for pair in "agriculture TN" "finance TN"; do
  say "build $pair"
  python -m vetra.intake build $pair 2>&1 | tail -1 | cut -c1-120 >> "$LOG"
done
say "rate lines"
python tools/rate_lines.py TN > eval/cache/hand/rates.log 2>&1
say "fourth data queue finished"

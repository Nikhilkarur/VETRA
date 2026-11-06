#!/usr/bin/env bash
# After tools/data_queue4.sh: build Andhra Pradesh with the 6 Nov morning picks (pick_AP3.jsonl). No language model.
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=eval/cache/hand/queue.log
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }
while ps -ef | grep 'data_queue4.sh' | grep -v grep > /dev/null; do sleep 30; done
for pair in "finance AP" "agriculture AP"; do
  say "build $pair"
  python -m vetra.intake build $pair 2>&1 | tail -1 | cut -c1-120 >> "$LOG"
done
say "rate lines"
python tools/rate_lines.py AP > eval/cache/hand/rates_ap.log 2>&1
say "fifth data queue finished"

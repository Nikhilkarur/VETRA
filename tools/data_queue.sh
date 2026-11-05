#!/usr/bin/env bash
# Data work on the PC with no language model: download what pick_docs chose, build search one topic at a time, pull rate lines.
# Each step can be re-run safely. Run: bash tools/data_queue.sh
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=eval/cache/hand/queue.log
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }
for state in AP TN; do
  say "fetch picks $state"
  python tools/fetch_docs.py "eval/cache/hand/pick_$state.jsonl" > "eval/cache/hand/fetch_$state.log" 2>&1
  tail -1 "eval/cache/hand/fetch_$state.log" >> "$LOG"
done
say "order links"
python tools/order_links.py > eval/cache/hand/order_links.log 2>&1
for pair in "finance AP" "agriculture AP" "finance TN" "agriculture TN"; do
  say "build $pair"
  python -m vetra.intake build $pair 2>&1 | tail -1 | cut -c1-120 >> "$LOG"
done
say "rate lines"
python tools/rate_lines.py TN AP > eval/cache/hand/rates.log 2>&1
say "data queue finished"

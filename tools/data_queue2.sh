#!/usr/bin/env bash
# Second batch, after tools/data_queue.sh: Tamil Nadu orders by file name. No language model. Run: bash tools/data_queue2.sh
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=eval/cache/hand/queue.log
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }
while ps -ef | grep 'data_queue.sh' | grep -v grep > /dev/null; do sleep 30; done
say "fetch TN orders by file name"
python tools/fetch_docs.py eval/cache/hand/pick_TN2.jsonl > eval/cache/hand/fetch_TN2.log 2>&1
tail -1 eval/cache/hand/fetch_TN2.log >> "$LOG"
python tools/order_titles.py eval/cache/hand/pick_TN2.jsonl 2>&1 | tail -1 >> "$LOG"
say "order links"
python tools/order_links.py > eval/cache/hand/order_links.log 2>&1
for pair in "agriculture TN" "finance TN" "agriculture AP" "finance AP"; do
  say "build $pair"
  python -m vetra.intake build $pair 2>&1 | tail -1 | cut -c1-120 >> "$LOG"
done
say "rate lines"
python tools/rate_lines.py TN AP > eval/cache/hand/rates.log 2>&1
say "second data queue finished"

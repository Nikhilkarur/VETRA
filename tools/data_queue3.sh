#!/usr/bin/env bash
# Third batch, after tools/data_queue2.sh: name the scanned Tamil Nadu orders from their OCR and
# build Tamil Nadu agriculture again (OCR already read is reused). No language model. Run: bash tools/data_queue3.sh
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=eval/cache/hand/queue.log
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }
while ps -ef | grep 'data_queue2.sh' | grep -v grep > /dev/null; do sleep 30; done
say "name TN orders from OCR"
python tools/order_titles.py eval/cache/hand/pick_TN2.jsonl 2>&1 | tail -1 >> "$LOG"
say "build agriculture TN"
python -m vetra.intake build agriculture TN > eval/cache/hand/build_tn3.log 2>&1
tail -1 eval/cache/hand/build_tn3.log | cut -c1-120 >> "$LOG"
say "order links"
python tools/order_links.py > eval/cache/hand/order_links.log 2>&1
say "rate lines"
python tools/rate_lines.py TN > eval/cache/hand/rates.log 2>&1
say "third data queue finished"

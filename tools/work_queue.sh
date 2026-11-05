#!/usr/bin/env bash
# Long jobs for the PC, one after another, so builds never overlap. Each step can be re-run safely.
# Run: bash tools/work_queue.sh LOG   (the list files are made by hand in eval/cache/hand/)
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
LOG=${1:-eval/cache/hand/queue.log}
say() { echo "$(date '+%d %b %H:%M') $*" >> "$LOG"; }

for list in eval/cache/hand/list6.jsonl eval/cache/hand/list5a.jsonl; do
  say "fetch $list"
  python tools/fetch_docs.py "$list" 2>&1 | tail -1 >> "$LOG"
done
for pair in "finance AP" "finance TN" "agriculture AP" "agriculture TN"; do
  say "build $pair"
  python -m vetra.intake build $pair 2>&1 | tail -1 | cut -c1-120 >> "$LOG"
done
say "aspect questions AP TN"
python eval/aspect_questions.py first AP TN >> eval/cache/hand/aspects.log 2>&1
say "queue finished"

#!/usr/bin/env bash
# Keep asking the aspect questions until each has a real answer, waiting out free-tier limits.
# Run: bash tools/aspect_loop.sh NAME STATE [STATE ...]
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8
name=$1; shift
for i in $(seq 1 48); do
  python eval/aspect_questions.py "$name" "$@" >> eval/cache/hand/aspects.log 2>&1
  missing=$(python -c "
import json,sys
sys.path.insert(0,'eval')
from aspect_questions import QUESTIONS
s=json.load(open('eval/cache/aspects/$name.json',encoding='utf8'))
print(sum(f'{st}|{a}' not in s for st in '$*'.split() for a in QUESTIONS))")
  echo "$(date '+%d %b %H:%M') still missing $missing" >> eval/cache/hand/queue.log
  [ "$missing" = "0" ] && break
  sleep 1800
done
echo "$(date '+%d %b %H:%M') aspect questions finished" >> eval/cache/hand/queue.log

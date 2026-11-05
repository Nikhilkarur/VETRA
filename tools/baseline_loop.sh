#!/bin/bash
# Runs the frozen baseline test, retrying until every question is answered. Pass the frozen copy folder.
cd "$1"; export PYTHONIOENCODING=utf8
for i in $(seq 1 60); do
  python -u eval/gold_test.py --run first --wait 3 >> gold_loop.log 2>&1
  n=$(python -c "import json;print(len(json.load(open('eval/cache/gold/first.json',encoding='utf8'))))")
  echo "$(date) answered $n" >> gold_loop.log
  [ "$n" -ge 179 ] && break
  sleep 1800
done
python eval/gold_test.py --sheet first >> gold_loop.log 2>&1
echo FINISHED >> gold_loop.log

#!/usr/bin/env bash
cd /root/zongyuan-yuanji/src
export YUANJI_ROOT=/root/zongyuan-yuanji
python3 seed_extractor.py > /root/zongyuan-yuanji/logs/extract_run.log 2>&1
echo "EXIT:$?" >> /root/zongyuan-yuanji/logs/extract_run.log

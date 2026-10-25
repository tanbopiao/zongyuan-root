#!/usr/bin/env bash
cd /root/zongyuan-yuanji/src
export YUANJI_ROOT=/root/zongyuan-yuanji
python3 seed_verify.py > /root/zongyuan-yuanji/logs/verify_run.log 2>&1
echo "EXIT:$?" >> /root/zongyuan-yuanji/logs/verify_run.log

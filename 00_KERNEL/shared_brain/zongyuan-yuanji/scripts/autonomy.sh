#!/bin/bash
if ! pgrep -f wrapper.py > /dev/null; then
    cd /root/zongyuan-yuanji
    export ARK_API_KEY=ark-800a6f28-5c7f-4ec5-9766-4b7da1a58f1d-50a70
    nohup python3 src/wrapper.py >> logs/wrapper.log 2>&1 &
    echo "$(date) restarted" >> logs/autonomy.log
fi

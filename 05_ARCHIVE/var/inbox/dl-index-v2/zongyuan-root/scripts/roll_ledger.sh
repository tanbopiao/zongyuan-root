#!/bin/bash
# W-04 滚动分片账本：跨月归档副本 + 阈值保护 ｜ DID-BR-000002
ROOT=${1:-/home/user/ZONGYUAN-ROOT}
LEDGER=$ROOT/HASH-LEDGER.csv
ARC=$ROOT/var/ledger_archive
mkdir -p $ARC
YM=$(date +%Y%m)
CUR=$ARC/HASH-LEDGER-$YM.csv
LINES=$(wc -l < $LEDGER 2>/dev/null || echo 0)
if [ ! -f "$CUR" ]; then
  cp $LEDGER $CUR
  echo "$(date) 月度分片归档: $LINES 行 -> $CUR"
fi
if [ "$LINES" -gt 6000 ]; then
  echo "$(date) WARN HASH-LEDGER=$LINES 行超阈值(6000)，建议下月自动分片" >> $ROOT/logs/roll_ledger.log
fi
echo "$(date) roll_ledger ok lines=$LINES" >> $ROOT/logs/roll_ledger.log

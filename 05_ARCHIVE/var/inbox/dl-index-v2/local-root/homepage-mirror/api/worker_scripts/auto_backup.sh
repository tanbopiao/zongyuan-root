#!/bin/bash
# auto_backup.sh 每周全量备份
BK="/home/user/ZONGYUAN-ROOT/backups/$(date +%Y%m%d)"
mkdir -p "$BK"
cp -r /home/user/ZONGYUAN-ROOT/operators /home/user/ZONGYUAN-ROOT/hooks /home/user/ZONGYUAN-ROOT/scripts /home/user/ZONGYUAN-ROOT/config "$BK/" 2>/dev/null
echo "备份到 $BK"

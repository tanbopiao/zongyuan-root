#!/bin/bash
rm -rf /opt/ZONGYUAN-ROOT/ops/oracle
crontab -l 2>/dev/null | grep -v zb-oracle | crontab -
echo "oracle rolled back"

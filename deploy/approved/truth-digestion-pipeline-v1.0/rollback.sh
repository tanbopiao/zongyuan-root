#!/bin/bash
rm -rf /opt/ZONGYUAN-ROOT/ops/digest
crontab -l 2>/dev/null | grep -v zb-digest | crontab -
echo "digest rolled back"

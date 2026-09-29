#!/bin/bash
rm -rf /opt/ZONGYUAN-ROOT/ops/refine
crontab -l 2>/dev/null | grep -v zb-refine | crontab -
echo "refine rolled back"

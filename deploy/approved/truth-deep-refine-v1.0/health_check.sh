#!/bin/bash
[ -s /opt/ZONGYUAN-ROOT/data/refine_report.json ] && echo "refine ok" && exit 0
echo "refine missing" && exit 1

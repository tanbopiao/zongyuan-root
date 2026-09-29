#!/bin/bash
[ -s /opt/ZONGYUAN-ROOT/data/oracle_report.json ] && echo "oracle ok" && exit 0
echo "oracle missing" && exit 1

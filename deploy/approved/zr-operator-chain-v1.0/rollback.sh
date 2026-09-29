#!/bin/bash
rm -rf /opt/ZONGYUAN-ROOT/ops/chain
grep -v orchestrator.py /opt/ZONGYUAN-ROOT/worker/consumer.sh 2>/dev/null > /tmp/c.tmp && mv /tmp/c.tmp /opt/ZONGYUAN-ROOT/worker/consumer.sh
echo "chain rolled back"

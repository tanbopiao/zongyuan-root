#!/bin/bash
[ -f /opt/ZONGYUAN-ROOT/ops/chain/chain.json ] && [ -f /opt/ZONGYUAN-ROOT/ops/chain/orchestrator.py ] && echo "chain ok" && exit 0
echo "chain missing" && exit 1

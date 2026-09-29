#!/bin/bash
rm -rf /opt/ZONGYUAN-ROOT/ops/evolve /opt/ZONGYUAN-ROOT/data/evolve_state.json
crontab -l 2>/dev/null | grep -v zb-evolve | crontab -
echo "evolve rolled back"

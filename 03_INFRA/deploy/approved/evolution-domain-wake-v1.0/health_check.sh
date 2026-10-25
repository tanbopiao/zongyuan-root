#!/bin/bash
[ -s /opt/ZONGYUAN-ROOT/data/evolve_report.json ] && echo "evolve ok" && exit 0
echo "evolve missing" && exit 1

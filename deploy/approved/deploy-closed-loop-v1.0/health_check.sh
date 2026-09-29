#!/bin/bash
[ -f /opt/ZONGYUAN-ROOT/worker/notify.sh ] && [ -f /opt/ZONGYUAN-ROOT/worker/enhance.sh ] && echo "loop ok" && exit 0
echo "loop missing" && exit 1

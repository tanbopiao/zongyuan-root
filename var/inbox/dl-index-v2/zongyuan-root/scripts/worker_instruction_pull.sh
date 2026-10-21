#!/bin/bash
# worker 认知指令拉取（中枢智能管控）| DID-BR-000002 | cron */5 | 失败不阻塞
HOST=zongyuan-cloud
DST=/home/user/ZONGYUAN-ROOT/var/instructions
mkdir -p "$DST"
TS=$(date +%s)
ssh -o BatchMode=yes -o ConnectTimeout=10 "$HOST" "python3 /opt/ZONGYUAN-ROOT/scripts/truth_instructions.py" > "$DST/raw.jsonl" 2>/dev/null
if [ -s "$DST/raw.jsonl" ]; then
  python3 /home/user/ZONGYUAN-ROOT/scripts/instruction_filter.py "$DST/raw.jsonl" "$DST/inbox.jsonl" "$DST/seen-ids" "$TS"
else
  echo "云端不可达或空响应（不阻塞）"
fi
